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
    if df_contacts is not None and not df_contacts.empty:
        try:
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

            if "Contact Information" in df.columns:
                df["email"] = df["Contact Information"].apply(detect_email)
                df["phone"] = df["Contact Information"].apply(detect_phone)
            else:
                df["email"] = None
                df["phone"] = None

            # --- clean up (optional) ---
            if "First Name" in df.columns:
                df["First Name"] = df["First Name"].fillna("").str.strip()
            if "Last Name" in df.columns:
                df["Last Name"] = df["Last Name"].fillna("").str.strip()

            # --- reorder for readability ---
            cols = ["First Name", "Last Name", "email", "phone", "Contact Information"]
            df = df[[c for c in cols if c in df.columns]]

            return df
        except Exception as e:
            return pd.DataFrame(columns=["First Name", "Last Name", "email", "phone", "Contact Information"])

    if df_media is not None and not df_media.empty:
        try:
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
            if "relative_path" in df.columns and df["relative_path"].notna().any():
                parsed = df["relative_path"].apply(_parse_path_bits).apply(pd.Series)
                df["media_type"] = df["media_type"].fillna(parsed["media_type"])
                df["filename"] = parsed["filename"]
                df["ext"] = parsed["ext"]

                # Normalize timestamp info from path
                norm = parsed["ts_folder"].apply(_normalize_timestamp).apply(pd.Series)
            else:
                df["filename"] = None
                df["ext"] = None
                norm = pd.DataFrame({
                    "timestamp_str": None,
                    "year": None,
                    "month": None,
                    "day": None,
                    "year_month": None
                }, index=df.index)

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
            if "timestamp" in df.columns and df["timestamp"].notna().any():
                df.loc[df["year"].isna() & df["timestamp"].notna(), "year"] = (
                    df["timestamp"].str[:4].astype("Int64")
                )

            return df
        except Exception as e:
            return pd.DataFrame(columns=["media_type", "year", "timestamp", "relative_path", "filename", "ext"])

    if df_follows is not None and not df_follows.empty:
        try:
            df = df_follows.copy()

            # Ensure required columns exist
            if "timestamp" not in df.columns:
                return {"df": df, "sets_by_type": {}, "timeseries": pd.DataFrame(columns=["date", "follows_type", "new_count", "cum_count"])}

            # timestamp -> datetime -> date
            df["dt"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
            df["date"] = df["dt"].dt.date

            sets_by_type = {}
            if "follows_type" in df.columns and "username" in df.columns:
                sets_by_type = {
                    t: set(df.loc[df["follows_type"] == t, "username"])
                    for t in df["follows_type"].dropna().unique()
                }

            ts = pd.DataFrame()
            if "follows_type" in df.columns and "username" in df.columns:
                ts = (
                    df[df["follows_type"].isin(["followers", "followings"])]
                    .sort_values("dt")
                    .drop_duplicates(subset=["follows_type", "username"], keep="first")
                )
            
            if not ts.empty:
                daily_new = ts.groupby(["date", "follows_type"])["username"].nunique().reset_index(name="new_count")
            else:
                daily_new = pd.DataFrame(columns=["date", "follows_type", "new_count"])

            if not daily_new.empty:
                all_dates = pd.date_range(daily_new["date"].min(), daily_new["date"].max(), freq="D").date
                types_present = daily_new["follows_type"].unique()
                idx = pd.MultiIndex.from_product([all_dates, types_present], names=["date", "follows_type"])
                daily_full = daily_new.set_index(["date", "follows_type"]).reindex(idx, fill_value=0).reset_index()
            else:
                daily_full = pd.DataFrame(columns=["date", "follows_type", "new_count"])

            if not daily_full.empty and "follows_type" in daily_full.columns:
                daily_full["cum_count"] = daily_full.groupby("follows_type")["new_count"].cumsum()
            else:
                daily_full["cum_count"] = 0

            return {"df": df, "sets_by_type": sets_by_type, "timeseries": daily_full}
        except Exception as e:
            return {"df": pd.DataFrame(), "sets_by_type": {}, "timeseries": pd.DataFrame(columns=["date", "follows_type", "new_count", "cum_count"])}
    
    if df_devices is not None and not df_devices.empty:
        try:
            df = df_devices.copy()

            # Function to parse user agent
            def extract_user_agent_info(ua_string):
                try:
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
                except Exception:
                    return pd.Series({
                        'browser_family': None,
                        'browser_version': None,
                        'os_family': None,
                        'os_version': None,
                        'device_family': None,
                        'is_mobile': False,
                        'is_tablet': False,
                        'is_pc': False,
                        'is_bot': False
                    })

            if 'user_agent' in df.columns:
                ua_df = df['user_agent'].apply(extract_user_agent_info)
                df_processed = pd.concat([df, ua_df], axis=1)
            else:
                df_processed = df
                
            if 'last_login_timestamp' in df_processed.columns:
                df_processed['last_login_timestamp'] = df_processed['last_login_timestamp'].apply(
                    lambda x: date_str(x) if pd.notna(x) and x != 0 else None
                )
            return df_processed
        except Exception as e:
            return pd.DataFrame()
    
    if df_camera_info is not None and not df_camera_info.empty:
        # No preprocessing needed currently
        pass
    
    if df_locations_of_interest is not None and not df_locations_of_interest.empty:
        try:
            df = df_locations_of_interest.copy()
            
            if "value" not in df.columns:
                return pd.DataFrame(columns=["value", "latitude", "longitude"])
            
            geolocator = Nominatim(user_agent="insta_dashboard")
            latitudes, longitudes = [], []
            
            for loc in df["value"]:
                if pd.isna(loc) or not loc:
                    latitudes.append(None)
                    longitudes.append(None)
                    continue
                    
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
            
            # Filter out rows with missing coordinates
            df_filtered = df.dropna(subset=["latitude", "longitude"])
            
            # Rename for map compatibility
            if not df_filtered.empty:
                df_filtered = df_filtered.rename(columns={"latitude": "lat", "longitude": "lon"})
            
            return df_filtered
        except Exception as e:
            return pd.DataFrame(columns=["value", "lat", "lon"])

    if possible_emails is not None:
        pass
    if profile_based_in is not None:
        pass
    if df_link_history is not None and not df_link_history.empty:
        try:
            df = df_link_history.copy()
            
            required_cols = ["Website_link_you_visited", "Website session start time", "Website session end time"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return pd.DataFrame(columns=["Website_name", "session_start", "session_end", "total_time_min"])
            
            df["Website_name"] = df["Website_link_you_visited"].apply(
                lambda x: urlparse(x).netloc if pd.notna(x) else None
            )
            df["session_start"] = pd.to_datetime(
                df["Website session start time"],
                format="%b %d, %Y %I:%M:%S%p",
                errors="coerce"
            )

            df["session_end"] = pd.to_datetime(
                df["Website session end time"],
                format="%b %d, %Y %I:%M:%S%p",
                errors="coerce"
            )

            df["total_time_min"] = (df["session_end"] - df["session_start"]).dt.total_seconds() / 60

            return df
        except Exception as e:
            return pd.DataFrame(columns=["Website_name", "session_start", "session_end", "total_time_min"])

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
    
    if df_time_spent_on_ig is not None and not df_time_spent_on_ig.empty:
        try:
            df = df_time_spent_on_ig.copy()
            
            required_cols = ["start_time", "end_time", "duration_sec"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return pd.DataFrame(columns=["start_time", "end_time", "duration_sec", "date", "duration_min"])
            
            df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce", utc=True)
            df["end_time"] = pd.to_datetime(df["end_time"], errors="coerce", utc=True)
            df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce").fillna(0)
            
            df["date"] = df["start_time"].dt.date
            df["date"] = pd.to_datetime(df["date"])
            
            df["duration_min"] = df["duration_sec"] / 60.0
            
            return df
        except Exception as e:
            return pd.DataFrame(columns=["start_time", "end_time", "duration_sec", "date", "duration_min"])
    
    return

def count_user_messages(df_all_conversations: pd.DataFrame) -> tuple:
    """
    Identifies the owner user and counts sent and received messages.
    Returns: (sent_messages, received_messages)
    """
    if df_all_conversations is None or df_all_conversations.empty:
        return 0, 0
    
    try:
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

            # The main user is the one who appears most often
            main_user = max(candidate_users, key=candidate_users.get)
            return main_user
        
        main_user = find_main_user(df_all_conversations)
        
        # Count sent and received messages
        messages_envoyes = 0
        messages_recus = 0
        
        for _, row in df_all_conversations.iterrows():
            participation = row.get('participants_participation')
            
            if not participation or not isinstance(participation, dict):
                continue
                
            # Messages sent by the main user
            if main_user in participation:
                messages_envoyes += participation[main_user]
            
            # Messages received (all messages from other participants)
            for user, count in participation.items():
                if user != main_user:
                    messages_recus += count
        
        return messages_envoyes, messages_recus
    except Exception as e:
        return 0, 0