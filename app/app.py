import streamlit as st
from math import ceil
from pathlib import Path
from utils.io import load_data, DATA_PATH
from utils.prep import preprocess_data, date_str, count_user_messages
from utils.w2v_model import generate_clusters
from utils.data_enrichement import enrich_companies
from utils.viz.activities import total_activities_over_time, plot_duo_participation, group_vs_duo_conv_pie, plot_duo_reel_vs_nonreel, request_corr0, scroll_hist, saved_media_by_time, website_bar
from utils.viz.media import media_cumulative_line, media_type_bar, media_frequency_histogram
from utils.viz.ads import ads_bar, ads_countries_map, ads_enriched_missing_values, ads_inception_year
from utils.viz.preferences import clusters_podium, clusters_grid
from utils.viz.security import login_logout_hist, cookies_pie, password_activity_bar
from utils.viz.connections import upset, plot_venn, plot_follow_time_series_altair, follows_pie
from utils.viz.personal_info import devices_over_times

st.set_page_config(page_title="Data Storytelling Dashboard", layout="wide")

@st.cache_data(show_spinner="Loading your data...")
def get_data():
    return load_data()

@st.cache_data(show_spinner="Preprocessing your data...")
def preprocess_all_data(df_follows, df_contacts, df_media, df_link_history, df_locations_of_interest, df_last_known_location, df_devices, df_all_conversations, df_time_spent_on_ig):
    """Cache preprocessing to avoid re-execution on every interaction"""
    clean_follows = preprocess_data(df_follows=df_follows)
    clean_contacts = preprocess_data(df_contacts=df_contacts)
    df_media_prep = preprocess_data(df_media=df_media)
    df_link_history_prep = preprocess_data(df_link_history=df_link_history)
    df_locations_of_interest_prep = preprocess_data(df_locations_of_interest=df_locations_of_interest)
    df_last_known_location_prep = preprocess_data(df_last_known_location=df_last_known_location)
    df_devices_prep = preprocess_data(df_devices=df_devices)
    df_time_spent_on_ig_prep = preprocess_data(df_time_spent_on_ig=df_time_spent_on_ig)
    messages_sent, messages_received = count_user_messages(df_all_conversations)
    return clean_follows, clean_contacts, df_media_prep, df_link_history_prep, df_locations_of_interest_prep, df_last_known_location_prep, df_devices_prep, df_time_spent_on_ig_prep, messages_sent, messages_received

st.title("Personal Instagram Dashboard")

# Load data (spinner handled by @st.cache_data decorator)
(df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs, df_all_ads, substriction_status, information_youve_submitted_to_advertisers, advertisers_using_your_activity_or_information, other_categories_used_to_reach_you, advertisers_enriched,
        df_all_comments, df_liked_comments, df_liked_posts, df_all_conversations,
        df_time_spent_on_ig, df_your_information_download_requests, 
        df_saved_collections, df_saved_locations, df_saved_posts, df_saved_music,
        df_story_likes) = get_data()

# Preprocess data (spinner handled by @st.cache_data decorator)
clean_follows, clean_contacts, df_media_prep, df_link_history_prep, df_locations_of_interest_prep, df_last_known_location, df_devices_prep, df_time_spent_on_ig_prep, messages_sent, messages_received = preprocess_all_data(
    df_follows, df_contacts, df_media, df_link_history, df_locations_of_interest, df_last_known_location, df_devices, df_all_conversations, df_time_spent_on_ig
)

home, connections_tab, media_tab, preferences_tab, activity_tab, ads_tab, personal_info_tab, security_tab = st.tabs(["Welcome !", "Connections", "Media", "Preferences","Your activity", 'Ads Info', "Personnal Information", "Security Insights"])


with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", [])

