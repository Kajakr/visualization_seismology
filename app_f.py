import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
import requests

st.set_page_config(layout = "wide")

BASE_DIR = Path(__file__).parent

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

@st.cache_data(ttl = 24 * 3600)
def load_tectonics(url: str) -> dict:
    r = requests.get(url, timeout = 10)
    r.raise_for_status()
    return r.json()

df = load_data(BASE_DIR/"earthquakes_merged_f.csv")

st.title("Earthquakes in Europe")
st.write("This app presents earthquakes of magnitude 5.0 and higher in Europe recorded between 2015 and 2024. "
         " We can see strong spatial clustering along active tectonic regions, particularly in Southern and Southeastern Europe, while Northern and Western Europe show lower seismic activity.")

col_left, col_right = st.columns([5, 4])

top_region = (
    df.dropna(subset = ["region"])
      .groupby(["year", "region"]).size()
      .reset_index(name = "n")
      .sort_values(["year", "n"], ascending = [True, False])
      .drop_duplicates("year")[["year", "region"]]
      .rename(columns = {"region": "top_region"}))
top_mags = (
    df.groupby("year")["magnitude"]
      .apply(lambda s: s.nlargest(3).to_list() + [None, None, None])
      .apply(lambda L: L[:3])
      .apply(pd.Series)
      .reset_index())
top_mags.columns = ["year", "m1", "m2", "m3"]

per_year_df = (
    df.groupby("year")
      .size()
      .reset_index(name = "amount")
      .sort_values("year"))
per_year_df = per_year_df.merge(top_region, on = "year", how = "left").merge(top_mags, on = "year", how = "left")
custom = per_year_df[["year", "amount", "top_region", "m1", "m2", "m3"]].to_numpy()

years_barchart = per_year_df["year"].astype(int).tolist()
amount_barchart = per_year_df["amount"].tolist()
main_barchart = go.Figure(data = [go.Bar(
    x = years_barchart, 
    y = amount_barchart,
    customdata = custom,
    hovertemplate = (
        "Information for %{customdata[0]}<br>"
        "amount of earthquakes: %{customdata[1]}<br>"
        "region with the biggest amount: %{customdata[2]}<br>"
        "the strongest magnitude: %{customdata[3]:.1f}<br>"
        "the second strongest magnitude: %{customdata[4]:.1f}<br>"
        "the third strongest magnitude: %{customdata[5]:.1f}"
        "<extra></extra>"))])
main_barchart.update_traces(
    marker_color = "rgb(150, 120, 200)",
    marker_line_color = "rgb(80, 50, 130)",
    marker_line_width = 1.5, 
    opacity = 0.6)
main_barchart.update_layout(
    title = dict(
        text = "<b>Amount of earthquakes in Europe of magnitude 5 and higher</b>",
        font = dict(size = 20,
            color = 'black',
            family = 'Arial, sans-serif'),
        xanchor = 'right',
        x = 0.75),
    xaxis_title = "Year",
    yaxis_title = "Amount",
    xaxis_type = "category",
    clickmode = "event+select")

if "barchart_version" not in st.session_state:
    st.session_state.barchart_version = 0

with col_left:
    st.markdown("##### Please select a year by clicking on the corresponding bar")
    if st.button("Show all years"):
        st.session_state.barchart_version += 1
        st.rerun()
    selected = plotly_events(
        main_barchart,
        click_event = True,
        select_event = True,
        key = f"year_bar_selection_{st.session_state.barchart_version}")
    
selected_year = int(selected[0]["x"]) if selected else None
df_filtered = df.copy() if selected_year is None else df[df["year"] == selected_year].copy()

with col_left:
    st.write(f"**Selected year: {selected_year if selected_year is not None else 'all years'}**")

with col_left:
    left_sub_col, right_sub_col = st.columns([6, 2])
    with left_sub_col:    
        st.markdown("#### Earthquake epicenters")
    with right_sub_col:
        show_tectonics = st.checkbox("Show Tectonic Plate Boundaries", value=False)

mag_bins_dot = [5.0, 5.15, 5.35, 5.55, 5.75, 6.0, 6.15, 6.35, 6.55, 6.75, 7.0, 7.5, float("inf")]
mag_labels_dot = ["5.0–5.1","5.2–5.3","5.4–5.5","5.6–5.7","5.8–5.9","6.0–6.1","6.2–6.3","6.4–6.5","6.6-6.7","6.8-6.9","7.0-7.5","7.5+"]
 
df_filtered['magnitude_category'] = pd.cut( df_filtered['magnitude'],
        bins = mag_bins_dot, 
        labels = mag_labels_dot,
        right = False)

color_map_dots = {
    "5.0–5.1": "#0B7C38",
    "5.2–5.3": "#0FAE3A",
    "5.4–5.5": "#00FF2A",
    "5.6–5.7": "#B6FF00",
    "5.8–5.9": "#FFF200",
    "6.0–6.1": "#FFC300",
    "6.2–6.3": "#FF8A00",
    "6.4–6.5": "#FF4D00",
    "6.6-6.7": "#FF0000",
    "6.8-6.9": "#BD0202",
    "7.0-7.5": "#740C0C",
    "7.5+":    "#000000",}
   
dot_map = px.scatter_map(
    df_filtered,
    category_orders = {"magnitude_category": mag_labels_dot},
    lat = "latitude",
    lon = "longitude",
    color = "magnitude_category",
    color_discrete_map = color_map_dots,
    hover_data = {"latitude": False, "longitude": False, "magnitude_category": False, "magnitude": True},
    zoom = 2.6,
    center = {"lat": 50, "lon": 15},
    height = 600,)
