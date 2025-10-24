import streamlit as st
from math import ceil
from utils.io import load_data, DATA_PATH
from utils.prep import preprocess_data, date_str
# Import lazy - w2v_model ne chargera gensim que lors de l'appel à generate_clusters
from utils.w2v_model import generate_clusters
from utils.data_enrichement import enrich_companies
from utils.viz.activities import total_activities_over_time, plot_duo_participation, group_vs_duo_conv_pie, plot_duo_reel_vs_nonreel, request_corr0, scroll_hist, saved_media_by_time
from utils.viz.media import media_cumulative_line, media_type_bar, media_frequency_histogram
from utils.viz.ads import ads_bar, ads_countries_map, ads_enriched_missing_values, ads_inception_year
from utils.viz.preferences import clusters_podium, clusters_grid
from utils.viz.security import login_logout_hist, cookies_pie, password_activity_bar
from utils.viz.connections import upset, plot_venn, plot_follow_time_series_altair, follows_pie
from utils.viz.personal_info import devices_over_times
from utils.viz.link_history import website_bar

st.set_page_config(page_title="Data Storytelling Dashboard", layout="wide")
@st.cache_data(show_spinner=False)

def get_data():
    return load_data()

st.title("Personal Instagram Dashboard !")

with st.spinner("Loading your data...", show_time=True):
    (df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs, df_all_ads, substriction_status, information_youve_submitted_to_advertisers, advertisers_using_your_activity_or_information, other_categories_used_to_reach_you, advertisers_enriched,
            df_all_comments, df_liked_comments, df_liked_posts, df_all_conversations,
            df_time_spent_on_ig, df_your_information_download_requests, 
            df_saved_collections, df_saved_locations, df_saved_posts, df_saved_music,
            df_story_likes) = get_data()

with st.spinner("Preprocessing your data...", show_time=True):
    clean_follows = preprocess_data(df_follows=df_follows)
    clean_contacts = preprocess_data(df_contacts=df_contacts)
    df_media_prep = preprocess_data(df_media=df_media)
    df_link_history_prep = preprocess_data(df_link_history=df_link_history)
    df_locations_of_interest_prep = preprocess_data(df_locations_of_interest=df_locations_of_interest)
    df_last_known_location = preprocess_data(df_last_known_location=df_last_known_location)
    df_devices_prep = preprocess_data(df_devices=df_devices)

home, connections_tab, media_tab, preferences_tab, activity_tab, link_history_tab, ads_tab, personal_info_tab, security_tab = st.tabs(["Welcome !", "Connections", "Media", "Preferences","Your activity", "Link History", 'Ads Info', "Personnal Information", "Security Insights"])


with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", [])

with home :
    st.write("IDK what to put here....")

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
        
        # --- contrôles ---
        all_groups = sorted(clean_follows["sets_by_type"].keys())
        default_groups = [g for g in ["followings", "followers", "close_friends"] if g in all_groups]
        selected_groups = st.multiselect(
            "Groups for either Venn of UpSet diagram", options=all_groups, default=default_groups
        )

        sets_by_type = clean_follows["sets_by_type"]  # single source of truth
        selected = selected_groups if selected_groups else [
            g for g in ["followings", "followers", "close_friends"] if g in sets_by_type
        ]

        non_empty = [g for g in selected if g in sets_by_type and len(sets_by_type[g]) > 0]

        if len(non_empty) < 2:
            st.info("Select at least two non-empty groups.")
        elif 2 <= len(non_empty) <= 3:
            # Venn (2–3 groups)
            fig = plot_venn(sets_by_type, selected_types=non_empty)
            st.pyplot(fig, use_container_width=True)
        else:
            # UpSet-like (≥4 groups) — Altair chart
            chart = upset(sets_by_type, selected_types=non_empty)
            st.altair_chart(chart, use_container_width=True)

        st.caption(
            "Don't be fooled by the number: some follow counts can be duplicated. "
            "E.g., if you blocked the same person twice, it may be counted twice."
        )
    with col2:
        st.subheader("Followers / Followings accross time")
        mode = st.radio("Mode", ["Cumulative", "Dayly"], horizontal=True)
        cum = (mode == "Cumulative")
        #fig2 = plot_follow_time_series(clean["timeseries"], cumulative=cum,
                                    #title="Cumul des ajouts" if cum else "Ajouts quotidiens")
        chart2 = plot_follow_time_series_altair(clean_follows["timeseries"], cumulative=cum)
        if chart2:
            st.altair_chart(chart2, use_container_width=True)

    col12, col22 = st.columns([1,1], gap="large")
    with col12: # -- contacts info
        st.subheader("Contacts informations")
        st.write("Total of contacts registered by instagram :", df_contacts.shape[0])
        st.write("Among those, you have:")
        st.write("    - ",clean_contacts["phone"].notna().sum()," phone number registered")
        st.write("    - ",clean_contacts["email"].notna().sum()," email registered")
        st.caption("Instagram can use this contact list to recommend profiles for you.")
        st.caption("Even you, people can see your profile in their recommendations thanks to your contact information linked to your profile.")
        contact_methods = []
        if signup_details.get('Email'):
            contact_methods.append(signup_details['Email'])
        if signup_details.get('Phone Number'):
            contact_methods.append(signup_details['Phone Number'])
        if contact_methods:
            st.caption(f"In your case, people can reach you with: {', '.join(contact_methods)}")
        else:
            st.caption("In your case, no contact information is available for others to reach you.")

    with col22:
        st.subheader("Follows type pie")
        st.altair_chart(follows_pie(df_follows))

