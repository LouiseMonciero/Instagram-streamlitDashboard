import altair
import pandas as pd
import altair as alt
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# ------- Helper functions --------

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
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    
    # Ensure the date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_filtered[date_column]):
        df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
    
    return df_filtered[(df_filtered[date_column] >= start_date) & (df_filtered[date_column] <= end_date)]

# ------- activities --------

def total_activities_over_time(
    df_all_comments=None,
    df_liked_comments=None,
    df_liked_posts=None,
    df_story_likes=None,
    df_saved_posts=None,
    df_all_conversations=None,
    cumulative: bool = True,
    monthly: bool = True,  # True = agrégation par mois, False = par jour
    title: str = "Total Instagram Activities Over Time",
    use_log_y: bool = True,
    date_range: tuple = None
):
    """
    Altair line chart showing activity over time (cumulative or per period),
    with optional log-scale on Y.

    - cumulative=True  -> courbe cumulée
    - cumulative=False -> valeurs par période (mois ou jour)
    - monthly=True     -> agrégation mensuelle ('M'), sinon journalière ('D')
    - use_log_y=True   -> échelle Y logarithmique
    """

    # --- Collect available dataframes dynamically ---
    dfs = {
        "Comments": df_all_comments,
        "Liked Comments": df_liked_comments,
        "Liked Posts": df_liked_posts,
        "Story Likes": df_story_likes,
        "Saved Posts": df_saved_posts,
        "Conversations": df_all_conversations,
    }

    frames = []
    for name, df in dfs.items():
        if df is None or df.empty:
            continue
        temp = df.copy()

        # choose column to extract time
        if "date" in temp.columns:
            temp["date"] = pd.to_datetime(temp["date"], errors="coerce", utc=True)
        elif "timestamp" in temp.columns:
            temp["date"] = pd.to_datetime(temp["timestamp"], unit="s", errors="coerce", utc=True)
        elif "timestamps" in temp.columns:  # conversation case (list of timestamps)
            temp["date"] = pd.to_datetime(
                temp["timestamps"].apply(lambda x: x[0] if isinstance(x, list) else None),
                unit="ms", errors="coerce", utc=True
            )
        else:
            continue

        temp["activity_type"] = name
        frames.append(temp[["date", "activity_type"]])

    if not frames:
        st.warning("⚠️ No activity data available.")
        return None

    all_data = (
        pd.concat(frames, ignore_index=True)
        .dropna(subset=["date"])
        .assign(date=lambda d: d["date"].dt.tz_convert("Europe/Paris"))
    )
    
    # Apply date range filter if provided
    if date_range:
        all_data = filter_by_date_range(all_data, "date", date_range)

    # --- Choose granularity: month or day ---
    freq = "M" if monthly else "D"
    period_col = "period_month" if monthly else "period_day"
    all_data[period_col] = all_data["date"].dt.to_period(freq).dt.to_timestamp()

    # --- Aggregate counts per period & type ---
    agg = (
        all_data.groupby(["activity_type", period_col])
        .size()
        .reset_index(name="count")
        .sort_values(period_col)
    )

    # --- Cumulative if requested ---
    agg["cum_count"] = agg.groupby("activity_type")["count"].cumsum()

    y_col = "cum_count" if cumulative else "count"
    y_label = ("Cumulative count" if cumulative else ("New per month" if monthly else "New per day"))

    # --- Altair chart ---
    y_scale = alt.Scale(type="log", base=10, nice=True, clamp=True, domainMin=1) if use_log_y else alt.Undefined
    chart = (
        alt.Chart(agg)
        .mark_line(point=True, interpolate="monotone")
        .encode(
            x=alt.X(f"{period_col}:T", title="Date"),
            y=alt.Y(f"{y_col}:Q", title=y_label, scale=y_scale),
            color=alt.Color("activity_type:N", title="Activity type"),
            tooltip=[
                alt.Tooltip(f"{period_col}:T", title="Date"),
                alt.Tooltip("activity_type:N", title="Type"),
                alt.Tooltip(f"{y_col}:Q", title=y_label),
                alt.Tooltip("count:Q", title="Raw count (this period)"),
            ],
        )
        .properties(title=title, width="container", height=350)
        .interactive()
    )

    points = (
        alt.Chart(agg)
        .mark_circle(size=50)
        .encode(
            x=f"{period_col}:T",
            y=alt.Y(f"{y_col}:Q", scale=y_scale),
            color="activity_type:N",
            tooltip=[
                alt.Tooltip(f"{period_col}:T", title="Date"),
                alt.Tooltip("activity_type:N", title="Type"),
                alt.Tooltip(f"{y_col}:Q", title=y_label),
                alt.Tooltip("count:Q", title="Raw count (this period)"),
            ],
        )
    )

    return chart + points


