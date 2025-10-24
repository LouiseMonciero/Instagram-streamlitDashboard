import numpy as np
import pandas as pd
import altair as alt

# ---------- helpers ----------

def filter_by_date_range(df: pd.DataFrame, date_column: str, date_range: tuple) -> pd.DataFrame:
    """
    Filter a dataframe by date range without modifying the original.
    
    Args:
        df: DataFrame to filter
        date_column: Name of the date column
        date_range: Tuple of (start_date, end_date)
    
    Returns:
        Filtered DataFrame copy
    """
    if not date_range or len(date_range) != 2:
        return df
    
    df_filtered = df.copy()
    
    # Ensure the date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_filtered[date_column]):
        df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
    
    # Convert filter dates to datetime and handle timezone
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    
    # If the column has timezone info, localize the filter dates to match
    if df_filtered[date_column].dt.tz is not None:
        # Get the timezone from the column
        tz = df_filtered[date_column].dt.tz
        # Localize start and end dates to the same timezone
        if start_date.tz is None:
            start_date = start_date.tz_localize('UTC').tz_convert(tz)
        else:
            start_date = start_date.tz_convert(tz)
            
        if end_date.tz is None:
            end_date = end_date.tz_localize('UTC').tz_convert(tz)
        else:
            end_date = end_date.tz_convert(tz)
    
    return df_filtered[(df_filtered[date_column] >= start_date) & (df_filtered[date_column] <= end_date)]

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

# ---------- security charts ----------

def login_logout_hist(df: pd.DataFrame, by: str = "months", date_range: tuple = None) -> alt.Chart:
    """
    Histogramme logins (vert) / logouts (rouge, valeurs négatives) sur le même graphe.
    by ∈ {"months","days","years"}.
    """
    dfp = _preprocess(df)
    
    # Apply date filter if provided
    if date_range:
        dfp = filter_by_date_range(dfp, 'ts', date_range)
    
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
