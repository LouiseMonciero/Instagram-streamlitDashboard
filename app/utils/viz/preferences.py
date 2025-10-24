import pandas as pd
import altair as alt

# --------- preferences -------------
def clusters_podium(clusters_data: list[dict], clusters_compositions: dict) -> alt.Chart:
    
    clusters_compositions = {"0":["Crafts","Ground Transportation","Gym Workouts","Body Modification","AR/VR Games","Water Sports","Visual Arts","Beauty Product Types","Technology","Video Games by Game Mechanics","Types of Sports","Beauty Products","Cars & Trucks","Body Art","Interior Design"],"1":["Cosplay"],"2":["Foods","Cakes","Recipes","Desserts"],"3":["Fish","Birds","Wild Cats","Reptiles","Lions","Mammals","Dogs","Aquatic Animals","Animals","Farm Animals","Rabbits","Cats","Pets"],"4":["Drawing & Sketching","Painting","Watercolor Painting"],"5":["Beauty","Makeup","Faces & Face Care","Hair Care"],"6":["Baked Goods","Vacation & Leisure Activities","Asia Travel","Western Europe Travel","Travel Destinations","Europe Travel","Travel by Region"],"7":["Video Games","Anime TV & Movies","Animation TV & Movies","Dance","TV & Movies by Genre","Digital Art","Toys"],"8":["Fashion Products","Fashion","Fashion Styles & Trends","Fashion Media & Entertainment","Clothing & Accessories"],"9":["Non-Alcoholic Beverages","Drinks","Coffee Drinks"]}
    
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
    clusters_compositions = {"0":["Crafts","Ground Transportation","Gym Workouts","Body Modification","AR/VR Games","Water Sports","Visual Arts","Beauty Product Types","Technology","Video Games by Game Mechanics","Types of Sports","Beauty Products","Cars & Trucks","Body Art","Interior Design"],"1":["Cosplay"],"2":["Foods","Cakes","Recipes","Desserts"],"3":["Fish","Birds","Wild Cats","Reptiles","Lions","Mammals","Dogs","Aquatic Animals","Animals","Farm Animals","Rabbits","Cats","Pets"],"4":["Drawing & Sketching","Painting","Watercolor Painting"],"5":["Beauty","Makeup","Faces & Face Care","Hair Care"],"6":["Baked Goods","Vacation & Leisure Activities","Asia Travel","Western Europe Travel","Travel Destinations","Europe Travel","Travel by Region"],"7":["Video Games","Anime TV & Movies","Animation TV & Movies","Dance","TV & Movies by Genre","Digital Art","Toys"],"8":["Fashion Products","Fashion","Fashion Styles & Trends","Fashion Media & Entertainment","Clothing & Accessories"],"9":["Non-Alcoholic Beverages","Drinks","Coffee Drinks"]}
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
        
        # Create one entry per category with its position in the list
        for cat_idx, cat in enumerate(categories):
            grid_data.append({
                "cluster_name": cluster_name,
                "category": cat,
                "col": col,
                "row": row,
                "cat_idx": cat_idx,  # Position of category within cluster
                "weight": cluster.get('weights', 0)
            })
    
    df = pd.DataFrame(grid_data)
    
    # Create background rectangles for each cluster cell
    cluster_bg = pd.DataFrame({
        "col": [i % n_cols for i in range(min(len(clusters_data), max_clusters))],
        "row": [i // n_cols for i in range(min(len(clusters_data), max_clusters))],
        "cluster_name": [c.get('cluster_name', f"Cluster {i}") for i, c in enumerate(clusters_data[:max_clusters])],
        "weight": [c.get('weights', 0) for c in clusters_data[:max_clusters]]
    })
    
    # Background rectangles
    bg_chart = alt.Chart(cluster_bg).mark_rect(
        stroke='white',
        strokeWidth=2,
        opacity=0.1
    ).encode(
        x=alt.X('col:O', title=None, axis=None),
        y=alt.Y('row:O', title=None, axis=None),
        color=alt.Color('cluster_name:N', legend=None),
        tooltip=[
            alt.Tooltip('cluster_name:N', title='Cluster'),
            alt.Tooltip('weight:Q', title='Weight'),
        ]
    )
    
    # Cluster name labels (big and bold at the top)
    label_chart = alt.Chart(cluster_bg).mark_text(
        fontSize=20,
        fontWeight="bold",
        dy=-120,  # Move up
        align='center'
    ).encode(
        x=alt.X('col:O', title=None, axis=None),
        y=alt.Y('row:O', title=None, axis=None),
        text='cluster_name:N',
        color=alt.Color('cluster_name:N', legend=None)
    )
    
    # Categories text - each category on its own line
    categories_chart = alt.Chart(df).mark_text(
        fontSize=11,
        align='center',
        baseline='middle',
        dy=0
    ).encode(
        x=alt.X('col:O', title=None, axis=None),
        y=alt.Y('row:O', title=None, axis=None),
        text='category:N',
        color=alt.Color('cluster_name:N', legend=None),
        # Use cat_idx to offset each category vertically
        yOffset=alt.YOffset('cat_idx:Q', scale=alt.Scale(domain=[0, 15], range=[-80, 100])),
        tooltip=[
            alt.Tooltip('cluster_name:N', title='Cluster'),
            alt.Tooltip('category:N', title='Category'),
        ]
    )
    
    return (bg_chart + label_chart + categories_chart).properties(
        width=1000,
        height=800,
        title="Clusters grid (3x4)"
    ).configure_view(
        strokeWidth=0
    )
