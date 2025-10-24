import os
import glob
import pandas as pd
import json
import re
from dotenv import load_dotenv
load_dotenv()
DATA_PATH = os.getenv("DATA_PATH")
HEADERS = os.getenv("HEADERS")

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
        "lat": location_info["Precise Latitude"]["value"],
        "longitude": location_info["Precise Longitude"]["value"],
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

    # ---- ads infos -----
    advertisers_enriched = pd.read_csv('./data/advertisers_enriched.csv')

    videos_watched = pd.json_normalize(
        data = json.load(open(DATA_PATH+'/ads_information/ads_and_topics/videos_watched.json'))['impressions_history_videos_watched'],
        sep='.'
    )

    videos_watched = videos_watched.rename(columns={
        'string_map_data.Author.value': 'author',
        'string_map_data.Time.timestamp': 'timestamp'
    })[['author', 'timestamp']]
    videos_watched['ads_type'] = 'videos_watched'

    suggested_profiles_viewed = pd.json_normalize(
        data = json.load(open(DATA_PATH+'/ads_information/ads_and_topics/suggested_profiles_viewed.json'))['impressions_history_chaining_seen'],
        sep='.'
    )
    suggested_profiles_viewed = suggested_profiles_viewed.rename(columns={
        'string_map_data.Username.value': 'username',
        'string_map_data.Time.timestamp': 'timestamp'
    })[['username', 'timestamp']]
    suggested_profiles_viewed['ads_type'] = 'suggested_profiles'
    suggested_profiles_viewed = suggested_profiles_viewed.rename(columns={'username': 'author'})

    posts_viewed = pd.json_normalize(
        data = json.load(open(DATA_PATH+'/ads_information/ads_and_topics/posts_viewed.json'))['impressions_history_posts_seen'],
        sep='.'
    )
    posts_viewed = posts_viewed.rename(columns={
        'string_map_data.Author.value': 'author',
        'string_map_data.Time.timestamp': 'timestamp'
    })[['author', 'timestamp']]
    posts_viewed['ads_type'] = 'posts'

    ads_clicked = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/ads_information/ads_and_topics/ads_clicked.json'
        ))['impressions_history_ads_clicked'],
        sep='.'
    )
    ads_clicked['timestamp'] = ads_clicked['string_list_data'].apply(lambda x: x[0]['timestamp'])
    ads_clicked = ads_clicked.drop(columns=['string_list_data'])
    ads_clicked = ads_clicked.rename(columns={'title': 'author'})
    ads_clicked['ads_type'] = 'clicked'

    ads_viewed = pd.json_normalize(
        data = json.load(open(DATA_PATH+'/ads_information/ads_and_topics/ads_viewed.json'))['impressions_history_ads_seen'],
        sep='.'
    )
    ads_viewed = ads_viewed.rename(columns={
        'string_map_data.Author.value': 'author',
        'string_map_data.Time.timestamp': 'timestamp'
    })[['author', 'timestamp']]
    ads_viewed['ads_type'] = 'viewed'

    df_all_ads = pd.concat(
        [
            videos_watched[['author', 'timestamp', 'ads_type']],
            suggested_profiles_viewed[['author', 'timestamp', 'ads_type']],
            posts_viewed[['author', 'timestamp', 'ads_type']],
            ads_clicked[['author', 'timestamp', 'ads_type']],
            ads_viewed[['author', 'timestamp', 'ads_type']]
        ],
        ignore_index=True
    )

    df_all_ads['date'] = (
        pd.to_datetime(df_all_ads['timestamp'], unit='s', utc=True)
        .dt.tz_convert('Europe/Paris')
    )

    information_youve_submitted_to_advertisers = json.load(open(DATA_PATH+"/ads_information/instagram_ads_and_businesses/information_you've_submitted_to_advertisers.json"))['ig_lead_gen_info']
    substriction_status = json.load(open(DATA_PATH+'/ads_information/instagram_ads_and_businesses/subscription_for_no_ads.json'))['label_values'][0]['value']

    advertisers_using_your_activity_or_information = pd.json_normalize(
            data = json.load(open(DATA_PATH+'/ads_information/instagram_ads_and_businesses/advertisers_using_your_activity_or_information.json')),
            record_path=['ig_custom_audiences_all_types'],
            errors='ignore'
    )

    data = json.load(open(DATA_PATH+'/ads_information/instagram_ads_and_businesses/other_categories_used_to_reach_you.json'))
    other_categories_used_to_reach_you = [item["value"] for item in data["label_values"][0]["vec"]]


    # --------- your activity ----------------
    reel_comments = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/comments/reels_comments.json'
        ))['comments_reels_comments'],
        sep='.'
    )[[
        'string_map_data.Comment.value',
        'string_map_data.Media Owner.value',
        'string_map_data.Time.timestamp'
    ]]
    reel_comments.columns = ['comment', 'media_owner', 'timestamp']
    reel_comments['comments_type'] = 'reel'

    post_comments = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/comments/post_comments_1.json'
        )),
        sep='.'
    )[[
        'string_map_data.Comment.value',
        'string_map_data.Media Owner.value',
        'string_map_data.Time.timestamp'
    ]]
    post_comments.columns = ['comment', 'media_owner', 'timestamp']
    
    post_comments['comments_type'] = 'post'

    df_all_comments = pd.concat(
        [
            reel_comments,
            post_comments
        ],
        ignore_index=True
    )

    df_all_comments['date'] = (
        pd.to_datetime(df_all_comments['timestamp'], unit='s', utc=True)
        .dt.tz_convert('Europe/Paris')
    )

    df_liked_comments = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/likes/liked_comments.json'
        ))['likes_comment_likes'],
        sep='.',
        record_path='string_list_data',
        meta='title'
    )
    df_liked_comments.drop(['value'], axis=1, inplace=True)
    df_liked_comments.columns = ['href', 'timestamp', 'comment_owner']
    
    df_liked_posts = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/likes/liked_posts.json'
        ))['likes_media_likes'],
        sep='.',
        record_path='string_list_data',
        meta='title'
    )
    df_liked_posts.drop(['value'], axis=1, inplace=True)
    df_liked_posts.columns = ['href', 'timestamp', 'media_owner']

    messages_folders = glob.glob(DATA_PATH+'/your_instagram_activity/messages/inbox/*', recursive=True)
    conversation_inbox_df = pd.DataFrame(columns=['conv_name','participants', 'count_total_interaction', 'count_total_link_shared','count_total_reel_sent','participants_participation','timestamps'])

    def count_total(participants, messages):
        count_participants = { x:0 for x in participants}
        count_has_linked = 0
        count_has_reel_linked = 0
        all_timestamp = []
        for message in messages:
            link = None
            share = message.get("share")
            if isinstance(share, dict):
                link = share.get("link")

            if link:
                sender = message.get("sender_name")
                if sender in count_participants:
                    count_participants[sender] += 1
                else:
                    count_participants.setdefault(sender, 0)
                    count_participants[sender] += 1
                count_has_linked+=1
                if re.search( '^https://www.instagram.com/reel/*', message['share']['link']):
                    count_has_reel_linked+=1
            all_timestamp.append(message['timestamp_ms'])
        return count_participants, count_has_linked, count_has_reel_linked, all_timestamp

    for conv_path in messages_folders:
        data=json.load(open(
            conv_path+'/message_1.json'
        ))
        count_participants, count_has_linked, count_has_reel_linked, all_timestamp = count_total([x["name"] for x in data['participants']], data['messages'])

        new_row = {
            'conv_name':'',
            'participants':[x["name"] for x in data['participants']],
            'count_total_interaction': len(data['messages']),
            'count_total_link_shared': count_has_linked,
            'count_total_reel_sent': count_has_reel_linked,
            'participants_participation': count_participants,
            'timestamps': all_timestamp,
        }
        conversation_inbox_df.loc[len(conversation_inbox_df)] = new_row

    conversation_inbox_df['message_type'] = 'message_inbox'
   
    messages_folders = glob.glob(DATA_PATH+'/your_instagram_activity/messages/message_requests/*', recursive=True)
    conversation_request_df = pd.DataFrame(columns=['conv_name','participants', 'count_total_interaction', 'count_total_link_shared','count_total_reel_sent','participants_participation','timestamps'])

    for conv_path in messages_folders:
        data=json.load(open(
            conv_path+'/message_1.json'
        ))
        count_participants, count_has_linked, count_has_reel_linked, all_timestamp = count_total([x["name"] for x in data['participants']], data['messages'])

        new_row = {
            'conv_name':'',
            'participants':[x["name"] for x in data['participants']],
            'count_total_interaction': len(data['messages']),
            'count_total_link_shared': count_has_linked,
            'count_total_reel_sent': count_has_reel_linked,
            'participants_participation': count_participants,
            'timestamps': all_timestamp,
        }
        
        conversation_request_df.loc[len(conversation_request_df)] = new_row

    conversation_request_df['message_type'] = 'message_requests'

    df_all_conversations = pd.concat([
        conversation_request_df,
        conversation_inbox_df
    ])

    data = json.load(open(DATA_PATH+'/your_instagram_activity/other_activity/time_spent_on_instagram.json'))

    rows = []
    for session in data:
        session_ts = session.get("timestamp")

        update_time = None
        intervals = []
        for item in session.get("label_values", []):
            if item.get("label") == "Update time":
                update_time = item.get("timestamp_value")
            elif item.get("label") == "Intervals":
                intervals = item.get("vec", [])

        for interval in intervals:
            d = interval.get("dict", [])
            start = end = None
            for kv in d:
                if kv.get("label") == "Start time":
                    start = kv.get("timestamp_value")
                elif kv.get("label") == "End time":
                    end = kv.get("timestamp_value")
            if start is not None and end is not None:
                rows.append({
                    "session_timestamp": session_ts,
                    "update_time": update_time,
                    "start_time": start,
                    "end_time": end
                })
    df_time_spent_on_ig = pd.DataFrame(rows)
    for col in ["session_timestamp", "update_time", "start_time", "end_time"]:
        df_time_spent_on_ig[col] = pd.to_datetime(df_time_spent_on_ig[col], unit="s", utc=True)
    df_time_spent_on_ig["duration_sec"] = (df_time_spent_on_ig["end_time"] - df_time_spent_on_ig["start_time"]).dt.total_seconds()

    data=json.load(open(
        DATA_PATH+'/your_instagram_activity/other_activity/your_information_download_requests.json'
    ))
    df_your_information_download_requests = {'download_count':len(data), 'timestamps':[x['timestamp'] for x in data]}

    data = json.load(open(
        DATA_PATH+'/your_instagram_activity/saved/saved_collections.json'
    ))['saved_saved_collections']

    def pick(ts_dict):
        return (ts_dict or {}).get("timestamp")

    def extract(row):
        smd = row.get("string_map_data", {}) or {}
        name = smd.get("Name", {}) or {}
        return {
            "title": row.get("title"),
            "value": name.get("value"),
            "href": name.get("href"),
            "creation_time": pick(smd.get("Creation Time")),
            "update_time": pick(smd.get("Update Time")),
            "added_time": pick(smd.get("Added Time")),
        }

    df_saved_collections = pd.DataFrame([extract(r) for r in data])
    for c in ["creation_time", "update_time", "added_time"]:
        df_saved_collections[c] = pd.to_datetime(df_saved_collections[c], unit="s", utc=True, errors="coerce")

    df_saved_collections["saved_type"] = "saved_collections"

    df_saved_locations = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/saved/saved_locations.json'
        ))['saved_saved_locations'][0]['string_map_data'],
        sep='.',
    )
    df_saved_locations.drop(['Name.href','Name.timestamp','Saved At.href','Saved At.value','Latitude.timestamp','Latitude.href','Longitude.href','Longitude.timestamp'], axis=1, inplace=True)
    df_saved_locations.columns = ['value', 'timestamp', 'lat','lon']
    df_saved_locations['saved_type'] = 'saved_locations'

    df_saved_posts = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/saved/saved_posts.json'
        ))['saved_saved_media'],
        sep='.',
        meta='title'
    )
    df_saved_posts.columns = ['media_owner', 'href', 'timestamp']
    df_saved_posts['saved_type'] = 'saved_posts'

    df_saved_music = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/saved/saved_music.json'
        ))['saved_saved_music'],
        sep='.',
    )

    df_story_likes = pd.json_normalize(
        data=json.load(open(
            DATA_PATH+'/your_instagram_activity/story_interactions/story_likes.json'
        ))['story_activities_story_likes'],
        sep='.',
        meta='title',
        record_path='string_list_data'
    )

    return (df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs, df_all_ads, substriction_status, information_youve_submitted_to_advertisers, advertisers_using_your_activity_or_information, other_categories_used_to_reach_you, advertisers_enriched,
            df_all_comments, df_liked_comments, df_liked_posts, df_all_conversations,
            df_time_spent_on_ig, df_your_information_download_requests, 
            df_saved_collections, df_saved_locations, df_saved_posts, df_saved_music,
            df_story_likes )

def fetch_and_cache():
    return

def pwd():
    return os.getcwd()


license_txt = 'this is my license'