def preprocess_duo_conversations(
    df_all_conversations: pd.DataFrame,
    top_n: int = 10,
    owner_aliases=("Instagram User", "louise"),   # names that identify *you*
    exclude_requests: bool = True
) -> pd.DataFrame:
    """
    Prepare a long dataframe for plotting top-N duo conversations:
    columns -> ['conversation','role','count','total','pct']
    - keeps rows with exactly 2 participants
    - keeps rows where one participant is you (owner_aliases)
    - sorts by total messages and keeps top_n (clamped to [1,50])
    """
    if df_all_conversations is None or df_all_conversations.empty:
        return pd.DataFrame(columns=["conversation","role","count","total","pct"])

    df = df_all_conversations.copy()

    if exclude_requests and "message_type" in df.columns:
        df = df[df["message_type"] != "message_requests"]

    # only 2 participants
    df = df[df["participants"].apply(lambda x: isinstance(x, list) and len(x) == 2)]
    if df.empty:
        return pd.DataFrame(columns=["conversation","role","count","total","pct"])

    rows = []
    for _, r in df.iterrows():
        participants = r["participants"]
        counts = r.get("participants_participation", {}) or {}

        # identify 'you' (owner) if present
        you = next((p for p in participants if p in owner_aliases), None)
        if you is None:
            # skip pairs that don't involve the account owner
            continue

        other = participants[0] if participants[1] == you else participants[1]

        c_you   = int(counts.get(you, 0) if pd.notna(counts.get(you, 0)) else 0)
        c_other = int(counts.get(other, 0) if pd.notna(counts.get(other, 0)) else 0)
        total = c_you + c_other
        if total <= 0:
            # nothing to plot
            continue

        label = other  # bar label = the other person
        rows.append({"conversation": label, "role": "You",   "count": c_you,   "total": total})
        rows.append({"conversation": label, "role": "Other", "count": c_other, "total": total})

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return long_df

    # keep top-N by total (sum per conversation)
    top_n = int(np.clip(top_n, 1, 50))
    top_convs = (
        long_df.groupby("conversation")["total"].max()
        .sort_values(ascending=False)
        .head(top_n).index
    )
    long_df = long_df[long_df["conversation"].isin(top_convs)].copy()

    # percentage for tooltip
    long_df["pct"] = (long_df["count"] / long_df["total"] * 100).round(1)

    return long_df


def plot_duo_participation(
    df_all_conversations: pd.DataFrame,
    top_n: int = 10
) -> alt.Chart:
    """
    Horizontal stack-normalized bar chart (You vs Other) for the top-N duo conversations.
    """
    plot_df = preprocess_duo_conversations(df_all_conversations, top_n=top_n)
    if plot_df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["No duo conversations to display"]})).mark_text(
            size=16, align="center"
        ).encode(text="msg:N")

    conv_order = (
        plot_df.groupby("conversation")["total"].max()
        .sort_values(ascending=False)
        .index.tolist()
    )

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            y=alt.Y("conversation:N", sort=conv_order, title=None),
            x=alt.X("count:Q", stack="normalize",
                    title="Share of messages (%)",
                    axis=alt.Axis(format="%")),
            color=alt.Color("role:N",
                            title="Participant",
                            scale=alt.Scale(domain=["You","Other"],
                                            range=["#BA1CFE","#53595F"])),
            tooltip=[
                alt.Tooltip("conversation:N", title="Conversation with"),
                alt.Tooltip("role:N", title="Participant"),
                alt.Tooltip("count:Q", title="Messages"),
                alt.Tooltip("total:Q", title="Total (duo)"),
                alt.Tooltip("pct:Q", title="Share (%)")
            ],
        )
        .properties(
            title=f"Top-{len(conv_order)} duo conversations — message share",
            width="container",
            height=max(220, 28 * len(conv_order))
        )
    )

    return chart

