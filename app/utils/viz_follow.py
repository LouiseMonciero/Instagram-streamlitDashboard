# utils/viz_follow.py
import pandas as pd
import numpy as np
from typing import Dict, Set, List
from urllib.parse import urlparse

import altair as alt
import matplotlib.pyplot as plt
from matplotlib_venn import venn2, venn3
from upsetplot import UpSet, from_memberships



# ---------------------------
# set builders
# ---------------------------
def build_sets_at_date(df_long: pd.DataFrame, target_date: pd.Timestamp, groups: List[str]) -> Dict[str, Set[str]]:
    """
    For a given date (take that day's snapshot; if multiple per day, take max timestamp),
    build sets of usernames per group.
    """
    df = df_long.copy()
    # coarsen to date (no time) for snapshot selection
    df["date_only"] = df["snapshot_date"].dt.date
    target = pd.to_datetime(target_date).date()

    # if the exact date isn't present, pick the nearest previous date
    available = sorted(df["date_only"].dropna().unique())
    if target not in available:
        # pick the latest date <= target, else earliest
        prev = [d for d in available if d <= target]
        chosen = prev[-1] if prev else available[0]
    else:
        chosen = target

    snap = df[df["date_only"].eq(chosen)]

    sets = {}
    for g in groups:
        users = set(snap.loc[snap["group"].eq(g), "username"].dropna().unique().tolist())
        sets[g] = users
    return sets, pd.to_datetime(chosen)


# ---------------------------
# Venn / UpSet plotting
# ---------------------------
def venn_or_upset(df_long: pd.DataFrame, groups: List[str], target_date=None):
    """
    If len(groups) <= 3 -> Venn (matplotlib figure)
    Else -> UpSet plot (matplotlib figure)
    """
    if target_date is None:
        target_date = df_long["snapshot_date"].max()

    sets, chosen_date = build_sets_at_date(df_long, target_date, groups)

    fig = None
    if len(groups) == 2:
        a, b = groups
        fig, ax = plt.subplots(figsize=(5,4), dpi=150)
        venn2([sets[a], sets[b]], set_labels=(a, b), ax=ax)
        ax.set_title(f"Venn ({a} vs {b}) — {chosen_date.date()}")
        plt.tight_layout()
        return fig

    if len(groups) == 3:
        a, b, c = groups
        fig, ax = plt.subplots(figsize=(6,5), dpi=150)
        venn3([sets[a], sets[b], sets[c]], set_labels=(a, b, c), ax=ax)
        ax.set_title(f"Venn ({a}, {b}, {c}) — {chosen_date.date()}")
        plt.tight_layout()
        return fig

    # 4+ groups -> UpSet
    memberships = []
    # build list like ["followers","following"] per user for upset
    all_users = set().union(*sets.values()) if sets else set()
    for u in all_users:
        m = [g for g in groups if u in sets[g]]
        memberships.append(m)

    series = from_memberships(memberships)
    fig = plt.figure(figsize=(8,5), dpi=150)
    UpSet(series, subset_size='count', show_percentages=True).plot(fig=fig)
    plt.suptitle(f"UpSet — {chosen_date.date()}")
    plt.tight_layout()
    return fig


# ---------------------------
# Line chart (followers vs following over time)
# ---------------------------
def followers_following_timeseries(df_long: pd.DataFrame) -> alt.Chart:
    """
    Returns an Altair line chart with two series:
    - count of 'followers' by date
    - count of 'following' by date
    """
    df = df_long.copy()
    df["date_only"] = df["snapshot_date"].dt.date

    pivot = (
        df.groupby(["date_only", "group"], as_index=False)
          .agg(count=("username", "nunique"))
    )

    # keep only the two lines requested; if absent, they'll simply be missing
    pivot = pivot[pivot["group"].isin(["followers","following"])]

    chart = (
        alt.Chart(pivot)
        .mark_line(point=True)
        .encode(
            x=alt.X("date_only:T", title="Date"),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color("group:N", title="Group", scale=alt.Scale(domain=["followers","following"], range=["#1f77b4","#ff7f0e"])),
            tooltip=[
                alt.Tooltip("date_only:T", title="Date"),
                alt.Tooltip("group:N", title="Group"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(height=320)
    )
    return chart