with media_tab:
    st.header("Media Dashboard")
    with st.expander("Show raw data"):
        st.write("Media")
        st.write(df_media)
    with st.expander("Show preprocessed data"):
        st.write("Media")
        st.write("This preprocessing step standardizes the media dataset and reconstructs missing information from the file paths." \
            "When only the relative_path is available, the script automatically extracts the media type (e.g. posts, stories, reels), the year, the month, and a normalized timestamp from the folder structure. " \
            "It also adds helper columns such as filename, extension, and a year_month date to make temporal analysis easier.")
        st.write(df_media_prep)
    
    st.header("Insights")
    col1, col2 = st.columns([1,1], gap="large")
    with col1 : 
        st.subheader("Posting over the years")
        st.altair_chart(media_cumulative_line(df_media_prep), use_container_width=True)
        st.write("You currently have", df_media_prep[df_media_prep["media_type"]=="posts"].shape[0], "pictures in your posts,", df_media_prep[df_media_prep["media_type"]=="archived_posts"].shape[0],"archived posts pictures,", df_media_prep[df_media_prep["media_type"]=="profile"].shape[0], "profile picture,", df_media_prep[df_media_prep["media_type"]=="stories"].shape[0], "stories and", df_media_prep[df_media_prep["media_type"]=="recently_deleted"].shape[0], "recently deleted pictures")
    with col2 :
        st.subheader("Media types distribution")
        st.altair_chart(media_type_bar(df_media_prep), use_container_width=True)

    st.subheader("Stories frequencies ")
    by_stories = st.radio("Grouped by :", ["years","months","weeks"], index=1, horizontal=True, key="stories_hist")
    st.altair_chart(media_frequency_histogram(df_media_prep, by_stories), use_container_width=True)

    st.subheader("Posts & Archived Posts frequencies ")
    by_posts = st.radio("Grouped by :", ["years","months","weeks"], index=1, horizontal=True, key="posts_hist")
    st.altair_chart(media_frequency_histogram(df_media_prep, by_posts, media_type=["archived_posts", "posts"], color='blues'), use_container_width=True)

