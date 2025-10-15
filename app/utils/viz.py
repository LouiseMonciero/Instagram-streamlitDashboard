
# chart functions to enforce consistent style
# utils/viz.py
import pandas as pd
import numpy as np
import altair as alt
import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn3

# ---------- helpers ----------
def _auto_to_datetime(ts_series: pd.Series) -> pd.Series:
    """Convertit epoch en datetime Europe/Paris. Auto-détection s (<=1e11) vs ms (>1e11)."""
    ts = pd.to_numeric(ts_series, errors="coerce")
    unit = "ms" if ts.dropna().median() > 1e11 else "s"
    dt = pd.to_datetime(ts, unit=unit, utc=True).dt.tz_convert("Europe/Paris")
    return dt

def _preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # normalisation minimale -> colonnes attendues
    expected = {"log_type","cookie_name","ip_address","language","timestamp","user_agent"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}")

    df["ts"] = _auto_to_datetime(df["timestamp"])
    df["year"] = df["ts"].dt.year

    weekday_map = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    df["weekday_num"] = df["ts"].dt.weekday
    df["weekday"] = df["weekday_num"].map(weekday_map)

    # label months lisible et triable
    df["ym"] = df["ts"].dt.to_period("M").astype(str)  # "2025-10"
    try:
        month_fr = df["ts"].dt.month_name(locale="fr_FR").str.capitalize()
    except Exception:
        months_fr = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        month_fr = df["ts"].dt.month.map(lambda m: months_fr[m-1])
    df["months"] = df["ym"] + " · " + month_fr

    # borne l’événement
    df["event"] = df["log_type"].astype(str).str.lower().str.strip()
    df.loc[~df["event"].isin(["login","logout"]), "event"] = "login"

    # alias pour pie
    df["cookie"] = df["cookie_name"]
    df["ip"] = df["ip_address"]
    df["lang"] = df["language"]
    df["ua"] = df["user_agent"]

    return df

def _group_counts(df: pd.DataFrame, by: str):
    if by == "months":
        key = "months"
        # ordre basé sur "YYYY-MM · Nom"
        order = sorted(df[key].unique(), key=lambda s: s.split(" · ")[0])
    elif by == "days":
        key = "weekday"
        order = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    elif by == "years":
        key = "year"
        order = sorted(df[key].unique().tolist())
    else:
        raise ValueError("by must be 'months', 'days' or 'years'")

    grp = (
        df.groupby([key, "event"], as_index=False)
          .size()
          .rename(columns={"size":"count"})
    )
    grp["count_signed"] = np.where(grp["event"].eq("logout"), -grp["count"], grp["count"])
    return grp, key, order

# ---------- media -----------

def media_cumulative_line(df: pd.DataFrame) -> alt.Chart:
    """
    Line chart showing cumulative count of posts (or archived_posts) and stories over time.
    """
    # Keep only posts and stories
    media = df[df["media_type"].isin(["posts", "archived_posts", "stories"])].copy()

    if media.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No media data"]})).mark_text().encode(text="msg")

    media["timestamp"] = media["timestamp"].astype(str)
    media["date"] = pd.to_datetime(media["timestamp"].str[:6], format="%Y%m", errors="coerce")

    # Aggregate counts
    media["count"] = 1
    media = (
        media.groupby(["date", "media_type"], as_index=False)["count"]
        .sum()
        .sort_values("date")
    )

    # Cumulative sum by type
    media["cum_count"] = media.groupby("media_type")["count"].cumsum()

    chart = (
        alt.Chart(media)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("cum_count:Q", title="Cumulative Count"),
            color=alt.Color("media_type:N", title="Media Type"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("media_type:N", title="Type"),
                alt.Tooltip("cum_count:Q", title="Cumulative posts"),
            ],
        )
        .properties(
            title="Cumulative evolution of posts and stories over time",
            width=700,
            height=400,
        )
        .interactive()
    )
    return chart