with home:
    st.markdown("""
    ### Welcome to your personal Instagram data analysis platform!
    
    This interactive dashboard helps you visualize and understand what Meta knows about you through your Instagram data.
    Explore your connections, media, preferences, activities, ads exposure, and more with dynamic visualizations and minimal machine learning.
    """)
    
    st.subheader("Project Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📁 Data Folder Size", f"{sum(f.stat().st_size for f in Path(DATA_PATH).rglob('*') if f.is_file()) / (1024**2):.1f} MB")
    
    with col2:
        total_files = len(list(Path(DATA_PATH).rglob('*')))
        st.metric("Total Files", f"{total_files}")
    
    with col3:
        image_files = len([f for f in Path(DATA_PATH).rglob('*') if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
        st.metric("Images", f"{image_files}")
    

    # Technologies Used
    st.subheader("🛠️ Technologies & Libraries")
    tech_col1, tech_col2 = st.columns(2)
    
    with tech_col1:
        st.markdown("""
        **Data & Visualization**
        - `streamlit` - Interactive dashboards
        - `pandas` - Data manipulation
        - `altair` - Declarative visualizations
        - `matplotlib` - Plotting library
        """)
    
    with tech_col2:
        st.markdown("""
        **Machine Learning**
        - `gensim` - Word2Vec clustering
        - `scikit-learn` - ML algorithms
        - `numpy` - Numerical computing
        """)
    
    tech_col3, tech_col4 = st.columns(2)
    
    with tech_col3:
        st.markdown("""
        **Utilities**
        - `geopy` - Geocoding locations
        - `python-dotenv` - Environment config
        - `matplotlib-venn` - Venn diagrams
        """)

    with tech_col4:
        st.markdown("""
        **Data Enrichment APIs**
        - `Wikidata` - Structured company data
        - `Wikipedia` - Entity identification
        - `Clearbit` - Domain inference
        - `OpenCorporates` - Business registry
        """)
    
    # How to use
    st.subheader("How to Use This Dashboard")
    st.markdown("""
    1. **Connections**: Explore your followers, followings, and contacts relationships
    2. **Media**: Analyze your posts, stories, and media consumption patterns
    3. **Preferences**: Discover your interests through ML clustering
    4. **Your Activity**: Track your interactions, messages, and time spent
    5. **Ads Info**: Understand what advertisers know about you
    6. **Personal Information**: Review your devices, locations, and account details
    7. **Security Insights**: Monitor login activities and security events
    """)
    
    st.info("💡 **Tip**: Use the sidebar filters to refine your analysis by date range.")

with connections_tab:
    
    st.header("Connections")
    with st.expander("Show raw datas"):
        st.write("Followers and Following")
        st.write(df_follows)
        st.write("Contacts")
        st.write(df_contacts)
    
    col1, col2 = st.columns([1,1], gap="large")

    with col1:
        st.subheader("Follows intersect")
        
        # --- controllers ---
        all_groups = sorted(clean_follows["sets_by_type"].keys())
        default_groups = [g for g in ["followings", "followers", "close_friends"] if g in all_groups]
        selected_groups = st.multiselect(
            "Groups for either Venn or UpSet diagram", options=all_groups, default=default_groups
        )

        sets_by_type = clean_follows["sets_by_type"]
        selected = selected_groups if selected_groups else [
            g for g in ["followings", "followers", "close_friends"] if g in sets_by_type
        ]

        non_empty = [g for g in selected if g in sets_by_type and len(sets_by_type[g]) > 0]

        if len(non_empty) < 2:
            st.info("Select at least two non-empty groups.")
        elif 2 <= len(non_empty) <= 3:
            # Venn (2–3 groups)
            fig = plot_venn(sets_by_type, selected_types=non_empty)
            if fig:
                st.pyplot(fig, use_container_width=True)
        else:
            # UpSet-like (≥4 groups) — Altair chart
            chart = upset(sets_by_type, selected_types=non_empty)
            if chart:
                st.altair_chart(chart, use_container_width=True)

        st.caption(
            "Don't be fooled by the number: some follow counts can be duplicated. "
            "E.g., if you blocked the same person twice, it may be counted twice."
        )
    with col2:
        st.subheader("Followers / Followings across time")
        mode = st.radio("Mode", ["Cumulative", "Daily"], horizontal=True)
        cum = (mode == "Cumulative")
        if not clean_follows["timeseries"].empty:
            chart2 = plot_follow_time_series_altair(clean_follows["timeseries"], cumulative=cum, date_range=date_range)
            if chart2:
                st.altair_chart(chart2, use_container_width=True)
        else:
            st.info("📊 No follow/unfollow data available to display.")

    col12, col22 = st.columns([1,1], gap="large")
    with col12: # -- contacts info
        st.subheader("Contacts information")
        contact_count = df_contacts.shape[0] if not df_contacts.empty else 0
        st.write("Total contacts registered by Instagram:", contact_count)
        if contact_count > 0:
            st.write("Among those, you have:")
            phone_count = clean_contacts["phone"].notna().sum() if not clean_contacts.empty else 0
            email_count = clean_contacts["email"].notna().sum() if not clean_contacts.empty else 0
            st.write(f"    - {phone_count} phone numbers registered")
            st.write(f"    - {email_count} emails registered")
        st.caption("Instagram can use this contact list to recommend profiles for you.")
        st.caption("Even you, people can see your profile in their recommendations thanks to your contact information linked to your profile.")
        contact_methods = []
        if signup_details.get('Email') and signup_details['Email'] != 'N/A':
            contact_methods.append(signup_details['Email'])
        if signup_details.get('Phone Number') and signup_details['Phone Number'] != 'N/A':
            contact_methods.append(signup_details['Phone Number'])
        if contact_methods:
            st.caption(f"In your case, people can reach you with: {', '.join(contact_methods)}")
        else:
            st.caption("In your case, no contact information is available for others to reach you.")

    with col22:
        st.subheader("Follow types pie chart")
        if not df_follows.empty:
            chart = follows_pie(df_follows)
            if chart:
                st.altair_chart(chart)
        else:
            st.info("📊 No follow data available.")

with media_tab:
    st.header("Media Dashboard")
    with st.expander("Show raw data"):
        st.write("Media")
        st.write(df_media)
    with st.expander("Show preprocessed data"):
        st.write("Media")
        st.info("This preprocessing step standardizes the media dataset and reconstructs missing information from the file paths." \
            "When only the relative_path is available, the script automatically extracts the media type (e.g. posts, stories, reels), the year, the month, and a normalized timestamp from the folder structure. " \
            "It also adds helper columns such as filename, extension, and a year_month date to make temporal analysis easier.")
        st.write(df_media_prep)
    
    st.header("Insights")
    col1, col2 = st.columns([1,1], gap="large")
    with col1 : 
        st.subheader("Posting over the years")
        if not df_media_prep.empty:
            chart = media_cumulative_line(df_media_prep, date_range=date_range)
            if chart:
                st.altair_chart(chart, use_container_width=True)
            
            posts_count = df_media_prep[df_media_prep["media_type"]=="posts"].shape[0]
            archived_count = df_media_prep[df_media_prep["media_type"]=="archived_posts"].shape[0]
            profile_count = df_media_prep[df_media_prep["media_type"]=="profile"].shape[0]
            stories_count = df_media_prep[df_media_prep["media_type"]=="stories"].shape[0]
            deleted_count = df_media_prep[df_media_prep["media_type"]=="recently_deleted"].shape[0]
            
            st.write(f"You currently have {posts_count} pictures in your posts, {archived_count} archived posts pictures, "
                    f"{profile_count} profile picture, {stories_count} stories and {deleted_count} recently deleted pictures")
        else:
            st.info("📊 No media data available.")
            
    with col2 :
        st.subheader("Media types distribution")
        if not df_media_prep.empty:
            chart = media_type_bar(df_media_prep, date_range=date_range)
            if chart:
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("📊 No media data available.")

    st.subheader("Stories frequencies")
    if not df_media_prep.empty:
        by_stories = st.radio("Grouped by:", ["years","months","weeks"], index=1, horizontal=True, key="stories_hist")
        chart = media_frequency_histogram(df_media_prep, by_stories, date_range=date_range)
        if chart:
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📊 No stories data available.")

    st.subheader("Posts & Archived Posts frequencies")
    if not df_media_prep.empty:
        by_posts = st.radio("Grouped by:", ["years","months","weeks"], index=1, horizontal=True, key="posts_hist")
        chart = media_frequency_histogram(df_media_prep, by_posts, media_type=["archived_posts", "posts"], color='blues', date_range=date_range)
        if chart:
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📊 No posts data available.")

# ------------gallery ---------------
    st.header("Gallery")
    
    if 'show_gallery' not in st.session_state:
        st.session_state['show_gallery'] = False
    
    if st.button("Load your gallery !", type="primary"):
        st.session_state['show_gallery'] = True
    
    if st.session_state['show_gallery']:
        if df_media_prep.empty:
            st.info("📊 No media available for gallery display.")
        else:
            controls = st.columns(4)
            with controls[0]:
                media_types = st.multiselect("Media Types", ["Posts", "Stories", "Archived Posts", "Deleted"], default=["Posts", "Stories"])
            with controls[1]:
                # Extract unique year-months from the 'timestamp' column, sort them
                available_dates = sorted(df_media_prep['timestamp'].unique())
                # Convert to string for display (if not already)
                available_dates = [str(d) for d in available_dates]
                if available_dates:
                    # Use select_slider for date range selection
                    selected_range = st.select_slider(
                        "Date Range:",
                        options=available_dates,
                        value=(available_dates[0], available_dates[-1]),
                        key='date_range'
                    )
                    # Filter df_media_prep based on selected_range
                    df_media_prep_filtered = df_media_prep[
                        (df_media_prep['timestamp'] >= selected_range[0]) &
                        (df_media_prep['timestamp'] <= selected_range[1])
                    ]
                else:
                    df_media_prep_filtered = df_media_prep
                    
            with controls[2]:
                batch_size = st.select_slider("Batch size:", range(10, 110, 10), key='batch_slider')
            
            if df_media_prep_filtered.empty:
                st.info("📊 No media in selected date range.")
            else:
                num_batches = ceil(len(df_media_prep_filtered) / batch_size)

                with controls[3]:
                    page = st.selectbox("Page", range(1, num_batches + 1), key='page')


        def update(image, col):
            df_media_prep_filtered.at[image, col] = st.session_state[f'{col}_{image}']
            if st.session_state[f'incorrect_{image}'] == False:
                st.session_state[f'label_{image}'] = ''
                df_media_prep_filtered.at[image, 'label'] = ''

        batch = df_media_prep_filtered[(page - 1) * batch_size : page * batch_size]
        row_size = 4
        grid = st.columns(row_size)
        col = 0


        # Loop over the batch and display images/videos
        for _, media in batch.iterrows():
            media_path = media['relative_path']
            media_ext = media['ext']
            media_file = f'{DATA_PATH}/media/{media_path}'
            with grid[col]:
                if media_ext in ['jpg', 'jpeg', 'png']:
                    st.image(media_file, caption='Media')
                elif media_ext == 'mp4':
                    st.video(media_file)

            col = (col + 1) % row_size

with activity_tab:
    st.header("Your activity")
    with st.expander("Show raw datas"):
        st.subheader("All comments")
        st.write(df_all_comments)
        st.subheader("Liked comments")
        st.write(df_liked_comments)
        st.subheader("Liked posts")
        st.write(df_liked_posts)
        st.subheader("Your conversations data")
        st.write(df_all_conversations)
        st.subheader("Time spent on instagram")
        st.write(df_time_spent_on_ig)
        st.subheader("Your downloaded information")
        st.write(df_your_information_download_requests)
        st.subheader("Saved collections")
        st.write(df_saved_collections)
        st.subheader("Saved locations")
        st.write(df_saved_locations)
        st.subheader("Saved posts")
        st.write(df_saved_posts)
        st.subheader("Saved music")
        st.write(df_saved_music)
        st.subheader("Story liked")
        st.write(df_story_likes)
        st.write("Link history")
        st.write(df_link_history)
    with st.expander("Show preprocessed datas"):
        st.subheader("Link history")
        st.info("This preprocessing extracts the website name from URLs and calculates session duration in minutes.")
        st.write(df_link_history_prep)
        
        st.subheader("Time spent on Instagram")
        st.info("This preprocessing converts timestamps, adds date column, and calculates duration in minutes for easier analysis.")
        st.write(df_time_spent_on_ig_prep)
    
    st.subheader("Overview")
    c1, c2, c3, c4 = st.columns(4)
    
    hours_spent = df_time_spent_on_ig['duration_sec'].sum() / 3600 if not df_time_spent_on_ig.empty and 'duration_sec' in df_time_spent_on_ig.columns else 0
    likes_count = len(df_liked_posts) if not df_liked_posts.empty else 0
    story_likes_count = len(df_story_likes) if not df_story_likes.empty else 0
    comment_likes_count = len(df_liked_comments) if not df_liked_comments.empty else 0
    
    c1.metric("Hours spent on Instagram", f"{hours_spent:.2f} hours")
    c2.metric("Likes", f"{likes_count}")
    c3.metric("Stories liked", f"{story_likes_count}")
    c4.metric("Likes on comments", f"{comment_likes_count}")

    c21, c22, c23, c24 = st.columns(4)
    comments_count = len(df_all_comments) if not df_all_comments.empty else 0
    download_count = df_your_information_download_requests.get('download_count', 0) if isinstance(df_your_information_download_requests, dict) else 0
    
    c21.metric("Messages sent", f"{messages_sent}")
    c22.metric("Messages received", f"{messages_received}")
    c23.metric("Comments", f"{comments_count}")
    c24.metric("Times you downloaded your data", f"{download_count}")

    st.subheader("Your activities across time")
    mode = st.radio("Mode", ["Cumulative", "Monthly"], horizontal=True)
    cum = (mode == "Cumulative")
    monthly = (mode == "Monthly")

    # Check if we have any activity data
    has_activity_data = any([
        not df_all_comments.empty,
        not df_liked_comments.empty,
        not df_liked_posts.empty,
        not df_story_likes.empty,
        not df_saved_posts.empty,
        not df_all_conversations.empty
    ])
    
    if has_activity_data:
        chart = total_activities_over_time(
            df_all_comments,
            df_liked_comments,
            df_liked_posts,
            df_story_likes,
            df_saved_posts,
            df_all_conversations,
            cumulative=cum,
            monthly=True,
            title="Activities over time",
            use_log_y=True,
            date_range=date_range
        )
        if chart:
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📊 No activity data available to display.")

    st.subheader("Messages & conversations")
    if not df_all_conversations.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.write("Participation in your conversations")
            top_n_participation = st.slider("Top N conversations", 1, 30, 10, key="participations_slider")
            chart = plot_duo_participation(df_all_conversations, top_n_participation)
            if chart:
                st.altair_chart(chart)

            st.write("Group vs duo conversations")
            chart = group_vs_duo_conv_pie(df_all_conversations)
            if chart:
                st.altair_chart(chart)

        with col2:
            st.write("'Reel based' conversations")
            top_n_reel = st.slider("Top N conversations", 1, 30, 10, key="reel_slider")
            chart = plot_duo_reel_vs_nonreel(df_all_conversations, top_n_reel)
            if chart:
                st.altair_chart(chart)
    else:
        st.info("📊 No conversation data available.")
    
    st.subheader("DM requests")
    if not df_all_conversations.empty:
        col21, col22 = st.columns(2)
        with col21:
            fig0 = request_corr0(df_all_conversations)
            if fig0:
                st.pyplot(fig0, use_container_width=True)
        with col22:
            st.info("On Instagram, the requests sent in DMs are often scam or sexual content.\n" \
            "See how the number of participants and the total messages sent can be correlated to the type of messages you received.")
    else:
        st.info("📊 No DM request data available.")
    

    st.subheader("Time spent on Instagram")
    if not df_time_spent_on_ig_prep.empty:
        chart = scroll_hist(df_time_spent_on_ig_prep, date_range=date_range)
        if chart:
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("📊 No time tracking data available.")

    st.subheader("Saved information")
    has_saved_data = any([
        not df_saved_collections.empty,
        not df_saved_posts.empty,
        not df_saved_music.empty
    ])
    
    if has_saved_data:
        by_saved = st.radio("Grouped by:", ["days","months","weeks"], index=1, horizontal=True, key="saved_hist")
        chart = saved_media_by_time(df_saved_collections, df_saved_posts, df_saved_music, by_saved, date_range=date_range)
        if chart:
            st.altair_chart(chart)
    else:
        st.info("📊 No saved content data available.")
    
    saved_c1, saved_c2, saved_c3 = st.columns(3)
    with saved_c1:
        st.write()
    with saved_c2:
        st.write()

    with saved_c3:
        st.write()

    st.subheader("Link history")
    if not df_link_history_prep.empty:
        chart = website_bar(df_link_history_prep)
        if chart:
            st.altair_chart(chart)
    else:
        st.info("📊 No link history data available.")

with preferences_tab:
    st.header("Your recommended topics")
    with st.expander("Show raw data"):
        st.write("Recommended topics")
        st.write(recommended_topics)
    
    if not recommended_topics or len(recommended_topics) == 0:
        st.info("📊 No recommended topics data available.")
    else:
        st.write("Launching the predictions will allow you to see your most frequent categories among your preferences. " \
            "This model is a Clustering ML model based on Word2Vector library using gensim.")
        button_col = st.columns([1, 2, 1])[1]
        with button_col:
            if st.button("🚀 Generate Topic Clusters", type="primary"):
                with st.spinner("Loading Word2Vec model and generating clusters... This may take a moment."):
                    try:
                        cluster_datas, clusters_compositions = generate_clusters(recommended_topics=recommended_topics)
                        st.session_state['cluster_datas'] = cluster_datas
                        st.session_state['clusters_compositions'] = clusters_compositions
                        st.success("✅ Clusters generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating clusters: {e}")

        if 'cluster_datas' in st.session_state and 'clusters_compositions' in st.session_state:
            with st.expander("Show your results"):
                st.subheader("Topic Clusters")
                st.write(st.session_state['cluster_datas'])
                st.subheader("Cluster Compositions")
                st.write(st.session_state['clusters_compositions'])
            
            chart1 = clusters_podium(st.session_state['cluster_datas'], clusters_compositions)
            if chart1:
                st.altair_chart(chart1)
            
            chart2 = clusters_grid(st.session_state['cluster_datas'], clusters_compositions)
            if chart2:
                st.altair_chart(chart2)

with ads_tab:
    st.header("Ads information")
    with st.expander("Show raw data"):
        st.subheader("Advertisers using your activity or information")
        st.write(advertisers_using_your_activity_or_information)
        st.subheader("Other categories used to reach you")
        st.write(other_categories_used_to_reach_you)
    
    st.write("Your subscription for no-ads is", substriction_status)
    st.write("Below are the **personal information you submitted to advertisers**:")
    if information_youve_submitted_to_advertisers:
        st.table(information_youve_submitted_to_advertisers)
    else:
        st.info("No information submitted to advertisers.")

    if not advertisers_using_your_activity_or_information.empty:
        chart = ads_bar(advertisers_using_your_activity_or_information)
        if chart:
            st.altair_chart(chart)
    else:
        st.info("📊 No advertiser data available.")

    if advertisers_enriched is not None and not advertisers_enriched.empty:
        st.write("The following visualizations were compiled thanks to data enrichment")
    else:
        if not advertisers_using_your_activity_or_information.empty:
            if st.button("Enrich the advertisers data"):
                seconds = len(advertisers_using_your_activity_or_information)
                with st.spinner(f"Enriching your advertisers data... Browsing the advertisers name on Wikidata... This may take a moment (~{seconds//60}min {seconds%60}sec)"):
                        try:
                            advertisers_enriched = enrich_companies(advertisers_using_your_activity_or_information, name_col="advertiser_name")
                            advertisers_enriched.to_csv("./data/advertisers_enriched.csv")
                            st.success("✅ Data enriched successfully!")
                        except Exception as e:
                            st.error(f"Error scraping the data: {e}")
    st.info("""
            **Enrichment sources used:**
            - **Wikipedia** → to find the most probable page and retrieve the corresponding **Wikidata QID**  
            - **Wikidata** → to extract structured data such as **country**, **industry**, **headquarters**, **inception**, and **website**  
            - **Clearbit Autocomplete API** → to infer official **domains/websites** when missing  
            - **OpenCorporates API** → to identify the company’s **country of registration** when not available elsewhere  

            Data is collected only from **public APIs** with rate limits respected (no scraping).
            """)
    if advertisers_enriched is not None and not advertisers_enriched.empty:
        st.subheader("Advertisers visualization after enrichment")
        with st.expander("Show raw data"):
            st.subheader("Advertisers after the enrichment")
            st.write(advertisers_enriched)
        
        chart1 = ads_enriched_missing_values(advertisers_enriched)
        if chart1:
            st.altair_chart(chart1)
        
        chart2 = ads_countries_map(advertisers_enriched)
        if chart2:
            st.altair_chart(chart2)
        
        st.write("**Creation year of each advertiser**")
        signup_time = signup_details.get('Time', 0)
        chart3 = ads_inception_year(advertisers_enriched, signup_time)
        if chart3:
            st.altair_chart(chart3)

with personal_info_tab:
    st.header("Personal Information")
    st.write("What does Instagram know about you?")
    with st.expander("Show raw data"):
        st.write("Your devices")
        st.write(df_devices)
        st.write("Your camera information")
        st.write(df_camera_info)
        st.write("Your locations of interest")
        st.write(df_locations_of_interest)
        st.write("Your last known locations")
        st.write(df_last_known_location)
    with st.expander("Show preprocessed data"):
        st.write("Your devices")
        st.info("The preprocessing of the devices pandas DataFrame was made possible with the user-agents python library.")
        st.write(df_devices_prep)
        st.write("Locations of interest")
        st.info("This dataframe was encoded in utf-8. Latitude and longitude were also added thanks to **geopy** library")
        st.write(df_locations_of_interest_prep)
   
    col1, col2 = st.columns([1,1], gap="large")
    with col1:
        st.write("Your profile is based in:", profile_based_in if profile_based_in else "Unknown")
        st.subheader("Your locations of interest")
        if not df_locations_of_interest_prep.empty and 'lat' in df_locations_of_interest_prep.columns and 'lon' in df_locations_of_interest_prep.columns:
            st.map(df_locations_of_interest_prep)
        else:
            st.info("📊 No location of interest data available.")
            
        st.subheader("Your last known location")
        if not df_last_known_location.empty and 'lat' in df_last_known_location.columns and 'longitude' in df_last_known_location.columns:
            st.map(df_last_known_location)
        else:
            st.info("📊 No last known location data available.")

    with col2:
        st.subheader("Personal Contact Information")
        phone = signup_details.get('Phone Number', 'N/A')
        st.write("Your phone number:", phone if phone and phone != 'N/A' else "Not available")
        st.write("Your email:", possible_emails if possible_emails else "Not available")
        
        st.subheader("Your device information")
        if not df_devices_prep.empty:
            chart = devices_over_times(df_devices_prep)
            if chart:
                st.altair_chart(chart)
        else:
            st.info("📊 No device data available.")

with security_tab:
    st.header("Security and log information")
    st.caption("The security dashboard shows the connection logs to your account and their information as well as your signup details.")
    with st.expander("Show raw data"):
        st.write("Logs Data")
        st.write(df_logs)
        st.write("Signup Details")
        st.write(signup_details)
        st.write("Password change Activity")
        st.write(password_change_activity)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Signup Details")
        signup_time = signup_details.get('Time', 0)
        st.caption(f"Time: {date_str(signup_time) if signup_time and signup_time != 0 else 'N/A'}")
        st.write(f"Username: {signup_details.get('Username', 'N/A')}")
        email = signup_details.get("Email")
        if email and email != 'N/A': 
            st.write(f"Email: {email}")
        phone = signup_details.get("Phone Number")
        if phone and phone != 'N/A': 
            st.write(f"Phone Number: {phone}")
        device = signup_details.get("Device")
        if device and device != 'N/A': 
            st.write(f"Device Name: {device}")
            
        st.subheader("Recovery contacts")
        st.write("Contact:", possible_emails if possible_emails else "None")
        
        st.subheader("Password change activity")
        if password_change_activity:
            chart = password_activity_bar(password_change_activity)
            if chart:
                st.altair_chart(chart)
        else:
            st.info("📊 No password change activity recorded.")
            
    with col2:
        st.subheader("Connection Logs")

        by = st.radio("Grouped by:", ["months","days","years"], horizontal=True, index=0)

        st.subheader("Login / Logout")
        if not df_logs.empty:
            chart = login_logout_hist(df_logs, by=by, date_range=date_range)
            if chart:
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("📊 No login/logout data available.")

        st.subheader("Cookies Distribution")
        if not df_logs.empty:
            chart = cookies_pie(df_logs)
            if chart:
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("📊 No cookie data available.")

st.markdown("---")
st.caption("This dashboard respects your privacy - all data processing happens locally on your machine.")
st.caption("This dashboard was vibecoded with [chatGPT-5](https://chatgpt.com/), [Claude Sonnet 4.5](https://claude.ai/) and [DeepSeek](https://chat.deepseek.com/)")

st.caption("Source: [Account Center - Instagram](https://accountscenter.instagram.com/info_and_permissions/dyi/?theme=dark)")