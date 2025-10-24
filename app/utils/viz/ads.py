import pandas as pd
import pycountry
import altair as alt
from vega_datasets import data

# --------- ads information -----------
def ads_bar(df):
    bars_df = pd.DataFrame({
        "metric": [
            "Total advertisers",
            "has_data_file_custom_audience (True)",
            "has_remarketing_custom_audience (True)",
            "has_in_person_store_visit (True)",
        ],
        "count": [
            len(df),
            int(df["has_data_file_custom_audience"].sum()),
            int(df["has_remarketing_custom_audience"].sum()),
            int(df["has_in_person_store_visit"].sum()),
        ],
    })
    bars_df["percent"] = (bars_df["count"] / len(df) * 100).round(1)
    bars_df["percent_str"] = bars_df["percent"].astype(str) + "%"

    chart = (
        alt.Chart(bars_df)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("metric:N", sort="-x", title=""),
            tooltip=[
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("percent:Q", title="Percent", format=".1f")
            ],
        ).properties(
            title="Instagram Advertiser Audience Features (Counts and %)",
            width=600,
            height=220
        )
    )
    return chart

def ads_countries_map(df):

    agg = (
        df.groupby("country", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    fix = {
        "United States": "United States of America",
        "Czech Republic": "Czechia",
        "South Korea": "Korea, South",
        "North Korea": "Korea, North",
        "Ivory Coast": "Côte d’Ivoire",
        "Swaziland": "Eswatini",
        "Macedonia": "North Macedonia",
        "Myanmar (Burma)": "Myanmar",
        # cas impossible à faire correspondre sur la carte actuelle
        "Socialist Federal Republic of Yugoslavia": None,
    }
    agg["country"] = (
        agg["country"]
        .astype(str).str.strip()
        .replace(fix)
    )
    agg = agg.dropna(subset=["country"]).copy()
    agg["count"] = agg["count"].astype(int)

    def get_iso_numeric(country_name):
        try:
            country = pycountry.countries.lookup(country_name)
            return int(country.numeric)
        except LookupError:
            return None

    agg['id'] = agg['country'].apply(get_iso_numeric)

    countries = alt.topo_feature(data.world_110m.url, 'countries')
    chart = (
        alt.Chart(countries)
        .mark_geoshape(stroke='white', strokeWidth=0.5)
        .transform_lookup(
            lookup='id',
            from_=alt.LookupData(agg, key='id', fields=['country', 'count'])
        )
        .encode(
            color=alt.Color('count:Q', title='Advertisers'),
            tooltip=[
                alt.Tooltip('country:N', title='Country'),
                alt.Tooltip('count:Q', title='Advertisers', format=',')
            ]
        )
        .project('equalEarth')
        .properties(width=900, height=500, title='Advertisers per country')
    )

    return chart

def ads_enriched_missing_values(enriched):
    # compute counts
    count = enriched.count().reset_index()
    count.columns = ["column", "count"]

    # add frequency (%)
    total_rows = len(enriched)
    pct = (count.loc[count['column'] == 'qid', 'count'].iloc[0] / total_rows) * 100
    count["freq_percent"] = (count["count"] / total_rows * 100).round(1)

    # build bar chart
    bar = (
        alt.Chart(count)
        .mark_bar(color="#4C78A8")
        .encode(
            x=alt.X("column:N", title="Field"),
            y=alt.Y("count:Q", title="Non-missing values"),
            tooltip=[
                alt.Tooltip("column:N", title="Field"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("freq_percent:Q", title="Frequency (%)"),
            ]
        )
    )
    rule = alt.Chart(pd.DataFrame({"y": [total_rows]})).mark_rule(color="red").encode(
        y="y:Q"
    )

    return (bar + rule).properties(
        width=600,
        title=f"Enriched values in the datasets {pct:.2f}%"
    )

def ads_inception_year(enriched, signup_ts):
    # -- Extract inception year safely
    enriched["inception_year"] = pd.to_datetime(
        enriched["inception"], errors="coerce"
    ).dt.year

    # -- Aggregate by year and cumulative sum
    by_year = (
        enriched.dropna(subset=["inception_year"])
        .groupby("inception_year")
        .size()
        .reset_index(name="count")
        .sort_values("inception_year")
    )
    by_year["cum"] = by_year["count"].cumsum()

    # -- Compute coverage %
    total_rows = len(enriched)
    known_rows = int(by_year["count"].sum())
    missing_rows = total_rows - known_rows
    by_year["coverage_pct"] = (by_year["cum"] / total_rows * 100).round(1)

    # -- Instagram signup timestamp → year
    signup_year = pd.to_datetime(signup_ts, unit="s", utc=True).year

    # -- Base chart
    base = alt.Chart(by_year).encode(
        x=alt.X("inception_year:Q", title="Inception year", axis=alt.Axis(format="d"))
    )

    area = base.mark_area(opacity=0.25).encode(
        y=alt.Y("cum:Q", title="Cumulative companies")
    )

    line = base.mark_line(color="#4C78A8").encode(y="cum:Q")

    pts = base.mark_circle(size=32, color="#4C78A8").encode(
        y="cum:Q",
        tooltip=[
            alt.Tooltip("inception_year:Q", title="Year"),
            alt.Tooltip("count:Q", title="New that year"),
            alt.Tooltip("cum:Q", title="Cumulative"),
            alt.Tooltip("coverage_pct:Q", title="Coverage (%)")
        ]
    )

    # -- Vertical rule for signup date
    rule = alt.Chart(pd.DataFrame({"x": [signup_year]})).mark_rule(
        color="red", strokeWidth=2
    ).encode(x="x:Q")

    # -- Annotation label placed above the plot
    label = alt.Chart(pd.DataFrame({"x": [signup_year]})).mark_text(
        text="Instagram signup date",
        align="center",
        dy=-150,          # push label higher
        color="red",
        fontSize=13,
        fontWeight="bold"
    ).encode(x="x:Q")

    # -- Combine layers
    chart = (area + line + pts + rule + label).properties(
        width=700,
        height=380,
        title=f"Cumulative company inceptions (known={known_rows}, missing={missing_rows}, total={total_rows})"
    )

    return chart
