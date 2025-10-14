import os
import glob
import pandas as pd
import json
import re
from dotenv import load_dotenv
load_dotenv()
DATA_PATH = os.getenv("DATA_PATH")

def load_data():
    # --- contacts ---
    df_contacts = pd.json_normalize(json.load(open(DATA_PATH+'/connections/contacts/synced_contacts.json'))["contacts_contact_info"], sep='_').applymap(lambda x: x.get('value') if isinstance(x, dict) else x)

    # --- followers_and_following ---
    df_restricted_profiles = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/restricted_profiles.json'))["relationships_restricted_users"],
        record_path=['string_list_data'],
        #meta=['title'], #pour garder le titre si besoin
        errors='ignore'
    )
    df_restricted_profiles['follows_type'] = 'restricted_profiles'
    df_restricted_profiles['username'] = df_restricted_profiles['value']
    df_restricted_profiles = df_restricted_profiles.drop(columns=["value"], axis=1)

    df_removed_suggestions = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/removed_suggestions.json'))['relationships_dismissed_suggested_users'],
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_removed_suggestions['follows_type'] = 'removed_suggestions'
    df_removed_suggestions['username'] = df_removed_suggestions['value']
    df_removed_suggestions = df_removed_suggestions.drop(columns=["value"], axis=1)

    df_recently_unfollowed_profiles = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/recently_unfollowed_profiles.json'))['relationships_unfollowed_users'],
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_recently_unfollowed_profiles['follows_type'] = 'recently_unfollowed_profiles'
    df_recently_unfollowed_profiles['username'] = df_recently_unfollowed_profiles['value']
    df_recently_unfollowed_profiles = df_recently_unfollowed_profiles.drop(columns=["value"], axis=1)

    df_recent_follow_requests = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/recent_follow_requests.json'))['relationships_permanent_follow_requests'],
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_recent_follow_requests['follows_type'] = 'recent_follow_requests'
    df_recent_follow_requests['username'] = df_recent_follow_requests['value']
    df_recent_follow_requests = df_recent_follow_requests.drop(columns=["value"], axis=1)

    df_pending_follow_requests = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/pending_follow_requests.json'))['relationships_follow_requests_sent'],
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_pending_follow_requests['follows_type'] = 'pending_follow_requests'
    df_pending_follow_requests['username'] = df_pending_follow_requests['value']
    df_pending_follow_requests = df_pending_follow_requests.drop(columns=["value"], axis=1)
   
    df_following = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/following.json'))['relationships_following'],
        record_path=['string_list_data'],
        meta=['title'],
        errors='ignore'
    )
    df_following['follows_type'] = 'followings'
    df_following['username'] = df_following['title']
    df_following = df_following.drop(columns=["title"], axis=1)

    df_followers = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/followers_1.json')),
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_followers['follows_type'] = 'followers'
    df_followers['username'] = df_followers['value']
    df_followers = df_followers.drop(columns=["value"], axis=1)

    df_close_friends = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/close_friends.json'))['relationships_close_friends'],
        record_path=['string_list_data'],
        errors='ignore'
    )
    df_close_friends['follows_type'] = 'close_friends'
    df_close_friends['username'] = df_close_friends['value']
    df_close_friends = df_close_friends.drop(columns=["value"], axis=1)

    df_blocked_profiles = pd.json_normalize(
        data=json.load(open(DATA_PATH+'/connections/followers_and_following/blocked_profiles.json'))['relationships_blocked_users'],
        record_path=['string_list_data'],
        meta=['title'],
        errors='ignore'
    )
    df_blocked_profiles['follows_type'] = 'blocked_profiles'
    df_blocked_profiles['username'] = df_blocked_profiles['title']
    df_blocked_profiles = df_blocked_profiles.drop(columns=["title"], axis=1)

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
    media_files = glob.glob(DATA_PATH+'/media/**/*.*', recursive=True)
    
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
        # chemin relatif à "../media"
        try:
            rel = str(Path(f).resolve().relative_to(media_root.resolve()))
        except Exception:
            # fallback si le resolve/relative_to échoue
            # on coupe à "media/"
            rel = f.split("/media/")[-1]

        if m:
            ts = m.group("timestamp")        # ex: "202404"
            rows.append({
                "media_type": m.group("media_type"),
                "year": ts[:4],
                "timestamp": ts,             # garde "YYYYMM" (string) — pratique pour trier
                "relative_path": rel
            })
        else:
            # si le chemin ne suit pas le pattern, on met None (tu pourras filtrer ensuite)
            rows.append({
                "media_type": None,
                "year": None,
                "timestamp": None,
                "relative_path": rel
            })

    df_media = pd.DataFrame(rows)

    # --- device information ---
    df_devices = pd.json_normalize([
        {
            "user_agent": d["string_map_data"].get("User Agent", {}).get("value"),
            "last_login_timestamp": d["string_map_data"].get("Last Login", {}).get("timestamp")
        }
        for d in json.load(open(DATA_PATH+'/personal_information/device_information/devices.json'))["devices_devices"]
    ])

    df_camera_info = pd.json_normalize(
        [
            {"key": k, **v}
            for item in json.load(open(DATA_PATH+'/personal_information/device_information/camera_information.json'))["devices_camera"]
            for k, v in item["string_map_data"].items()
        ]
    )

    # --- information about you ---
    possible_emails = json.load(open(DATA_PATH+'/personal_information/information_about_you/possible_emails.json'))['inferred_data_inferred_emails'][0]['string_list_data'][0]['value']
    profile_based_in = json.load(open(DATA_PATH+'/personal_information/information_about_you/profile_based_in.json'))['inferred_data_primary_location'][0]['string_map_data']['City Name']['value']
    with open(DATA_PATH+'/personal_information/information_about_you/locations_of_interest.json') as f:
        data = json.load(f)
    locations = [item['value'] for item in data['label_values'][0]['vec']]
    df_locations_of_interest = pd.DataFrame({'value': locations})

    # --- logged_information ---
    df_link_history = pd.DataFrame([
    {
        'timestamp': row['timestamp'],
        'Website_link_you_visited': next((lv['value'] for lv in row['label_values'] if lv['label'] == 'Website link you visited'), None),
        'Title of website page you visited': next((lv['value'] for lv in row['label_values'] if lv['label'] == 'Title of website page you visited'), None),
        'Website session start time': next((lv['value'] for lv in row['label_values'] if lv['label'] == 'Website session start time'), None),
        'Website session end time': next((lv['value'] for lv in row['label_values'] if lv['label'] == 'Website session end time'), None),
        'fbid': row['fbid']
    }
    for row in json.load(open(DATA_PATH+'/logged_information/link_history/link_history.json'))
    ])

    # --- preferences ---
    with open(DATA_PATH+'/preferences/your_topics/recommended_topics.json') as f:
        data = json.load(f)

    df_recommended_topic = pd.DataFrame([
        {
            'href': topic['string_map_data']['Name'].get('href', ''),
            'value': topic['string_map_data']['Name'].get('value', ''),
            'timestamp': topic['string_map_data']['Name'].get('timestamp', 0)
        }
        for topic in data['topics_your_topics']
    ])
    recommended_topics = df_recommended_topic['value'].tolist()

    # --- security ---
    data = json.load(open(DATA_PATH+'/security_and_login_information/login_and_profile_creation/signup_details.json'))['account_history_registration_info'][0]['string_map_data']
    signup_details = {
        'Username': data['Username']['value'],
        'IP Address': data['IP Address']['value'],
        'Time': data['Time']['timestamp'],
        'Email': data['Email']['value'],
        'Phone Number': data['Phone Number']['value'],
        'Device': data['Device']['value']
    }

    data = json.load(open(DATA_PATH+'/security_and_login_information/login_and_profile_creation/password_change_activity.json'))['account_history_password_change_history']
    password_change_activity = [x['string_map_data']['Time'] for x in data]


    location_info = json.load(open(DATA_PATH+'/security_and_login_information/login_and_profile_creation/last_known_location.json'))["account_history_imprecise_last_known_location"][0]["string_map_data"]

    df_last_known_location = pd.DataFrame([{
        "imprecise_latitude": location_info["Imprecise Latitude"]["value"],
        "imprecise_longitude": location_info["Imprecise Longitude"]["value"],
        "precise_latitude": location_info["Precise Latitude"]["value"],
        "precise_longitude": location_info["Precise Longitude"]["value"],
        "gps_time_uploaded": location_info["GPS Time Uploaded"]["timestamp"]
    }])


    login_data = json.load(open(DATA_PATH+'/security_and_login_information/login_and_profile_creation/login_activity.json'))["account_history_login_history"]
    df_login = pd.DataFrame([{
        "log_type": "login",
        "cookie_name": d["string_map_data"]["Cookie Name"]["value"],
        "ip_address": d["string_map_data"]["IP Address"]["value"],
        "port": d["string_map_data"]["Port"]["value"],
        "language": d["string_map_data"]["Language Code"]["value"],
        "timestamp": d["string_map_data"]["Time"]["timestamp"],
        "user_agent": d["string_map_data"]["User Agent"]["value"]
    } for d in login_data])

    logout_data = json.load(open(DATA_PATH+'/security_and_login_information/login_and_profile_creation/logout_activity.json'))["account_history_logout_history"]
    df_logout = pd.DataFrame([{
        "log_type": "logout",
        "cookie_name": d["string_map_data"]["Cookie Name"]["value"],
        "ip_address": d["string_map_data"]["IP Address"]["value"],
        "port": d["string_map_data"]["Port"]["value"],
        "language": d["string_map_data"]["Language Code"]["value"],
        "timestamp": d["string_map_data"]["Time"]["timestamp"],
        "user_agent": d["string_map_data"]["User Agent"]["value"]
    } for d in logout_data])

    df_logs = pd.concat([df_login, df_logout], ignore_index=True)

    return (df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs)

def fetch_and_cache():
    return

def pwd():
    return os.getcwd()


license_txt = 'this is my license'