# ------------gallery ---------------
    st.header("Gallery")
    if st.button("Load your gallery !", type="primary"):
        controls = st.columns(4)
        with controls[0]:
            media_types = st.multiselect("Media Types", ["Posts", "Stories", "Archived Posts", "Deleted"], default=["Posts", "Stories"])
        with controls[1]:
            # Extract unique year-months from the 'timestamp' column, sort them
            available_dates = sorted(df_media_prep['timestamp'].unique())
            # Convert to string for display (if not already)
            available_dates = [str(d) for d in available_dates]
            # Use select_slider for date range selection
            selected_range = st.select_slider(
                "Date Range:",
                options=available_dates,
                value=(available_dates[0], available_dates[-1]),
                key='date_range'
            )
            # Filter df_media_prep based on selected_range
            df_media_prep = df_media_prep[
                (df_media_prep['timestamp'] >= selected_range[0]) &
                (df_media_prep['timestamp'] <= selected_range[1])
            ]
        with controls[2]:
            batch_size = st.select_slider("Batch size:", range(10, 110, 10), key='batch_slider')
        num_batches = ceil(len(df_media) / batch_size)

        with controls[3]:
            page = st.selectbox("Page", range(1, num_batches + 1), key='page')

        # Update function when checkbox or label changes
        def update(image, col):
            df_media_prep.at[image, col] = st.session_state[f'{col}_{image}']
            if st.session_state[f'incorrect_{image}'] == False:
                st.session_state[f'label_{image}'] = ''
                df_media_prep.at[image, 'label'] = ''

        # Select the batch of files based on the page
        batch = df_media_prep[(page - 1) * batch_size : page * batch_size]

        # Create a grid of columns for the display
        row_size = 4  # Adjust based on how many columns you want to display per row
        grid = st.columns(row_size)
        col = 0


        # Loop over the batch and display images/videos
        for _, media in batch.iterrows():  # Use iterrows() to iterate over the rows
            media_path = media['relative_path']
            media_ext = media['ext']
            media_file = f'{DATA_PATH}/media/{media_path}'  # Adjust to your actual directory path

            with grid[col]:
                if media_ext in ['jpg', 'jpeg', 'png']:  # Image handling
                    st.image(media_file, caption='Media')
                elif media_ext == 'mp4':  # Video handling
                    st.video(media_file)

            col = (col + 1) % row_size  # Move to the next column

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
    with st.expander("Show preprocessed datas"):
        st.write("It empty here .... ") # encode differently pleeeeeease !!!
    
    st.subheader("Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours spent on instgram", f"{df_time_spent_on_ig['duration_sec'].sum() / 60:.2f} hours")
    c2.metric("Likes", f"{len(df_liked_posts)}")
    c3.metric("Stories liked", f"{len(df_story_likes)}")
    c4.metric("Likes on comment", f"{len(df_liked_comments)}")

    c21, c22, c23, c24 = st.columns(4)
    c21.metric("Messages sent", f"IDK")
    c22.metric("Messages received", f"IDK")
    c23.metric("Comments", f"{len(df_all_comments)}")
    c24.metric("Times you downloaded your datas", f"{len(df_your_information_download_requests)}")

    st.subheader("Your activities over time")
    st.subheader("Activities across time")
    mode = st.radio("Mode", ["Cumulative", "Monthly"], horizontal=True)
    cum = (mode == "Cumulative")
    monthly = (mode == "Monthly")

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
        use_log_y=True
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Messages & conversations")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Participations of your conversations")
        top_n_participation = st.slider("Top N conversations", 1, 30, 10, key="participations_slider")
        st.altair_chart(plot_duo_participation(df_all_conversations, top_n_participation))

        st.write("Group vs duo's conversations")
        st.altair_chart(group_vs_duo_conv_pie(df_all_conversations))

    with col2:
        st.write("'Reel based' conversations")
        top_n_reel = st.slider("Top N conversations", 1, 30, 10, key="reel_slider")
        st.altair_chart(plot_duo_reel_vs_nonreel(df_all_conversations, top_n_reel))
    
    st.subheader("Dm requests")
    col21, col22 = st.columns(2)
    with col21:
        fig0 = request_corr0(df_all_conversations)
        st.pyplot(fig0, use_container_width=True)
    with col22:
        st.info("On instagram, the requests sent in dms are often scam or sexual content.\n" \
        "See how the number of participant and the total messages sent can be correlated to the type of messages you received.")
    

    st.subheader("Time spent on instagram")
    #st.altair_chart(scroll_hist(df_time_spent_on_ig))

    st.subheader("Saved informations")
    by_saved = st.radio("Grouped by :", ["years","months","weeks"], index=1, horizontal=True, key="saved_hist")
    st.altair_chart(saved_media_by_time(df_saved_collections, df_saved_posts, df_saved_music, by_saved))
    saved_c1, saved_c2, saved_c3 = st.columns(3)
    with saved_c1:
        st.write()
    with saved_c2:
        st.write()

    with saved_c3:
        st.write()

with preferences_tab:
    st.header("Your recommended topics")
    with st.expander("Show raw datas"):
        st.write("recommended topics")
        st.write(recommended_topics)
    
    st.write("Launching the predictions will allow you to see your most frequent categories among your preferences." \
        "This model is a Clustering ML model based on Word2Vector librairie using gensim.")
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
        st.altair_chart(clusters_podium(st.session_state['cluster_datas'], clusters_compositions))
        st.altair_chart(clusters_grid(st.session_state['cluster_datas'], clusters_compositions))

with link_history_tab:
    st.header("Link history")
    with st.expander("Show raw datas"):
        st.write("Follows")
        st.write(df_follows)

    st.altair_chart(website_bar(df_link_history))

