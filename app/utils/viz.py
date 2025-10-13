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

# ---------- follows ---------

def plot_venn_or_upset(sets_by_type: dict, selected_types=None, title="Venn / UpSet"):
    """Venn si 2-3 groupes (matplotlib-venn), sinon fallback UpSet-like (barres intersections)."""

    if selected_types is None:
        selected_types = ["followings", "followers", "close_friends"]

    groups = [g for g in selected_types if g in sets_by_type and len(sets_by_type[g]) > 0]

    if len(groups) == 0:
        fig = plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "Pas de données pour les groupes sélectionnés", ha="center", va="center")
        plt.axis("off")
        return fig

    # Venn 2-3
    if len(groups) <= 3:
        fig = plt.figure(figsize=(6, 6))
        if len(groups) == 2:
            venn2([sets_by_type[groups[0]], sets_by_type[groups[1]]], set_labels=groups)
        else:  # 3
            venn3([sets_by_type[g] for g in groups], set_labels=groups)
        plt.title(title)
        return fig

    # UpSet-like (bar chart des intersections)
    union_users = set().union(*[sets_by_type[g] for g in groups])
    rows = []
    for u in union_users:
        rows.append({g: int(u in sets_by_type[g]) for g in groups})
    mat = pd.DataFrame(rows)

    comb = mat.groupby(groups).size().reset_index(name="count")
    comb = comb[comb["count"] > 0]

    def label_row(row):
        on = [g for g in groups if row[g] == 1]
        return "&".join(on) if on else "None"
    comb["label"] = comb.apply(label_row, axis=1)
    comb = comb.sort_values("count", ascending=False).head(15)

    fig = plt.figure(figsize=(9, 5))
    plt.bar(comb["label"], comb["count"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Utilisateurs dans l'intersection")
    plt.title(f"Intersections (Top {min(15, len(comb))})")
    plt.tight_layout()
    return fig


def plot_follow_time_series(timeseries: pd.DataFrame, cumulative: bool = True, title="Followers / Followings over time"):
    """Courbe cumulée (par défaut) ou journalière des ajouts."""
    y = "cum_count" if cumulative else "new_count"
    fig = plt.figure(figsize=(9, 4))
    if timeseries.empty:
        plt.text(0.5, 0.5, "Pas de données de série temporelle", ha="center", va="center")
        plt.axis("off")
        return fig

    for t, sub in timeseries.groupby("follows_type"):
        s = sub.sort_values("date")
        plt.plot(s["date"], s[y], label=t)

    plt.xlabel("Date")
    plt.ylabel("Cumul" if cumulative else "Nouveaux / jour")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    return fig

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
def website_bar(df_link_history):
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
            # 👇 couleur bleue + échelle ajustée
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
