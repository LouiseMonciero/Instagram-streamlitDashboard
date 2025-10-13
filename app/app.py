import streamlit as st
from utils.io import load_data, pwd
from utils.viz import login_logout_hist, cookies_pie, website_bar, password_activity_bar, plot_venn_or_upset, plot_follow_time_series
from utils.prep import preprocess_data, date_str
#from utils.prep import make_tables
#from utils.viz import line_chart, bar_chart, map_chart

st.set_page_config(page_title="Data Storytelling Dashboard", layout="wide")
@st.cache_data(show_spinner=False)

def get_data():
    #tables = make_tables(df_raw)
    return load_data()

st.logo('assets/logo-instagram.png')
st.title("Personal Instagram Dashboard !")
st.caption("Source: <dataset title> — <portal> — <license>")
tab1, connections_tab, tab3, tab4, tab5, link_history_tab, tab7, tab8, security_tab = st.tabs(["Welcome !", "Connections", "Media", "Preferences","Your activity", "Link History", 'Ads Info', "Personnal Information", "Security Insights"])

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
    
    clean = preprocess_data(df_follows=df_follows)

    # --- contrôles ---
    all_groups = sorted(clean["sets_by_type"].keys())
    default_groups = [g for g in ["followings", "followers", "close_friends"] if g in all_groups]
    selected_groups = st.multiselect(
        "Groupes pour le Venn / UpSet", options=all_groups, default=default_groups
    )

    col1, col2 = st.columns([1,1], gap="large")

    with col1:
        st.subheader("Venn (≤3) ou UpSet-like (>3)")
        fig = plot_venn_or_upset(clean["sets_by_type"], selected_types=selected_groups, title="Intersections de groupes")
        st.pyplot(fig)

    with col2:
        st.subheader("Followers / Followings dans le temps")
        mode = st.radio("Mode", ["Cumulatif", "Journalier"], horizontal=True)
        cum = (mode == "Cumulatif")
        fig2 = plot_follow_time_series(clean["timeseries"], cumulative=cum,
                                    title="Cumul des ajouts" if cum else "Ajouts quotidiens")
        st.pyplot(fig2)

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