def media_frequency_histogram(df: pd.DataFrame, by: str = "months", media_type=["stories"], color="oranges") -> alt.Chart:
    """
    Histogram of posts/stories frequency grouped by year, month, or week.
    The DataFrame must have a 'timestamp' column formatted as YYYYMM or YYYYMMDD.
    """

    selected_medias = df[df["media_type"].isin(media_type)]

    if selected_medias.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No story data"]})).mark_text().encode(text="msg")

    # Parse timestamp safely
    selected_medias["timestamp"] = selected_medias["timestamp"].astype(str)
    selected_medias["date"] = pd.to_datetime(selected_medias["timestamp"].str[:6], format="%Y%m", errors="coerce")

    # Choose grouping level
    if by == "years":
        selected_medias["period"] = selected_medias["date"].dt.year.astype(str)
    elif by == "months":
        selected_medias["period"] = selected_medias["date"].dt.to_period("M").astype(str)
    elif by == "weeks":
        selected_medias["period"] = selected_medias["date"].dt.to_period("W").astype(str)
    else:
        raise ValueError("Parameter 'by' must be 'year', 'month', or 'week'.")

    agg = selected_medias.groupby("period", as_index=False).size().rename(columns={"size": "count"})

    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("period:N", title=f"Period ({by})", sort="x"),
            y=alt.Y("count:Q", title="Number of Stories"),
            tooltip=["period:N", "count:Q"],
            color=alt.Color("count:Q", scale=alt.Scale(scheme=color)),
        )
        .properties(
            title=f"Stories frequency by {by.capitalize()}",
            width=600,
            height=350,
        )
    )
    return chart

def media_type_bar(df: pd.DataFrame) -> alt.Chart:
    agg = (
        df.groupby("media_type", as_index=False)
          .size()
          .rename(columns={"size": "count"})
          .sort_values("count", ascending=False)
    )

    chart = (
        alt.Chart(agg)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("media_type:N", title="Media Type", sort="-y"),
            y=alt.Y("count:Q", title="Number of Media"),
            color=alt.Color("count:Q", scale=alt.Scale(scheme="blues")),
            tooltip=[
                alt.Tooltip("media_type:N", title="Type"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(
            title="Distribution of Media Types",
            width=400,
            height=350,
        )
    )
    return chart


# ---------- follows ---------
def plot_venn(sets_by_type: dict, selected_types=None):
    """Venn if 2-3 groups (matplotlib-venn)"""

    if selected_types is None:
        selected_types = ["followings", "followers", "close_friends"]

    groups = [g for g in selected_types if g in sets_by_type and len(sets_by_type[g]) > 0]

    if len(groups) == 0:
        fig = plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "No data for the selected groups", ha="center", va="center")
        plt.axis("off")
        return fig

    # Venn 2-3
    if len(groups) <= 3:
        fig = plt.figure(figsize=(6, 6))
        if len(groups) == 2:
            venn2([sets_by_type[groups[0]], sets_by_type[groups[1]]], set_labels=groups)
        else:  # 3
            venn3([sets_by_type[g] for g in groups], set_labels=groups)
        plt.title("Follows Type - Venn Diagram")
        return fig
    
    else :
        fig = plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "+ 3 gps", ha="center", va="center")
        return fig

def upset(sets_by_type: dict, selected_types=None):
    # UpSet-like (bar chart des intersections)
    groups = [g for g in selected_types if g in sets_by_type and len(sets_by_type[g]) > 0]
    union_users = set().union(*[sets_by_type[g] for g in groups])
    rows = [{g: int(u in sets_by_type[g]) for g in groups} for u in union_users]
    mat = pd.DataFrame(rows)
    comb = mat.groupby(groups).size().reset_index(name="count")
    comb = comb[comb["count"] > 0]

    def label_row(row):
        on = [g for g in groups if row[g] == 1]
        return "&".join(on) if on else "None"
    comb["label"] = comb.apply(label_row, axis=1)
    comb = comb.sort_values("count", ascending=False).head(15)

    chart = (
        alt.Chart(comb)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("label:N", title="Group combinations", sort="-y"),
            y=alt.Y("count:Q", title="Users in intersection"),
            tooltip=["label", "count"],
            color=alt.Color("count:Q", scale=alt.Scale(scheme="blues")),
        )
        .properties(title=f"Group intersections (Top {min(15, len(comb))})", width="container", height=350)
    )
    return chart