with ads_tab:
    st.header("Ads information")
    with st.expander("Show raw datas"):
        st.subheader("Advertisers using your activity or information")
        st.write(advertisers_using_your_activity_or_information)
        st.subheader("Other categories used to reach you")
        st.write(other_categories_used_to_reach_you)
    
    st.write("Your substriction for no-ads is", substriction_status)
    st.write("Below are the **personal informations you submitted to advertisers** :")
    st.table(information_youve_submitted_to_advertisers)

    st.altair_chart(ads_bar(advertisers_using_your_activity_or_information))

    if advertisers_enriched is not None :
        st.write("The following vizualisation were compiled thanks to data enrichement")
    else :
        if st.button("Enrich the advestisers data"):
            seconds = len(advertisers_using_your_activity_or_information)
            with st.spinner("Enriching your advertisers data... Browsing the advertisers name on wikidata... This may take a moment (~"+str(seconds//60)+"min"+str(seconds%60)+"sec)"):
                    try:
                        advertisers_enriched = enrich_companies(advertisers_using_your_activity_or_information, name_col="advertiser_name")
                        advertisers_enriched.to_csv("./data/advertisers_enriched.csv")
                        st.success("✅ Clusters generated successfully!")
                    except Exception as e:
                        st.error(f"Error scrapping the datas: {e}")
    st.info("""
            **Enrichment sources used:**
            - **Wikipedia** → to find the most probable page and retrieve the corresponding **Wikidata QID**  
            - **Wikidata** → to extract structured data such as **country**, **industry**, **headquarters**, **inception**, and **website**  
            - **Clearbit Autocomplete API** → to infer official **domains/websites** when missing  
            - **OpenCorporates API** → to identify the company’s **country of registration** when not available elsewhere  

            Data is collected only from **public APIs** with rate limits respected (no scraping).
            """)
    if advertisers_enriched is not None :
        st.subheader("Advertissers vizualisation after enrichement")
        with st.expander("Show raw datas"):
            st.subheader("Advertisers after the enrichement")
            st.write(advertisers_enriched)
        st.altair_chart(ads_enriched_missing_values(advertisers_enriched))
        st.altair_chart(ads_countries_map(advertisers_enriched))
        st.altair_chart(ads_inception_year(advertisers_enriched, signup_details['Time']))

with personal_info_tab:
    st.header("Personal Information")
    st.write("What does instagram know about you ?")
    with st.expander("Show raw data"):
        st.write("Your devices")
        st.write(df_devices)
        st.write("Your cameras informations")
        st.write(df_camera_info)
        st.write("Your locations of interest")
        st.write(df_locations_of_interest)
        st.write("Your last known locations")
        st.write(df_last_known_location)
    with st.expander("Show preprossed data"):
        st.write("Your devices")
        st.info("The preprocessing of the devices pandas dataFrame was made possible with the user-agents python librairies.")
        st.write(df_devices_prep)
        st.write("Location of interest")
        st.info("This dataframe was encoded in utf-8. Latitude and longitude were also added thanks to **geopy** librairy")
        st.write(df_locations_of_interest_prep)
   
    col1, col2 = st.columns([1,1], gap="large")
    with col1:
        st.write("Your profile is based in :", profile_based_in)
        st.subheader("Your locations of interest")
        st.map(df_locations_of_interest_prep)
        st.subheader("Your last known locations... ")
        st.map(df_last_known_location)

    with col2:
        st.subheader("Personal Contact Information")
        st.write("Your phone number :", signup_details['Phone Number'])
        st.write("Your email : ", possible_emails)
        st.subheader("Your devices informations")
        st.altair_chart(devices_over_times(df_devices_prep))

with security_tab:
    st.header("Security and logs info")
    st.caption("The security dashboard shows the connections logs to your account and their informations as well as you signup details.")
    with st.expander("Show raw datas"):
        st.write("Logs Data")
        st.write(df_logs)
        st.write("Signup Details")
        st.write(signup_details)
        st.write("Password change Activity")
        st.write(password_change_activity)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Signup Details")
        st.caption(f"Time: {date_str(signup_details.get('Time', 'N/A'))}")
        st.write(f"Username: {signup_details.get('Username', 'N/A')}")
        if signup_details.get("Email"): st.write(f"Email: {signup_details['Email']}")
        if signup_details.get("Phone Number"): st.write(f"Phone Number: {signup_details['Phone Number']}")
        if signup_details.get("Device"): st.write(f"Device Name: {signup_details['Device']}")
        st.subheader("Recovery contacts")
        st.write("Contact : ", possible_emails)
        st.subheader("Password change activity")
        st.altair_chart(password_activity_bar(password_change_activity))
    with col2:
        st.subheader("Connections Logs")

        by = st.radio("Grouped by :", ["months","days","years"], horizontal=True, index=0)

        st.subheader("Login / Logout")
        st.altair_chart(login_logout_hist(df_logs, by=by), use_container_width=True)

        st.subheader("Cookies Distribution")
        st.altair_chart(cookies_pie(df_logs), use_container_width=True)

st.caption("Source: [Account Center - Instagram](https://accountscenter.instagram.com/info_and_permissions/dyi/?theme=dark)")