import streamlit as st
from utils.io import load_data, pwd
from utils.viz import login_logout_hist, cookies_pie, website_bar, password_activity_bar, upset, plot_venn, plot_follow_time_series_altair, follows_pie, media_cumulative_line, media_type_bar, stories_histogram
from utils.prep import preprocess_data, date_str
#from utils.prep import make_tables
#from utils.viz import line_chart, bar_chart, map_chart

st.set_page_config(page_title="Data Storytelling Dashboard", layout="wide")
@st.cache_data(show_spinner=False)

def get_data():
    #tables = make_tables(df_raw)
    return load_data()
#st.image('assets/logo-instagram-black-bg.webp', width=80)
#st.logo('assets/277-removebg-preview.png')

st.title("Personal Instagram Dashboard !")
st.caption("Source: <dataset title> — <portal> — <license>")
tab1, connections_tab, media_tab, tab4, tab5, link_history_tab, tab7, tab8, security_tab = st.tabs(["Welcome !", "Connections", "Media", "Preferences","Your activity", "Link History", 'Ads Info', "Personnal Information", "Security Insights"])

st.write('here is the path',pwd())

with st.sidebar:
    st.header("Filters")
    date_range = st.date_input("Date range", [])

df_contacts, df_media, df_follows, df_devices, df_camera_info, df_locations_of_interest, possible_emails, profile_based_in, df_link_history, recommended_topics, signup_details, password_change_activity, df_last_known_location, df_logs = get_data()

with connections_tab:
    st.header("Connections")
    with st.expander("Show raw datas"):
        st.write("Followers and Following")
        st.write(df_follows)
        st.write("Contacts")
        st.write(df_contacts)
    
    clean_follows = preprocess_data(df_follows=df_follows)
    clean_contacts = preprocess_data(df_contacts=df_contacts)
    
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
        mode = st.radio("Mode", ["Cumulatif", "Journalier"], horizontal=True)
        cum = (mode == "Cumulatif")
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
    df_media_prep = preprocess_data(df_media=df_media)
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

    with col2 :
        st.subheader("Media types distribution")
        st.altair_chart(media_type_bar(df_media_prep), use_container_width=True)

    st.subheader("Stories frequencies ")
    by = st.radio("Grouped by :", ["years","months","weeks"], horizontal=True, index=0)
    st.altair_chart(stories_histogram(df_media_prep, by), use_container_width=True)

    st.subheader("Gallery")



with link_history_tab:
    df_link_history_prep = preprocess_data(df_link_history=df_link_history)
    st.header("Link history")
    with st.expander("Show raw datas"):
        st.write("Follows")
        st.write(df_follows)

    st.altair_chart(website_bar(df_link_history))

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
        #st.write(signup_details)
        st.subheader("Password change activity")
        st.altair_chart(password_activity_bar(password_change_activity))
    with col2:
        st.subheader("Connections Logs")

        by = st.radio("Grouped by :", ["months","days","years"], horizontal=True, index=0)

        st.subheader("Login / Logout")
        st.altair_chart(login_logout_hist(df_logs, by=by), use_container_width=True)

        st.subheader("Cookies Distribution")
        st.altair_chart(cookies_pie(df_logs), use_container_width=True)


""" 
# KPI row
c1, c2, c3 = st.columns(3)
c1.metric("KPI 1", "…", "∆ vs. baseline")
c2.metric("KPI 2", "…")
c3.metric("KPI 3", "…")

st.subheader("Trends over time")
line_chart(tables["timeseries"]) # custom function adds consistent styling

st.subheader("Compare regions")
bar_chart(tables["by_region"])

st.subheader("Map view")
map_chart(tables["geo"])

st.markdown("### Data Quality & Limitations")
st.info("Describe missing data, measurement limits, and biases.")
st.markdown("### Key Insights & Next Steps")
st.success("Summarize what matters and what actions follow.") """