def plot_follow_time_series_altair(
    timeseries: pd.DataFrame,
    cumulative: bool = True,
    title: str = "Followers / Followings over time",
):
    """
    Interactive Altair line chart showing the evolution of followers / followings.
    - cumulative=True: cumulative count
    - cumulative=False: daily new additions
    """
    if timeseries.empty:
        st.warning("⚠️ No data available for time series.")
        return None

    y_col = "cum_count" if cumulative else "new_count"
    y_label = "Cumulative count" if cumulative else "New per day"

    # ensure correct types
    timeseries = timeseries.copy()
    timeseries["date"] = pd.to_datetime(timeseries["date"])

    chart = (
        alt.Chart(timeseries)
        .mark_line(point=True, interpolate="monotone")
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            color=alt.Color("follows_type:N", title="Type"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("follows_type:N", title="Type"),
                alt.Tooltip(f"{y_col}:Q", title=y_label),
            ],
        )
        .properties(
            title=title,
            width="container",
            height=350,
        )
        .interactive()
    )

    # Add smooth transitions with layered points (optional)
    points = (
        alt.Chart(timeseries)
        .mark_circle(size=60)
        .encode(
            x="date:T",
            y=f"{y_col}:Q",
            color="follows_type:N",
            tooltip=["date:T", "follows_type:N", f"{y_col}:Q"],
        )
    )

    return chart + points

def follows_pie(df: pd.DataFrame) -> alt.Chart:
    # --- aggregate by follows_type ---
    agg = (
        df.groupby("follows_type", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    agg["percentage"] = 100 * agg["count"] / agg["count"].sum()

    # --- Altair pie chart ---
    chart = (
        alt.Chart(agg)
        .mark_arc(outerRadius=130, innerRadius=40)
        .encode(
            theta=alt.Theta("count:Q", stack=True, title=""),
            color=alt.Color("follows_type:N", title="Follows Type", scale=alt.Scale(scheme="tableau10")),
            tooltip=[
                alt.Tooltip("follows_type:N", title="Type"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("percentage:Q", title="%", format=".1f"),
            ],
        )
        .properties(
            title="Distribution of Follows Types",
            width=400,
            height=400,
        )
    )

    return chart

# ---------- security charts ----------
def login_logout_hist(df: pd.DataFrame, by: str = "months") -> alt.Chart:
    """
    Histogramme logins (vert) / logouts (rouge, valeurs négatives) sur le même graphe.
    by ∈ {"months","days","years"}.
    """
    dfp = _preprocess(df)
    grp, key, order = _group_counts(dfp, by)

    color_scale = alt.Scale(domain=["login","logout"], range=["#22c55e","#ef4444"])

    chart = (
        alt.Chart(grp)
        .mark_bar()
        .encode(
            x=alt.X(f"{key}:O", sort=order, title=key.capitalize()),
            y=alt.Y("count_signed:Q", title="Nombre d'événements (logout inversé)"),
            color=alt.Color("event:N", title="Type", scale=color_scale),
            tooltip=[
                alt.Tooltip(f"{key}:O", title=key.capitalize()),
                alt.Tooltip("event:N", title="Type"),
                alt.Tooltip("count:Q", title="Nombre"),
            ],
        )
        .properties(height=360)
        .configure_axis(grid=True)
    )
    return chart

def cookies_pie(df: pd.DataFrame) -> alt.Chart:
    """
    Distribution (%) per cookie.
    Tooltips: cookie, %, occurrences, most frequent langage, distincts @IP, example user-agent.
    """
    dfp = _preprocess(df)

    # most frequent langage
    lang_mode = (
        dfp.groupby(["cookie","lang"], as_index=False)
           .size()
           .sort_values(["cookie","size"], ascending=[True, False])
           .groupby("cookie")
           .first()
           .reset_index()[["cookie","lang"]]
           .rename(columns={"lang":"lang_mode"})
    )

    cookie_stats = (
        dfp.groupby("cookie", as_index=False)
           .agg(
               count=("cookie","size"),
               ip_unique=("ip", pd.Series.nunique),
               ua_example=("ua", "first")
           )
           .merge(lang_mode, on="cookie", how="left")
    )
    cookie_stats["pct"] = 100 * cookie_stats["count"] / cookie_stats["count"].sum()

    pie = (
        alt.Chart(cookie_stats)
        .mark_arc(outerRadius=140, innerRadius=30)
        .encode(
            theta=alt.Theta("count:Q", stack=True),
            color=alt.Color("cookie:N", legend=None),
            tooltip=[
                alt.Tooltip("cookie:N", title="Cookie"),
                alt.Tooltip("pct:Q", title="Part (%)", format=".1f"),
                alt.Tooltip("count:Q", title="Occurrences"),
                alt.Tooltip("lang_mode:N", title="Most frequent language"),
                alt.Tooltip("ip_unique:Q", title="Distincts IP"),
                alt.Tooltip("ua_example:N", title="Example User-Agent"),
            ],
        )
        .properties(height=360, width=420)
    )
    return pie

def password_activity_bar(l: list[dict]) -> alt.Chart:
    df = pd.DataFrame(l)
    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["year"] = df["date"].dt.year

    agg = (
        df.groupby("year", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )

    chart = (
        alt.Chart(agg)
        .mark_bar(size=20, color="#4B9CD3")
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y("count:Q", title="Password change count"),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip("count:Q", title="Changes"),
            ],
        )
        .properties(
            title="Password change activity",
            height=150,
            width=300
        )
    )

    return chart


# --------- link history charts -------
def website_bar(df_link_history : pd.DataFrame) -> alt.Chart:
    agg = (
    df_link_history.groupby("Website_name", as_index=False)
    .agg(
        visit_count=("Website_name", "size"),
        total_time_min=("total_time_min", "sum")
    )
    .sort_values("visit_count", ascending=False)
)

    
    chart = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("Website_name:N", sort="-y", title="Website"),
            y=alt.Y("visit_count:Q", title="Number of visits"),
            color=alt.Color(
                "total_time_min:Q",
                title="Total time (min)",
                scale=alt.Scale(
                    scheme="blues",          # palette bleue
                    domain=[0, agg["total_time_min"].max()]  # bornes de l’échelle
                )
            ),
            tooltip=[
                alt.Tooltip("Website_name:N", title="Website"),
                alt.Tooltip("visit_count:Q", title="Visit count"),
                alt.Tooltip("total_time_min:Q", title="Total time (min)", format=".2f"),
            ],
        )
        .properties(
            title="Website visits and total time spent (in minutes)",
            width=800,
            height=400
        )
    )
    return chart

