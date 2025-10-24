# cleaning, normalization, feature engineering
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime
import re
from geopy.geocoders import Nominatim
from user_agents import parse

def date_str(timestamp):
    return datetime.fromtimestamp(timestamp)

def preprocess_data( df_contacts=None, df_media=None, df_follows=None, df_devices=None, df_camera_info=None, df_locations_of_interest=None, possible_emails=None, profile_based_in=None, df_link_history=None, recommended_topics=None, signup_details=None, password_change_activity=None, df_last_known_location=None, df_logs=None, df_time_spent_on_ig=None):
    if df_contacts is not None:
        df = df_contacts.copy()
        df.columns = [c.strip().replace("string_map_data_", "").replace("_value", "") for c in df.columns]

        email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")

        def detect_email(val):
            if isinstance(val, str) and email_pattern.match(val.strip()):
                return val.strip()
            return None

        def detect_phone(val):
            if isinstance(val, str):
                cleaned = re.sub(r"[^\d+]", "", val)
                if 6 <= len(cleaned) <= 15:
                    return cleaned
            return None

        df["email"] = df["Contact Information"].apply(detect_email)
        df["phone"] = df["Contact Information"].apply(detect_phone)

        # --- clean up (optional) ---
        df["First Name"] = df["First Name"].fillna("").str.strip()
        df["Last Name"] = df["Last Name"].fillna("").str.strip()

        # --- reorder for readability ---
        cols = ["First Name", "Last Name", "email", "phone", "Contact Information"]
        df = df[[c for c in cols if c in df.columns]]

        return df

    if df_media is not None:
        def _parse_path_bits(path: str) -> dict:
            """Extract media_type, timestamp-like folder, filename, and extension from a relative path."""
            if not isinstance(path, str) or not path.strip():
                return {"media_type": None, "ts_folder": None, "filename": None, "ext": None}

            parts = [p for p in path.split("/") if p]
            media_type = parts[0] if len(parts) >= 1 else None
            ts_folder = parts[1] if len(parts) >= 2 else None
            filename = parts[-1] if parts else None
            ext = filename.split(".")[-1].lower() if filename and "." in filename else None

            return {"media_type": media_type, "ts_folder": ts_folder, "filename": filename, "ext": ext}

        def _normalize_timestamp(ts_folder: str) -> dict:
            """
            Converts folder-like timestamps such as '202404', '2021-08', '20210430' into structured info.
            Uses date_str() for readable datetime values when possible.
            """
            if not ts_folder or not isinstance(ts_folder, str):
                return {"timestamp_str": None, "year": None, "month": None, "day": None, "year_month": None}

            digits = re.sub(r"\D", "", ts_folder)  # e.g. '2021-08' → '202108'
            year = month = day = None
            timestamp_str = None
            year_month = None

            # Try YYYYMMDD
            if len(digits) >= 8:
                year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
                timestamp_str = f"{year:04d}{month:02d}{day:02d}"
                try:
                    year_month = date_str(datetime(year, month, 1).timestamp())
                except ValueError:
                    year_month = None
                return {"timestamp_str": timestamp_str, "year": year, "month": month, "day": day, "year_month": year_month}

            # Try YYYYMM
            if len(digits) >= 6:
                year, month = int(digits[:4]), int(digits[4:6])
                timestamp_str = f"{year:04d}{month:02d}"
                try:
                    year_month = date_str(datetime(year, month, 1).timestamp())
                except ValueError:
                    year_month = None
                return {"timestamp_str": timestamp_str, "year": year, "month": month, "day": None, "year_month": year_month}

            # Try YYYY only
            if len(digits) >= 4:
                year = int(digits[:4])
                timestamp_str = f"{year:04d}"
                return {"timestamp_str": timestamp_str, "year": year, "month": None, "day": None, "year_month": None}

            return {"timestamp_str": None, "year": None, "month": None, "day": None, "year_month": None}

        df = df_media.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        for col in ["media_type", "year", "timestamp", "relative_path"]:
            if col not in df.columns:
                df[col] = None

        # Parse relative_path
        parsed = df["relative_path"].apply(_parse_path_bits).apply(pd.Series)
        df["media_type"] = df["media_type"].fillna(parsed["media_type"])
        df["filename"] = parsed["filename"]
        df["ext"] = parsed["ext"]

        # Normalize timestamp info from path
        norm = parsed["ts_folder"].apply(_normalize_timestamp).apply(pd.Series)

        # Fill year and timestamp
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["year"] = df["year"].fillna(norm["year"]).astype("Int64")

        def _clean_ts(x):
            if pd.isna(x):
                return None
            s = re.sub(r"\D", "", str(x))
            return s if len(s) in (4, 6, 8) else None

        df["timestamp"] = df["timestamp"].apply(_clean_ts).fillna(norm["timestamp_str"])
        df["day"] = norm["day"].astype("Int64")
        df["year_month"] = norm["year_month"]

        # Backfill missing values from timestamp
        df.loc[df["year"].isna() & df["timestamp"].notna(), "year"] = (
            df["timestamp"].str[:4].astype("Int64")
        )

        return df

    if df_follows is not None:
        df = df_follows.copy()

        # timestamp -> datetime -> date
        df["dt"] = pd.to_datetime(df["timestamp"], unit="s")
        df["date"] = df["dt"].dt.date

        sets_by_type = {
            t: set(df.loc[df["follows_type"] == t, "username"])
            for t in df["follows_type"].dropna().unique()
        }

        ts = (
            df[df["follows_type"].isin(["followers", "followings"])]
            .sort_values("dt")
            .drop_duplicates(subset=["follows_type", "username"], keep="first")
        )
        daily_new = ts.groupby(["date", "follows_type"])["username"].nunique().reset_index(name="new_count")

        if not daily_new.empty:
            all_dates = pd.date_range(daily_new["date"].min(), daily_new["date"].max(), freq="D").date
            types_present = daily_new["follows_type"].unique()
            idx = pd.MultiIndex.from_product([all_dates, types_present], names=["date", "follows_type"])
            daily_full = daily_new.set_index(["date", "follows_type"]).reindex(idx, fill_value=0).reset_index()
        else:
            daily_full = pd.DataFrame(columns=["date", "follows_type", "new_count"])

        daily_full["cum_count"] = daily_full.groupby("follows_type")["new_count"].cumsum()

        return {"df": df, "sets_by_type": sets_by_type, "timeseries": daily_full}
    
    if df_devices is not None:
        df = df_devices.copy()

        # Function to parse user agent
        def extract_user_agent_info(ua_string):
            ua = parse(ua_string)
            return pd.Series({
                'browser_family': ua.browser.family,
                'browser_version': ua.browser.version_string,
                'os_family': ua.os.family,
                'os_version': ua.os.version_string,
                'device_family': ua.device.family,
                'is_mobile': ua.is_mobile,
                'is_tablet': ua.is_tablet,
                'is_pc': ua.is_pc,
                'is_bot': ua.is_bot
            })

        ua_df = df['user_agent'].apply(extract_user_agent_info)
        df_processed = pd.concat([df, ua_df], axis=1)
        df_processed['last_login_timestamp'] = df_processed['last_login_timestamp'].apply(date_str)
        return df_processed
    
    if df_camera_info is not None:
        pass
    
    if df_locations_of_interest is not None:
        df = df_locations_of_interest.copy()
        #df["value"].encode(encoding='utf-8', inplace=True)
        geolocator = Nominatim(user_agent="insta_dashboard")
        latitudes, longitudes = [], []
        for loc in df["value"]:
            try:
                location = geolocator.geocode(loc)
                if location:
                    latitudes.append(location.latitude)
                    longitudes.append(location.longitude)
                else:
                    latitudes.append(None)
                    longitudes.append(None)
            except Exception:
                latitudes.append(None)
                longitudes.append(None)
        df["latitude"] = latitudes
        df["longitude"] = longitudes
        return df.dropna(subset=["latitude", "longitude"])

    if possible_emails is not None:
        pass
    if profile_based_in is not None:
        pass
    if df_link_history is not None:
        df = df_link_history.copy()
        df["Website_name"] = df["Website_link_you_visited"].apply(
            lambda x: urlparse(x).netloc if pd.notna(x) else None
        )
        df["session_start"] = pd.to_datetime(
        df["Website session start time"],
            format="%b %d, %Y %I:%M:%S%p"
        )

        df["session_end"] = pd.to_datetime(
            df["Website session end time"],
            format="%b %d, %Y %I:%M:%S%p"
        )

        df["total_time_min"] = (df["session_end"] - df["session_start"]).dt.total_seconds() / 60

        return df

    if recommended_topics is not None:
        pass
    if signup_details is not None:
        pass
    if password_change_activity is not None:
        pass
    if df_last_known_location is not None:
        pass
    if df_logs is not None:
        pass
    
    if df_time_spent_on_ig is not None:
        df = df_time_spent_on_ig.copy()
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce", utc=True)
        df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce", utc=True)
        df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce").fillna(0)
        
        df["date"] = df["start_time"].dt.date
        df["date"] = pd.to_datetime(df["date"])
        
        df["duration_min"] = df["duration_sec"] / 60.0
        
        return df
    
    return

