import numpy as np
import pandas as pd
import altair as alt

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

