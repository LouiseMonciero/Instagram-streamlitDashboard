import pandas as pd
import altair as alt

# ------- devices --------
def devices_over_times(df_devices_prep:pd.DataFrame) -> alt.Chart:

    rows = []
    for _, r in df_devices_prep.iterrows():
        if r['is_pc']:
            rows.append({'device_type': 'PC', 'last_login': r['last_login_timestamp'],
                        'os_family': r['os_family'], 'browser_family': r['browser_family'],
                        'browser_version': r['browser_version']})
        if r['is_tablet']:
            rows.append({'device_type': 'Tablet', 'last_login': r['last_login_timestamp'],
                        'os_family': r['os_family'], 'browser_family': r['browser_family'],
                        'browser_version': r['browser_version']})
        if r['is_mobile']:
            rows.append({'device_type': 'Mobile', 'last_login': r['last_login_timestamp'],
                        'os_family': r['os_family'], 'browser_family': r['browser_family'],
                        'browser_version': r['browser_version']})

    df_long = pd.DataFrame(rows)

    # Sort by device and last_login
    df_long = df_long.sort_values(['device_type', 'last_login']).reset_index(drop=True)

    # Compute start time per device as the last login of the previous row of the same device
    df_long['start'] = df_long.groupby('device_type')['last_login'].shift(1)
    df_long['start'] = df_long['start'].fillna(df_long['last_login'] - pd.Timedelta(days=1))  # default 1 day before

    # Altair timeline plot
    chart = alt.Chart(df_long).mark_bar().encode(
        y=alt.Y('device_type:N', title='Device'),
        x=alt.X('start:T', title='Start'),
        x2=alt.X2('last_login:T', title='End'),
        color=alt.Color('os_family:N', title='OS Family'),
        tooltip=[
            alt.Tooltip('os_family:N', title='OS Device'),
            alt.Tooltip('browser_family:N', title='Browser'),
            alt.Tooltip('browser_version:N', title='Version'),
            alt.Tooltip('last_login:T', title='End'),
        ]
    ).properties(
        width=800,
        height=200
    )

    return chart

# ---------- personal locations ---------
def plot_locations_map(df):
    chart = alt.Chart(df).mark_circle(size=100, color="#3182bd", opacity=0.7).encode(
        longitude="longitude:Q",
        latitude="latitude:Q",
        tooltip=["value", "latitude:Q", "longitude:Q"]
    ).properties(
        width=700,
        height=500,
        title="Locations Map"
    )
    return chart