def group_vs_duo_conv_pie(df_all_conversations: pd.DataFrame) -> alt.Chart:
    """
    Create a pie chart comparing:
      - Duo conversations (2 participants)
      - Group conversations (>2 participants)
    Excludes rows where message_type == 'message_requests'.
    """
    if df_all_conversations is None or df_all_conversations.empty:
        return alt.Chart(pd.DataFrame({'label': [], 'count': []})).mark_text().encode(text="label:N")

    # Filter out message requests
    df = df_all_conversations[df_all_conversations["message_type"] != "message_requests"].copy()

    if df.empty:
        return alt.Chart(pd.DataFrame({'label': [], 'count': []})).mark_text().encode(text="label:N")

    # Compute number of participants per conversation
    df["n_participants"] = df["participants"].apply(lambda x: len(x) if isinstance(x, list) else None)

    # Label each conversation
    df["conversation_type"] = df["n_participants"].apply(
        lambda n: "Duo (2 participants)" if n == 2 else "Group (>2 participants)"
    )

    # Aggregate counts
    summary = df["conversation_type"].value_counts().reset_index()
    summary.columns = ["conversation_type", "count"]
    total = summary["count"].sum()
    summary["percentage"] = (summary["count"] / total * 100).round(1)

    # Pie chart
    chart = (
        alt.Chart(summary)
        .mark_arc(outerRadius=120)
        .encode(
            theta=alt.Theta("count:Q", title="Number of conversations"),
            color=alt.Color("conversation_type:N", title="Type", scale=alt.Scale(scheme="set2")),
            tooltip=[
                alt.Tooltip("conversation_type:N", title="Conversation type"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("percentage:Q", title="Percentage (%)"),
            ],
        )
        .properties(
            title="Conversations: Duo vs Group",
            width=400,
            height=350,
        )
    )

    # Add text labels (percentages)
    text = chart.mark_text(radius=140, size=13, color="black").encode(
        text=alt.Text("percentage:Q", format=".1f")
    )

    return chart + text


def preprocess_duo_reel_vs_nonreel(
    df_all_conversations: pd.DataFrame,
    top_n: int = 10,
    owner_aliases=("Instagram User", "louise"),
    exclude_requests: bool = True
) -> pd.DataFrame:
    """
    Renvoie un DF long pour plotting:
    columns -> ['conversation','kind','count','total','pct','total_reels']
      - duo uniquement (2 participants)
      - la conversation doit inclure l'utilisateur (owner_aliases)
      - top-N selon count_total_reel_sent (desc)
      - kind ∈ {'Reels','Autres messages'}
    """
    if df_all_conversations is None or df_all_conversations.empty:
        return pd.DataFrame(columns=["conversation","kind","count","total","pct","total_reels"])

    df = df_all_conversations.copy()
    if exclude_requests and "message_type" in df.columns:
        df = df[df["message_type"] != "message_requests"]

    # duo uniquement
    df = df[df["participants"].apply(lambda x: isinstance(x, list) and len(x) == 2)]
    if df.empty:
        return pd.DataFrame(columns=["conversation","kind","count","total","pct","total_reels"])

    rows = []
    for _, r in df.iterrows():
        p = r["participants"]
        # vérifier que la conv inclut "moi"
        me = next((x for x in p if x in owner_aliases), None)
        if me is None:
            continue
        other = p[0] if p[1] == me else p[1]

        total_msgs  = int(r.get("count_total_interaction", 0) or 0)
        total_reels = int(r.get("count_total_reel_sent", 0) or 0)
        if total_reels <= 0 or total_msgs <= 0:
            continue

        others = total_msgs - total_reels
        if others < 0:  # sécurité
            others = 0

        conv_label = f"{other}-Moi"

        rows.append({"conversation": conv_label, "kind": "Reels",
                     "count": total_reels, "total": total_msgs, "total_reels": total_reels})
        rows.append({"conversation": conv_label, "kind": "Autres messages",
                     "count": others, "total": total_msgs, "total_reels": total_reels})

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return long_df

    # top-N par nb de reels
    top_n = int(np.clip(top_n, 1, 50))
    keep = (
        long_df.groupby("conversation")["total_reels"].max()
        .sort_values(ascending=False).head(top_n).index
    )
    long_df = long_df[long_df["conversation"].isin(keep)].copy()
    long_df["pct"] = (long_df["count"] / long_df["total"] * 100).round(1)
    return long_df

def plot_duo_reel_vs_nonreel(
    df_all_conversations: pd.DataFrame,
    top_n: int = 10
) -> alt.Chart:
    """
    Barres horizontales empilées/normalisées: part des reels vs autres messages
    pour les top-N conversations duo (triées par nb de reels envoyés).
    """
    plot_df = preprocess_duo_reel_vs_nonreel(df_all_conversations, top_n=top_n)
    if plot_df.empty:
        return alt.Chart(pd.DataFrame({"msg": ["Aucune conversation duo avec des reels"]})).mark_text(
            size=16, align="center"
        ).encode(text="msg:N")

    # ordre par nb de reels (plus gros en bas, style “pyramide”)
    conv_order = (
        plot_df.groupby("conversation")["total_reels"].max()
        .sort_values(ascending=False).index.tolist()
    )

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            y=alt.Y("conversation:N", sort=conv_order, title="Conversation"),
            x=alt.X("count:Q", stack="normalize",
                    title="Répartition des messages (%)",
                    axis=alt.Axis(format="%")),
            color=alt.Color("kind:N", title="Type de message",
                            scale=alt.Scale(domain=["Reels","Autres messages"],
                                            range=["#582EFD","#53595F"])),
            tooltip=[
                alt.Tooltip("conversation:N", title="Conversation"),
                alt.Tooltip("kind:N", title="Type"),
                alt.Tooltip("count:Q", title="Volume"),
                alt.Tooltip("total:Q", title="Total messages"),
                alt.Tooltip("pct:Q", title="Part (%)"),
                alt.Tooltip("total_reels:Q", title="Reels (total)"),
            ],
        )
        .properties(
            title=f"Top-{len(conv_order)} conversations (duo) — part des reels vs autres messages",
            width="container",
            height=max(220, 28 * len(conv_order))
        )
    )
    return chart