# --------- preferences -------------
def clusters_podium(clusters_data: list[dict], clusters_compositions: dict) -> alt.Chart:
    
    # Sort clusters by weights descending and get top 3
    top3 = sorted(clusters_data, key=lambda el: el['weights'], reverse=True)[:3]
    # Assign podium order (1st, 2nd, 3rd)
    for idx, cluster in enumerate(top3):
        cluster['order'] = idx + 1
        # Use index as key for composition
        comp_key = str(clusters_data.index(cluster))
        cluster['composition'] = ", ".join(clusters_compositions.get(comp_key, []))

    podium_df = pd.DataFrame(top3)
    chart = alt.Chart(podium_df).mark_bar(size=60).encode(
        x=alt.X("order:O", title="Podium Place", axis=alt.Axis(labelExpr='datum.value == 1 ? "1" : datum.value == 2 ? "2" : "3"')),
        y=alt.Y("weights:Q", title="Importance of the cluster"),
        color=alt.Color("order:O", scale=alt.Scale(domain=[1,2,3], range=["#FFD700", "#C0C0C0", "#CD7F32"]), legend=None),
        tooltip=[
            alt.Tooltip("cluster_name:N", title="Cluster Name"),
            alt.Tooltip("weights:Q", title="Number of categories in cluster"),
            alt.Tooltip("composition:N", title="Cluster Categories"),
        ],
    ).properties(
        title="Podium: Top 3 Clusters",
        width=400,
        height=350
    )
    return chart

