import os
import glob
import pandas as pd
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DATA_PATH = os.getenv("DATA_PATH")
HEADERS = os.getenv("HEADERS")

def safe_load_json(filepath, default=None):
    """
    Safely load a JSON file. Returns default value if file not found or error occurs.
    
    Args:
        filepath: Path to JSON file
        default: Default value to return on error (None by default)
    
    Returns:
        Loaded JSON data or default value
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Warning: Could not load {filepath}: {e}")
        return default if default is not None else {}

def safe_json_normalize(data, **kwargs):
    """Safely normalize JSON data, return empty DataFrame on error."""
    try:
        if not data:
            return pd.DataFrame()
        return pd.json_normalize(data, **kwargs)
    except Exception as e:
        print(f"⚠️ Error normalizing data: {e}")
        return pd.DataFrame()

def load_follows_type(filename, key, follows_type_name, username_field='value'):
    """Helper to load a specific follows type with error handling."""
    try:
        data = safe_load_json(f'{DATA_PATH}/connections/followers_and_following/{filename}', {key: []})
        df = safe_json_normalize(
            data=data.get(key, []),
            record_path=['string_list_data'],
            meta=['title'] if 'title' in str(data) else None,
            errors='ignore'
        )
        
        if df.empty:
            return pd.DataFrame(columns=['follows_type', 'username', 'timestamp', 'href'])
        
        df['follows_type'] = follows_type_name
        
        # Handle username field
        if username_field == 'title' and 'title' in df.columns:
            df['username'] = df['title']
            df = df.drop(columns=["title"], errors='ignore')
        elif username_field == 'value' and 'value' in df.columns:
            df['username'] = df['value']
            df = df.drop(columns=["value"], errors='ignore')
            
        return df
    except Exception as e:
        print(f"⚠️ Error loading {follows_type_name}: {e}")
        return pd.DataFrame(columns=['follows_type', 'username', 'timestamp', 'href'])

def load_data():
    """Load all Instagram data with error tolerance."""
    
    # --- contacts ---
    try:
        contacts_data = safe_load_json(f'{DATA_PATH}/connections/contacts/synced_contacts.json', {"contacts_contact_info": []})
        df_contacts = safe_json_normalize(contacts_data.get("contacts_contact_info", []), sep='_')
        if not df_contacts.empty:
            df_contacts = df_contacts.applymap(lambda x: x.get('value') if isinstance(x, dict) else x)
    except Exception as e:
        print(f"⚠️ Error loading contacts: {e}")
        df_contacts = pd.DataFrame()

    # --- followers_and_following ---
    df_restricted_profiles = load_follows_type('restricted_profiles.json', 'relationships_restricted_users', 'restricted_profiles')
    df_removed_suggestions = load_follows_type('removed_suggestions.json', 'relationships_dismissed_suggested_users', 'removed_suggestions')
    df_recently_unfollowed_profiles = load_follows_type('recently_unfollowed_profiles.json', 'relationships_unfollowed_users', 'recently_unfollowed_profiles')
    df_recent_follow_requests = load_follows_type('recent_follow_requests.json', 'relationships_permanent_follow_requests', 'recent_follow_requests')
    df_pending_follow_requests = load_follows_type('pending_follow_requests.json', 'relationships_follow_requests_sent', 'pending_follow_requests')
    df_following = load_follows_type('following.json', 'relationships_following', 'followings', 'title')
    df_followers = load_follows_type('followers_1.json', '', 'followers')
    df_close_friends = load_follows_type('close_friends.json', 'relationships_close_friends', 'close_friends')
    df_blocked_profiles = load_follows_type('blocked_profiles.json', 'relationships_blocked_users', 'blocked_profiles', 'title')

    df_follows = pd.concat([
        df_blocked_profiles,
        df_close_friends,
        df_followers,
        df_following,
        df_recently_unfollowed_profiles,
        df_removed_suggestions,
        df_recent_follow_requests,
        df_restricted_profiles,
        df_pending_follow_requests
    ], ignore_index=True)

    # --- media ---
    try:
        media_files = glob.glob(f'{DATA_PATH}/media/**/*.*', recursive=True)
        media_root = Path(f'{DATA_PATH}/media')
        
        pat = re.compile(
            r"""
            /media/
            (?P<media_type>[^/]+)
            /
            (?P<timestamp>\d{6})
            /
            [^/]+\.(?P<ext>jpg|jpeg|png|mp4|mov|json|gif|webp)$
            """,
            re.IGNORECASE | re.VERBOSE
        )
        rows = []

        for f in media_files:
            f = str(f)
            m = pat.search(f)
            try:
                rel = str(Path(f).resolve().relative_to(media_root.resolve()))
            except Exception:
                rel = f.split("/media/")[-1] if "/media/" in f else f

            if m:
                ts = m.group("timestamp")
                rows.append({
                    "media_type": m.group("media_type"),
                    "year": ts[:4],
                    "timestamp": ts,
                    "relative_path": rel
                })
            else:
                rows.append({
                    "media_type": None,
                    "year": None,
                    "timestamp": None,
                    "relative_path": rel
                })

        df_media = pd.DataFrame(rows)
    except Exception as e:
        print(f"⚠️ Error loading media: {e}")
        df_media = pd.DataFrame(columns=['media_type', 'year', 'timestamp', 'relative_path'])

    # --- device information ---
    try:
        devices_data = safe_load_json(f'{DATA_PATH}/personal_information/device_information/devices.json', {"devices_devices": []})
        df_devices = pd.json_normalize([
            {
                "user_agent": d.get("string_map_data", {}).get("User Agent", {}).get("value"),
                "last_login_timestamp": d.get("string_map_data", {}).get("Last Login", {}).get("timestamp")
            }
            for d in devices_data.get("devices_devices", [])
        ])
    except Exception as e:
        print(f"⚠️ Error loading devices: {e}")
        df_devices = pd.DataFrame(columns=['user_agent', 'last_login_timestamp'])

    try:
        camera_data = safe_load_json(f'{DATA_PATH}/personal_information/device_information/camera_information.json', {"devices_camera": []})
        df_camera_info = pd.json_normalize(
            [
                {"key": k, **v}
                for item in camera_data.get("devices_camera", [])
                for k, v in item.get("string_map_data", {}).items()
            ]
        )
    except Exception as e:
        print(f"⚠️ Error loading camera info: {e}")
        df_camera_info = pd.DataFrame()

    # --- information about you ---
    try:
        emails_data = safe_load_json(f'{DATA_PATH}/personal_information/information_about_you/possible_emails.json', {"inferred_data_inferred_emails": [{}]})
        possible_emails = emails_data.get("inferred_data_inferred_emails", [{}])[0].get("string_list_data", [{}])[0].get("value", "N/A")
    except Exception as e:
        print(f"⚠️ Error loading possible emails: {e}")
        possible_emails = "N/A"

    try:
        profile_data = safe_load_json(f'{DATA_PATH}/personal_information/information_about_you/profile_based_in.json', {"inferred_data_primary_location": [{}]})
        profile_based_in = profile_data.get("inferred_data_primary_location", [{}])[0].get("string_map_data", {}).get("City Name", {}).get("value", "N/A")
    except Exception as e:
        print(f"⚠️ Error loading profile location: {e}")
        profile_based_in = "N/A"

    try:
        locations_data = safe_load_json(f'{DATA_PATH}/personal_information/information_about_you/locations_of_interest.json', {"label_values": [{"vec": []}]})
        locations = [item.get('value', '') for item in locations_data.get('label_values', [{}])[0].get('vec', [])]
        df_locations_of_interest = pd.DataFrame({'value': locations})
    except Exception as e:
        print(f"⚠️ Error loading locations of interest: {e}")
        df_locations_of_interest = pd.DataFrame(columns=['value'])

    # --- link history ---
    try:
        link_history_data = safe_load_json(f'{DATA_PATH}/logged_information/link_history/link_history.json', [])
        df_link_history = pd.DataFrame([
            {
                'timestamp': row.get('timestamp'),
                'Website_link_you_visited': next((lv['value'] for lv in row.get('label_values', []) if lv.get('label') == 'Website link you visited'), None),
                'Title of website page you visited': next((lv['value'] for lv in row.get('label_values', []) if lv.get('label') == 'Title of website page you visited'), None),
                'Website session start time': next((lv['value'] for lv in row.get('label_values', []) if lv.get('label') == 'Website session start time'), None),
                'Website session end time': next((lv['value'] for lv in row.get('label_values', []) if lv.get('label') == 'Website session end time'), None),
                'fbid': row.get('fbid')
            }
            for row in link_history_data
        ])
    except Exception as e:
        print(f"⚠️ Error loading link history: {e}")
        df_link_history = pd.DataFrame(columns=['timestamp', 'Website_link_you_visited', 'Title of website page you visited', 'Website session start time', 'Website session end time', 'fbid'])

    # --- preferences (recommended topics) ---
    try:
        topics_data = safe_load_json(f'{DATA_PATH}/preferences/your_topics/recommended_topics.json', {"topics_your_topics": []})
        df_recommended_topic = pd.DataFrame([
            {
                'href': topic.get('string_map_data', {}).get('Name', {}).get('href', ''),
                'value': topic.get('string_map_data', {}).get('Name', {}).get('value', ''),
                'timestamp': topic.get('string_map_data', {}).get('Name', {}).get('timestamp', 0)
            }
            for topic in topics_data.get('topics_your_topics', [])
        ])
        recommended_topics = df_recommended_topic['value'].tolist() if not df_recommended_topic.empty else []
    except Exception as e:
        print(f"⚠️ Error loading recommended topics: {e}")
        recommended_topics = []

    # --- security & login information ---
    try:
        signup_data = safe_load_json(f'{DATA_PATH}/security_and_login_information/login_and_profile_creation/signup_details.json', {"account_history_registration_info": [{"string_map_data": {}}]})
        data = signup_data.get('account_history_registration_info', [{}])[0].get('string_map_data', {})
        signup_details = {
            'Username': data.get('Username', {}).get('value', 'N/A'),
            'IP Address': data.get('IP Address', {}).get('value', 'N/A'),
            'Time': data.get('Time', {}).get('timestamp', 0),
            'Email': data.get('Email', {}).get('value', 'N/A'),
            'Phone Number': data.get('Phone Number', {}).get('value', 'N/A'),
            'Device': data.get('Device', {}).get('value', 'N/A')
        }
    except Exception as e:
        print(f"⚠️ Error loading signup details: {e}")
        signup_details = {'Username': 'N/A', 'IP Address': 'N/A', 'Time': 0, 'Email': 'N/A', 'Phone Number': 'N/A', 'Device': 'N/A'}

    try:
        password_data = safe_load_json(f'{DATA_PATH}/security_and_login_information/login_and_profile_creation/password_change_activity.json', {"account_history_password_change_history": []})
        password_change_activity = [x.get('string_map_data', {}).get('Time', {}) for x in password_data.get('account_history_password_change_history', [])]
    except Exception as e:
        print(f"⚠️ Error loading password change activity: {e}")
        password_change_activity = []

    try:
        location_data = safe_load_json(f'{DATA_PATH}/security_and_login_information/login_and_profile_creation/last_known_location.json', {"account_history_imprecise_last_known_location": [{"string_map_data": {}}]})
        location_info = location_data.get("account_history_imprecise_last_known_location", [{}])[0].get("string_map_data", {})
        df_last_known_location = pd.DataFrame([{
            "imprecise_latitude": location_info.get("Imprecise Latitude", {}).get("value", 0),
            "imprecise_longitude": location_info.get("Imprecise Longitude", {}).get("value", 0),
            "lat": location_info.get("Precise Latitude", {}).get("value", 0),
            "longitude": location_info.get("Precise Longitude", {}).get("value", 0),
            "gps_time_uploaded": location_info.get("GPS Time Uploaded", {}).get("timestamp", 0)
        }])
    except Exception as e:
        print(f"⚠️ Error loading last known location: {e}")
        df_last_known_location = pd.DataFrame(columns=['imprecise_latitude', 'imprecise_longitude', 'lat', 'longitude', 'gps_time_uploaded'])

    # --- login/logout logs ---
    try:
        login_data = safe_load_json(f'{DATA_PATH}/security_and_login_information/login_and_profile_creation/login_activity.json', {"account_history_login_history": []})
        df_login = pd.DataFrame([{
            "log_type": "login",
            "cookie_name": d.get("string_map_data", {}).get("Cookie Name", {}).get("value", ""),
            "ip_address": d.get("string_map_data", {}).get("IP Address", {}).get("value", ""),
            "port": d.get("string_map_data", {}).get("Port", {}).get("value", ""),
            "language": d.get("string_map_data", {}).get("Language Code", {}).get("value", ""),
            "timestamp": d.get("string_map_data", {}).get("Time", {}).get("timestamp", 0),
            "user_agent": d.get("string_map_data", {}).get("User Agent", {}).get("value", "")
        } for d in login_data.get("account_history_login_history", [])])
    except Exception as e:
        print(f"⚠️ Error loading login activity: {e}")
        df_login = pd.DataFrame(columns=["log_type", "cookie_name", "ip_address", "port", "language", "timestamp", "user_agent"])

    try:
        logout_data = safe_load_json(f'{DATA_PATH}/security_and_login_information/login_and_profile_creation/logout_activity.json', {"account_history_logout_history": []})
        df_logout = pd.DataFrame([{
            "log_type": "logout",
            "cookie_name": d.get("string_map_data", {}).get("Cookie Name", {}).get("value", ""),
            "ip_address": d.get("string_map_data", {}).get("IP Address", {}).get("value", ""),
            "port": d.get("string_map_data", {}).get("Port", {}).get("value", ""),
            "language": d.get("string_map_data", {}).get("Language Code", {}).get("value", ""),
            "timestamp": d.get("string_map_data", {}).get("Time", {}).get("timestamp", 0),
            "user_agent": d.get("string_map_data", {}).get("User Agent", {}).get("value", "")
        } for d in logout_data.get("account_history_logout_history", [])])
    except Exception as e:
        print(f"⚠️ Error loading logout activity: {e}")
        df_logout = pd.DataFrame(columns=["log_type", "cookie_name", "ip_address", "port", "language", "timestamp", "user_agent"])

    df_logs = pd.concat([df_login, df_logout], ignore_index=True)

    # --- ads information ---
    try:
        advertisers_enriched = pd.read_csv('./data/advertisers_enriched.csv')
    except Exception as e:
        print(f"⚠️ Error loading enriched advertisers: {e}")
        advertisers_enriched = pd.DataFrame()

    # Load all ads data with error handling...
    # (continuing in next message due to length)
    
    # For now, return placeholder for remaining data
    df_all_ads = pd.DataFrame(columns=['author', 'timestamp', 'ads_type', 'date'])
    information_youve_submitted_to_advertisers = []
    substriction_status = "N/A"
    advertisers_using_your_activity_or_information = pd.DataFrame()
    other_categories_used_to_reach_you = []
    
    df_all_comments = pd.DataFrame(columns=['comment', 'media_owner', 'timestamp', 'comments_type', 'date'])
    df_liked_comments = pd.DataFrame(columns=['href', 'timestamp', 'comment_owner'])
    df_liked_posts = pd.DataFrame(columns=['href', 'timestamp', 'media_owner'])
    df_all_conversations = pd.DataFrame(columns=['conv_name', 'participants', 'count_total_interaction', 'count_total_link_shared', 'count_total_reel_sent', 'participants_participation', 'timestamps', 'message_type'])
    df_time_spent_on_ig = pd.DataFrame(columns=['session_timestamp', 'update_time', 'start_time', 'end_time', 'duration_sec'])
    df_your_information_download_requests = {'download_count': 0, 'timestamps': []}
    df_saved_collections = pd.DataFrame(columns=['title', 'value', 'href', 'creation_time', 'update_time', 'added_time', 'saved_type'])
    df_saved_locations = pd.DataFrame(columns=['value', 'timestamp', 'lat', 'lon', 'saved_type'])
    df_saved_posts = pd.DataFrame(columns=['media_owner', 'href', 'timestamp', 'saved_type'])
    df_saved_music = pd.DataFrame()
    df_story_likes = pd.DataFrame()

    return (df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs, df_all_ads, substriction_status, information_youve_submitted_to_advertisers, advertisers_using_your_activity_or_information, other_categories_used_to_reach_you, advertisers_enriched,
            df_all_comments, df_liked_comments, df_liked_posts, df_all_conversations,
            df_time_spent_on_ig, df_your_information_download_requests, 
            df_saved_collections, df_saved_locations, df_saved_posts, df_saved_music,
            df_story_likes)

def fetch_and_cache():
    return

def pwd():
    return os.getcwd()
