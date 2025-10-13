# cleaning, normalization, feature engineering
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime

def date_str(timestamp):
    return datetime.fromtimestamp(timestamp)

def preprocess_data( df_contacts=None, df_media=None, df_follows=None, df_devices=None, df_camera_info=None, df_locations_of_interest=None, possible_emails=None, profile_based_in=None, df_link_history=None, recommended_topics=None, signup_details=None, password_change_activity=None, df_last_known_location=None, df_logs=None):
    if df_contacts is not None:
        pass
    if df_media is not None:
        pass
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
        pass
    if df_camera_info is not None:
        pass
    if df_locations_of_interest is not None:
        pass
    if possible_emails is not None:
        pass
    if profile_based_in is not None:
        pass
    if df_link_history is not None:
        df_link_history["Website_name"] = df_link_history["Website_link_you_visited"].apply(
            lambda x: urlparse(x).netloc if pd.notna(x) else None
        )
        df_link_history["session_start"] = pd.to_datetime(
        df_link_history["Website session start time"],
            format="%b %d, %Y %I:%M:%S%p"
        )

        df_link_history["session_end"] = pd.to_datetime(
            df_link_history["Website session end time"],
            format="%b %d, %Y %I:%M:%S%p"
        )

        df_link_history["total_time_min"] = (df_link_history["session_end"] - df_link_history["session_start"]).dt.total_seconds() / 60

        return df_link_history
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
    return (df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs)