def count_user_messages(df_all_conversations: pd.DataFrame) -> tuple:
    """
    Identifie l'utilisateur propriétaire et compte les messages envoyés et reçus.
    Retourne: (nom_utilisateur, messages_envoyés, messages_reçus)
    """
    if df_all_conversations.empty:
        return 0, 0
    
    def find_main_user(df_all_conversations: pd.DataFrame) -> str:
        candidate_users = {}

        for _, row in df_all_conversations.iterrows():
            participants = row.get("participants")
            if not isinstance(participants, list) or len(participants) != 2:
                continue

            for user in participants:
                candidate_users[user] = candidate_users.get(user, 0) + 1

        if not candidate_users:
            return "Unknown User"

        # L'utilisateur principal est celui qui apparaît le plus souvent
        main_user = max(candidate_users, key=candidate_users.get)
        return main_user
    
    main_user = find_main_user(df_all_conversations)
    # Compter les messages envoyés et reçus
    messages_envoyes = 0
    messages_recus = 0
    
    for _, row in df_all_conversations.iterrows():
        participation = row['participants_participation']
        
        if not participation:
            continue
            
        # Messages envoyés par l'utilisateur principal
        if main_user in participation:
            messages_envoyes += participation[main_user]
        
        # Messages reçus (tous les messages des autres participants)
        for user, count in participation.items():
            if user != main_user:
                messages_recus += count
    
    return messages_envoyes, messages_recus