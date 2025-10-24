import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn3

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