def request_corr0(df_all_conversations: pd.DataFrame) -> plt.Figure:
    """
    Plot Pearson correlation matrix (matplotlib) including vectorized message_type.
    Returns a matplotlib Figure (use st.pyplot(fig) in Streamlit).
    """
    if df_all_conversations is None or df_all_conversations.empty:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    # Add numeric features
    df_all_conversations["n_participants"] = df_all_conversations["participants"].apply(
        lambda x: len(x) if isinstance(x, list) else np.nan
    )

    # Base numeric columns
    base_num_cols = ["count_total_interaction", "count_total_link_shared",
                     "count_total_reel_sent", "n_participants"]

    # Ensure numeric for base columns
    for c in base_num_cols:
        df_all_conversations[c] = pd.to_numeric(df_all_conversations[c], errors="coerce")

    # Vectorize message_type using one-hot encoding
    message_type_dummies = pd.get_dummies(df_all_conversations['message_type'], prefix='message_type')
    
    # Combine all features for correlation matrix
    correlation_df = pd.concat([
        df_all_conversations[base_num_cols],
        message_type_dummies
    ], axis=1)

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6), constrained_layout=True)

    vmin, vmax = -1.0, 1.0
    cmap = "coolwarm"

    # Compute correlation matrix
    corr = correlation_df.corr(method="pearson")

    # Plot heatmap
    im = ax.imshow(corr, vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_title("Correlation Matrix (including message types)")
    
    # Set ticks and labels
    all_columns = list(corr.columns)
    ax.set_xticks(range(len(all_columns)))
    ax.set_yticks(range(len(all_columns)))
    ax.set_xticklabels(all_columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(all_columns, fontsize=9)

    # Annotate cells with correlation values
    for i in range(len(all_columns)):
        for j in range(len(all_columns)):
            val = corr.iloc[i, j]
            if not pd.isna(val):
                # Use different text color for better visibility
                text_color = "white" if abs(val) > 0.5 else "black"
                txt = f"{val:.2f}"
                ax.text(j, i, txt, ha="center", va="center", 
                       color=text_color, fontsize=8, fontweight='bold')

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson r")

    return fig


def scroll_hist(df_time_spent_on_ig_prep: pd.DataFrame, color: str = "blues", date_range: tuple = None) -> alt.Chart:
    """
    Histogram of total time spent on Instagram grouped by day.
    Assumes the dataframe is already preprocessed with 'date' and 'duration_sec' columns.
    
    Args:
        df_time_spent_on_ig_prep: Preprocessed dataframe
        color: Color scheme for the bars
        date_range: Optional tuple of (start_date, end_date) to filter data
    """
    df = df_time_spent_on_ig_prep.copy()
    
    # Apply date range filter if provided
    if date_range and len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    
    daily_time = df.groupby("date", as_index=False)["duration_sec"].sum()
    daily_time["duration_min"] = daily_time["duration_sec"] / 60
    
    chart = (
        alt.Chart(daily_time)
        .mark_bar()
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("duration_min:Q", title="Minutes on Instagram"),
            color=alt.Color("duration_min:Q", scale=alt.Scale(scheme="blues")),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("duration_min:Q", title="Minutes", format=".1f"),
            ],
        )
        .properties(title="Time Spent on Instagram per Day", width=800, height=400)
    )

    return chart


