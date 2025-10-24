import pandas as pd
import altair as alt
from datetime import datetime

def saved_collections_over_time(saved_collections: pd.DataFrame) -> alt.Chart:
    """Show saved collections growth over time"""
    if saved_collections.empty:
        return None
    
    # Filter out collection folders and keep only saved items
    saved_items = saved_collections[saved_collections['title'].isna()].copy()
    
    if saved_items.empty:
        return None
    
    # Convert added_time to datetime and extract month-year
    saved_items['added_time'] = pd.to_datetime(saved_items['added_time'])
    saved_items['month_year'] = saved_items['added_time'].dt.to_period('M').dt.to_timestamp()
    
    # Count saved items per month
    monthly_counts = saved_items.groupby('month_year').size().reset_index(name='count')
    monthly_counts['cumulative_count'] = monthly_counts['count'].cumsum()
    
    # Create area chart
    chart = alt.Chart(monthly_counts).mark_area(
        opacity=0.6,
        interpolate='monotone'
    ).encode(
        x=alt.X('month_year:T', title='Date'),
        y=alt.Y('cumulative_count:Q', title='Cumulative Saved Items'),
        tooltip=['month_year:T', 'cumulative_count:Q']
    ).properties(
        title='Saved Collections Growth Over Time',
        width=600,
        height=400
    )
    
    return chart

def saved_posts_analysis(saved_posts: pd.DataFrame) -> alt.Chart:
    """Analyze saved posts by media owner"""
    if saved_posts.empty:
        return None
    
    # Count posts by media owner
    owner_counts = saved_posts['media_owner'].value_counts().head(15).reset_index()
    owner_counts.columns = ['media_owner', 'count']
    
    # Create bar chart
    chart = alt.Chart(owner_counts).mark_bar().encode(
        x=alt.X('count:Q', title='Number of Saved Posts'),
        y=alt.Y('media_owner:N', 
                title='Media Owner',
                sort='-x'),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='blues')),
        tooltip=['media_owner', 'count']
    ).properties(
        title='Top 15 Most Saved Media Owners',
        width=600,
        height=400
    )
    
    return chart

def saved_locations_chart(saved_locations: pd.DataFrame) -> alt.Chart:
    """Create a chart for saved locations (since we can't do maps with Altair without lat/lon)"""
    if saved_locations.empty:
        return None
    
    # Count locations by name
    location_counts = saved_locations['value'].value_counts().head(10).reset_index()
    location_counts.columns = ['location', 'count']
    
    # Create bar chart
    chart = alt.Chart(location_counts).mark_bar().encode(
        x=alt.X('count:Q', title='Number of Saves'),
        y=alt.Y('location:N', 
                title='Location Name',
                sort='-x'),
        color=alt.Color('count:Q', scale=alt.Scale(scheme='greens')),
        tooltip=['location', 'count']
    ).properties(
        title='Top 10 Most Saved Locations',
        width=600,
        height=400
    )
    
    return chart

def saved_media_timeline(saved_collections: pd.DataFrame, saved_posts: pd.DataFrame) -> alt.Chart:
    """Create a timeline of all saved media types"""
    timeline_data = []
    
    # Process saved collections
    if not saved_collections.empty:
        collections_timeline = saved_collections[saved_collections['title'].isna()].copy()
        collections_timeline['added_time'] = pd.to_datetime(collections_timeline['added_time'])
        collections_timeline = collections_timeline.dropna(subset=['added_time'])
        for _, row in collections_timeline.iterrows():
            timeline_data.append({
                'type': 'Collection Item',
                'date': row['added_time'],
                'value': row['value']
            })
    
    # Process saved posts
    if not saved_posts.empty:
        saved_posts_copy = saved_posts.copy()
        saved_posts_copy['timestamp'] = pd.to_datetime(saved_posts_copy['timestamp'], unit='s')
        for _, row in saved_posts_copy.iterrows():
            timeline_data.append({
                'type': 'Saved Post',
                'date': row['timestamp'],
                'value': row['media_owner']
            })
    
    if not timeline_data:
        return None
    
    timeline_df = pd.DataFrame(timeline_data)
    timeline_df = timeline_df.dropna(subset=['date'])
    timeline_df['year_month'] = timeline_df['date'].dt.to_period('M').astype(str)
    
    # Count by type and month
    monthly_type_counts = timeline_df.groupby(['year_month', 'type']).size().reset_index(name='count')
    
    # Create stacked bar chart
    chart = alt.Chart(monthly_type_counts).mark_bar().encode(
        x=alt.X('year_month:N', title='Month'),
        y=alt.Y('count:Q', title='Number of Saved Items'),
        color=alt.Color('type:N', legend=alt.Legend(title="Media Type")),
        tooltip=['year_month', 'type', 'count']
    ).properties(
        title='Saved Media Timeline by Type',
        width=700,
        height=400
    )
    
    return chart

def collections_breakdown(saved_collections: pd.DataFrame) -> alt.Chart:
    """Show breakdown of collections"""
    if saved_collections.empty:
        return None
    
    # Count items per collection (where title is not None)
    collections = saved_collections[saved_collections['title'].notna() & 
                                  (saved_collections['title'] != 'Collection')].copy()
    
    if collections.empty:
        return None
    
    collection_counts = collections['title'].value_counts().reset_index()
    collection_counts.columns = ['collection', 'count']
    
    chart = alt.Chart(collection_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(field="collection", type="nominal", 
                       legend=alt.Legend(title="Collections")),
        tooltip=['collection', 'count']
    ).properties(
        title='Saved Items Distribution by Collection',
        width=400,
        height=400
    )
    
    return chart
