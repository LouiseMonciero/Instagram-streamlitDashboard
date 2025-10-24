import pandas as pd
import altair as alt

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