def saved_media_by_time(saved_collections: pd.DataFrame, saved_posts: pd.DataFrame, saved_music: pd.DataFrame, by_saved: str) -> alt.Chart:
    """Show saved media activity across all types grouped by time period"""
    time_data = []
    
    # Process saved collections
    if not saved_collections.empty:
        collections = saved_collections[saved_collections['title'].isna()].copy()
        collections['added_time'] = pd.to_datetime(collections['added_time'])
        collections = collections.dropna(subset=['added_time'])
        
        if by_saved == "years":
            collections['period'] = collections['added_time'].dt.year.astype(str)
            x_title = 'Year'
        elif by_saved == "months":
            collections['period'] = collections['added_time'].dt.to_period('M').astype(str)
            x_title = 'Month'
        elif by_saved == "weeks":
            collections['period'] = collections['added_time'].dt.strftime('%Y-W%U')
            x_title = 'Week'
        else:  # default to months
            collections['period'] = collections['added_time'].dt.to_period('M').astype(str)
            x_title = 'Month'
            
        time_collections = collections.groupby('period').size().reset_index(name='count')
        time_collections['type'] = 'Collections'
        time_data.append(time_collections)
    
    # Process saved posts
    if not saved_posts.empty:
        posts = saved_posts.copy()
        posts['timestamp'] = pd.to_datetime(posts['timestamp'], unit='s')
        
        if by_saved == "years":
            posts['period'] = posts['timestamp'].dt.year.astype(str)
        elif by_saved == "months":
            posts['period'] = posts['timestamp'].dt.to_period('M').astype(str)
        elif by_saved == "weeks":
            posts['period'] = posts['timestamp'].dt.strftime('%Y-W%U')
        else:  # default to months
            posts['period'] = posts['timestamp'].dt.to_period('M').astype(str)
            
        time_posts = posts.groupby('period').size().reset_index(name='count')
        time_posts['type'] = 'Posts/Reels'
        time_data.append(time_posts)
    
    # Process saved music
    if not saved_music.empty:
        music = saved_music.copy()
        # Try different timestamp columns
        timestamp_cols = ['string_map_data.Created At.timestamp', 'timestamp']
        timestamp_col = None
        for col in timestamp_cols:
            if col in music.columns:
                timestamp_col = col
                break
        
        if timestamp_col:
            music['timestamp'] = pd.to_datetime(music[timestamp_col], unit='s')
            music = music.dropna(subset=['timestamp'])
            
            if by_saved == "years":
                music['period'] = music['timestamp'].dt.year.astype(str)
            elif by_saved == "months":
                music['period'] = music['timestamp'].dt.to_period('M').astype(str)
            elif by_saved == "weeks":
                music['period'] = music['timestamp'].dt.strftime('%Y-W%U')
            else:  # default to months
                music['period'] = music['timestamp'].dt.to_period('M').astype(str)
                
            time_music = music.groupby('period').size().reset_index(name='count')
            time_music['type'] = 'Music'
            time_data.append(time_music)
    
    if not time_data:
        return None
    
    # Combine all data
    combined_data = pd.concat(time_data, ignore_index=True)
    
    # Sort by period for better visualization
    if by_saved == "years":
        combined_data = combined_data.sort_values('period')
    elif by_saved == "months":
        # Convert to datetime for proper sorting
        combined_data['sort_key'] = pd.to_datetime(combined_data['period'])
        combined_data = combined_data.sort_values('sort_key')
        combined_data = combined_data.drop('sort_key', axis=1)
    elif by_saved == "weeks":
        # Sort weeks properly
        combined_data['sort_key'] = combined_data['period']
        combined_data = combined_data.sort_values('sort_key')
        combined_data = combined_data.drop('sort_key', axis=1)
    
    # Create chart based on grouping type
    if by_saved == "weeks":
        # For weeks, use bar chart as there might be many data points
        chart = alt.Chart(combined_data).mark_bar().encode(
            x=alt.X('period:N', title=x_title, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('count:Q', title='Number of Saves'),
            color=alt.Color('type:N', legend=alt.Legend(title="Media Type")),
            tooltip=['period', 'type', 'count']
        ).properties(
            title=f'Saved Media Activity by {x_title}',
            width=700,
            height=400
        )
    else:
        # For years and months, use line chart
        chart = alt.Chart(combined_data).mark_line(point=True).encode(
            x=alt.X('period:N', title=x_title, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('count:Q', title='Number of Saves'),
            color=alt.Color('type:N', legend=alt.Legend(title="Media Type")),
            tooltip=['period', 'type', 'count']
        ).properties(
            title=f'Saved Media Activity by {x_title}',
            width=700,
            height=400
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