def clusters_grid(clusters_data: list[dict], clusters_compositions: dict) -> alt.Chart:
    # Check if clusters_compositions is provided and not empty
    if not clusters_compositions:
        raise ValueError("clusters_compositions is missing or empty.")

    # Limite à 12 clusters pour une grille 3x4
    max_clusters = 12
    n_cols = 4
    n_rows = 3
    grid_data = []
    for idx, cluster in enumerate(clusters_data[:max_clusters]):
        cluster_name = cluster.get('cluster_name', f"Cluster {idx}")
        categories = clusters_compositions.get(str(idx), [])
        if not categories:
            categories = ["(aucune catégorie)"]
        col = idx % n_cols
        row = idx // n_cols
        for cat in categories:
            grid_data.append({
                "cluster_name": cluster_name,
                "category": cat,
                "col": col,
                "row": row,
                "weight": cluster.get('weights', 0)
            })
    df = pd.DataFrame(grid_data)
    # Nom du cluster en plus gros, catégories en plus petit
    chart = alt.Chart(df).mark_text(fontSize=14).encode(
        x=alt.X('col:O', title=None, axis=None),
        y=alt.Y('row:O', title=None, axis=None),
        text='category:N',
        color=alt.Color('cluster_name:N', legend=None),
        tooltip=[
            alt.Tooltip('cluster_name:N', title='Cluster'),
            alt.Tooltip('category:N', title='Category'),
        ]
    )
    # Ajoute le nom du cluster en plus gros au-dessus de chaque case
    cluster_labels = pd.DataFrame({
        "col": [i % n_cols for i in range(min(len(clusters_data), max_clusters))],
        "row": [i // n_cols for i in range(min(len(clusters_data), max_clusters))],
        "cluster_name": [c.get('cluster_name', f"Cluster {i}") for i, c in enumerate(clusters_data[:max_clusters])],
        "weight": [c.get('weights', 0) for c in clusters_data[:max_clusters]]
    })
    label_chart = alt.Chart(cluster_labels).mark_text(fontSize=22, fontWeight="bold", dy=-60).encode(
        x=alt.X('col:O', title=None, axis=None),
        y=alt.Y('row:O', title=None, axis=None),
        text='cluster_name:N',
        color=alt.Color('cluster_name:N', legend=None),
        tooltip=[
            alt.Tooltip('cluster_name:N', title='Cluster'),
            alt.Tooltip('weight:Q', title='Weight'),
        ]
    )
    return (label_chart + chart).properties(
        width=900,
        height=700,
        title="Clusters grid (3x4)"
    )

def clu_podium():
    clusters_data = [{"cluster_name":"Body & Games & Sports","weights":15},{"cluster_name":"Cosplay","weights":1},{"cluster_name":"Foods & Cakes & Recipes","weights":4},{"cluster_name":"Animals & Cats & Fish","weights":13},{"cluster_name":"Painting & Drawing","weights":3},{"cluster_name":"Care & Beauty & Makeup","weights":4},{"cluster_name":"Travel & Europe & Baked","weights":7},{"cluster_name":"TV & Movies","weights":7},{"cluster_name":"Fashion & Products","weights":5},{"cluster_name":"Drinks & Non-Alcoholic & Beverages","weights":3}]
    clusters_compositions = {"0":["Crafts","Ground Transportation","Gym Workouts","Body Modification","AR/VR Games","Water Sports","Visual Arts","Beauty Product Types","Technology","Video Games by Game Mechanics","Types of Sports","Beauty Products","Cars & Trucks","Body Art","Interior Design"],"1":["Cosplay"],"2":["Foods","Cakes","Recipes","Desserts"],"3":["Fish","Birds","Wild Cats","Reptiles","Lions","Mammals","Dogs","Aquatic Animals","Animals","Farm Animals","Rabbits","Cats","Pets"],"4":["Drawing & Sketching","Painting","Watercolor Painting"],"5":["Beauty","Makeup","Faces & Face Care","Hair Care"],"6":["Baked Goods","Vacation & Leisure Activities","Asia Travel","Western Europe Travel","Travel Destinations","Europe Travel","Travel by Region"],"7":["Video Games","Anime TV & Movies","Animation TV & Movies","Dance","TV & Movies by Genre","Digital Art","Toys"],"8":["Fashion Products","Fashion","Fashion Styles & Trends","Fashion Media & Entertainment","Clothing & Accessories"],"9":["Non-Alcoholic Beverages","Drinks","Coffee Drinks"]}
    top3 = sorted(clusters_data, key=lambda el: el['weights'], reverse=True)[:3]
    # Assign podium order (1st, 2nd, 3rd)
    for idx, cluster in enumerate(top3):
        cluster['order'] = idx + 1
        # Use index as key for composition
        comp_key = str(clusters_data.index(cluster))
        cluster['composition'] = ", ".join(clusters_compositions.get(comp_key, []))

    podium_df = pd.DataFrame(top3)
    chart = alt.Chart(podium_df).mark_bar(size=60).encode(
        x=alt.X("order:O", title="Podium Place", axis=alt.Axis(labelExpr='datum.value == 1 ? "1" : datum.value == 2 ? "2" : "3"')),
        y=alt.Y("weights:Q", title="Importance of the cluster"),
        color=alt.Color("order:O", scale=alt.Scale(domain=[1,2,3], range=["#FFD700", "#C0C0C0", "#CD7F32"]), legend=None),
        tooltip=[
            alt.Tooltip("cluster_name:N", title="Cluster Name"),
            alt.Tooltip("weights:Q", title="Number of categories in cluster"),
            alt.Tooltip("composition:N", title="Cluster Categories"),
        ],
    ).properties(
        title="Podium: Top 3 Clusters",
        width=400,
        height=350
    )
    return chart