dot_map.update_layout(
    legend = dict(title = dict(text = "Magnitude Category")),)

dot_map.update_traces(marker = dict(size = 8))
if show_tectonics:
    url = "https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json"
    try:
        tectonic_data = load_tectonics(url)
        for feature in tectonic_data['features']:
            coords = feature['geometry']['coordinates']
            if feature['geometry']['type'] == 'LineString':
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                dot_map.add_trace(go.Scattermap(
                    lon = lons,
                    lat = lats,
                    mode = 'lines',
                    line = dict(width = 2, color = 'red'),
                    name = 'Tectonic Boundaries',
                    showlegend = False,
                    hoverinfo = 'skip'))
    except Exception as e:
        st.warning(f"Could not load tectonic plate data: {e}")
with col_left:
    st.plotly_chart(dot_map, width = "stretch", config = {"displayModeBar": False})

df_regions = df_filtered.dropna(subset = ["region"]).copy()
df_regions["region"] = df_regions["region"].str.title().str.strip()
by_region = df_regions.groupby("region").size().reset_index(name = "count")
count_bins_chor = [-1, 1, 3, 6, 10, 20, float("inf")]
count_labels_chor = ["1", "2–3", "4–6", "7–10", "11–20", "21+"]
by_region["count_bin"] = pd.cut(by_region["count"], bins = count_bins_chor, labels = count_labels_chor)
color_map_counts = {
    "1":   "#4ae1f5",
    "2–3":   "#3bbcd9",
    "4–6":   "#2b88b8",
    "7–10":  "#1c5f9a",
    "11–20": "#123a73",
    "21+":   "#061849",}

choropleth_map = px.choropleth(
    by_region,
    locations = "region",
    locationmode = "country names",
    color = "count_bin",
    color_discrete_map = color_map_counts,
    category_orders = {"count_bin": count_labels_chor},
    title = "Amount of earthquakes in European countries/regions in the selected year",
    labels = {"count": "Amount", "count_bin": "Number of Events"},)
choropleth_map.update_geos(
    fitbounds = "locations",
    projection_type = "natural earth",
    showcountries = True)
choropleth_map.update_traces(
    hovertemplate = "<extra></extra>")
choropleth_map.update_layout(
    title = dict(
        font = dict(size = 20, color = "black", family = "Arial, sans-serif"),),)
with col_right:
    for _ in range(6):
        st.write("")
    st.plotly_chart(choropleth_map, width = "stretch", config = {"displayModeBar": False})

top3 = (
    df_filtered
    .dropna(subset = ["latitude", "longitude", "magnitude"])
    .nlargest(3, "magnitude")
    .copy())

top3 = top3.sort_values("magnitude_category")
mini_map = px.scatter_map(
    top3,
    lat = "latitude",
    lon = "longitude",
    color = "magnitude_category",
    color_discrete_map = color_map_dots,
    hover_data = {"magnitude": True, "depth": True, "stations_used": True, "region": True, "magnitude_category": False},
    zoom = 3,
    height = 400,)
mini_map.update_traces(marker = dict(size = 14))
mini_map.update_layout(
    legend = dict(
        title = dict(text = "Magnitude Category"),),)

with col_right:
    for _ in range(4):
        st.write("")
    st.markdown("#### Top 3 strongest earthquakes")
    st.plotly_chart(mini_map, width = "stretch", config = {"displayModeBar": False})

regions = ["All"] + sorted(df_filtered["region"].dropna().unique())
st.markdown("")

st.markdown("##### Please select a country/region for the pie chart")
region_selected = st.selectbox(
    "",
    options=regions,
    key = "region_select")

if region_selected == "All":
    df_pie_filtered = df_filtered.copy()
else:
    df_pie_filtered = df_filtered[df_filtered["region"] == region_selected].copy()
     
mag_bins_pie = [5.0, 5.15, 5.35, 5.55, 5.75, 6.0, 6.15, 6.35, 6.55, float("inf")]
mag_labels_pie = ["5.0–5.1","5.2–5.3","5.4–5.5","5.6–5.7","5.8–5.9","6.0–6.1","6.2–6.3","6.4–6.5","6.6+"]  

df_pie_filtered["mag_cluster"] = pd.cut(df_pie_filtered["magnitude"], bins = mag_bins_pie, labels = mag_labels_pie, right = False)

pie_color_map = {
    "5.0–5.1": color_map_dots["5.0–5.1"],
    "5.2–5.3": color_map_dots["5.2–5.3"],
    "5.4–5.5": color_map_dots["5.4–5.5"],
    "5.6–5.7": color_map_dots["5.6–5.7"],
    "5.8–5.9": color_map_dots["5.8–5.9"],
    "6.0–6.1": color_map_dots["6.0–6.1"],
    "6.2–6.3": color_map_dots["6.2–6.3"],
    "6.4–6.5": color_map_dots["6.4–6.5"],
    "6.6+": color_map_dots["6.8-6.9"],}

if df_pie_filtered.empty:
    st.warning("No data for the selected year(s) and region.")
else:
    df_pie = (
        df_pie_filtered
        .groupby("mag_cluster")
        .size()
        .reset_index(name = "count"))
    fig_pie = px.pie(
        df_pie,
        values = "count",
        names = "mag_cluster",
        color = "mag_cluster",
        category_orders = {"mag_cluster": mag_labels_pie},
        color_discrete_map = pie_color_map,
        title = "Distribution of earthquake magnitudes in the selected country/region")
    fig_pie.update_layout(
        legend = dict(
            title = dict(text = "Magnitude Category"),),
        title = dict(
            font = dict(size = 20),
            x = 0.45,  
            xanchor = 'center'))


    st.plotly_chart(fig_pie, width = "stretch")

