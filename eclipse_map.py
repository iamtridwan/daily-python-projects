"""
Visualizing the 2026 Eclipse with Python: Day 2 - Interactive Streamlit Web Map
Imports astronomy calculation engine from eclipse.py and renders an interactive
Folium map with local eclipse timing, search geocoding, and live countdown.
"""

import datetime
from zoneinfo import ZoneInfo

import folium
import streamlit as st
from streamlit_folium import st_folium

# Import astronomy engine and preset cities from Day 1 script
from eclipse import (
    PRESET_CITIES,
    compute_eclipse_details,
    format_duration,
    format_full_time,
    resolve_location,
)

# Page Configuration
st.set_page_config(
    page_title="2026 Total Solar Eclipse Map",
    page_icon="🌒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling matching reference UI
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        height: 2.75rem;
        width: 100%;
        border: none;
    }
    .stButton>button:hover {
        background-color: #E03E3E;
        color: white;
    }
    .info-card {
        background-color: #EBF3FE;
        border-radius: 8px;
        padding: 12px 16px;
        color: #1E3A8A;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .countdown-header {
        font-size: 1.15rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CACHING LAYER
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def cached_compute_eclipse_details(lat: float, lon: float) -> dict:
    """Cached wrapper for Skyfield eclipse computation engine."""
    return compute_eclipse_details(lat, lon)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_resolve_location(query: str) -> tuple[str, float, float, str]:
    """Cached wrapper for geocoding location query. Returns (display_name, lat, lon, tz_name_str)."""
    display_name, lat, lon, tz = resolve_location(query)
    return display_name, lat, lon, tz.key

# ==============================================================================
# ECLIPSE PATH DATA
# ==============================================================================
PATH_COORDS = [
    [78.5, -12.0],        # Greenland / Arctic
    [66.5, -23.5],        # Westfjords Iceland
    [64.1466, -21.9426],  # Reykjavik
    [55.0, -18.0],        # North Atlantic
    [45.0, -9.0],         # Atlantic off NW Spain
    [43.4623, -3.8099],   # Santander
    [43.2630, -2.9350],   # Bilbao
    [42.3440, -3.6969],   # Burgos
    [41.6488, -0.8891],   # Zaragoza
    [39.5696, 2.6502],    # Palma de Mallorca
    [36.8, 3.3],          # Exiting into Mediterranean / Algeria
]

# Default selected location (Boston as shown in Image 2)
DEFAULT_LAT = 42.361
DEFAULT_LON = -71.050
DEFAULT_NAME = "Boston"

# Initialize Session State
if "selected_lat" not in st.session_state:
    st.session_state.selected_lat = DEFAULT_LAT
    st.session_state.selected_lon = DEFAULT_LON
    st.session_state.selected_name = DEFAULT_NAME

# ==============================================================================
# LIVE COUNTDOWN BANNER
# ==============================================================================
def get_countdown_string() -> str:
    greatest_eclipse_time = datetime.datetime(2026, 8, 12, 17, 46, tzinfo=datetime.timezone.utc)
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if now_utc >= greatest_eclipse_time:
        return "⏱ Eclipse occurred on Aug 12, 2026 (17:46 UT)"

    diff = greatest_eclipse_time - now_utc
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    return f"⏱ **{days}d {hours}h {minutes}m** until greatest eclipse (17:46 UT, Aug 12)"

# Display Countdown Header
st.markdown(f"<div class='countdown-header'>{get_countdown_string()}</div>", unsafe_allow_html=True)

# ==============================================================================
# SEARCH BAR LAYOUT
# ==============================================================================
col_search, col_btn = st.columns([4, 1])

with col_search:
    search_query = st.text_input(
        label="Location Search",
        placeholder="Try 'Lisbon', 'Boston', 'Palma de Mallorca', or '43.26, -2.94'",
        label_visibility="collapsed",
        key="search_input"
    )

with col_btn:
    search_clicked = st.button("Search")

if search_clicked and search_query.strip():
    try:
        name, lat, lon, tz_str = cached_resolve_location(search_query.strip())
        st.session_state.selected_lat = lat
        st.session_state.selected_lon = lon
        st.session_state.selected_name = name
    except Exception as e:
        st.error(f"Could not find location '{search_query}'. Please try again.")

# ==============================================================================
# MAP RENDERING (FOLIUM)
# ==============================================================================
# Center map near selected location if zoomed in, or default Atlantic overview
map_center = [st.session_state.selected_lat, st.session_state.selected_lon] if st.session_state.selected_lat != DEFAULT_LAT else [44.0, -15.0]
zoom_lvl = 6 if st.session_state.selected_lat != DEFAULT_LAT else 4

m = folium.Map(
    location=map_center,
    zoom_start=zoom_lvl,
    tiles="OpenStreetMap",
    control_scale=True
)

# Draw Totality Path Polyline (Red line)
folium.PolyLine(
    locations=PATH_COORDS,
    color="#FF3333",
    weight=4,
    opacity=0.85,
    tooltip="Path of Totality - August 12, 2026"
).add_to(m)

# Pre-mark featured cities from Day 1 script
for city in PRESET_CITIES:
    lat = city["lat"]
    lon = city["lon"]
    details = cached_compute_eclipse_details(lat, lon)

    # Color logic: Green for totality, Orange for >90% partial, Blue for moderate
    if details["is_total"]:
        color = "#10B981"  # Green
        tot_label = f"Totality ({format_duration(details['totality_seconds'])})"
    elif details["max_coverage"] >= 90.0:
        color = "#F59E0B"  # Orange
        tot_label = f"Partial ({details['max_coverage']:.1f}%)"
    else:
        color = "#3B82F6"  # Blue
        tot_label = f"Partial ({details['max_coverage']:.1f}%)"

    popup_text = f"<b>{city['name']} ({city['country']})</b><br>{tot_label}"

    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.9,
        popup=popup_text,
        tooltip=city["name"]
    ).add_to(m)

# Add Marker for Selected Location (Red Star Pin)
folium.Marker(
    location=[st.session_state.selected_lat, st.session_state.selected_lon],
    popup=st.session_state.selected_name,
    tooltip=st.session_state.selected_name,
    icon=folium.Icon(color="red", icon="star", prefix="fa")
).add_to(m)

# Render Map & Handle Clicks
map_data = st_folium(m, width="100%", height=580, key="eclipse_folium_map")

# Update selected location if map clicked
if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]

    # Check if click position actually changed
    if abs(clicked_lat - st.session_state.selected_lat) > 0.001 or abs(clicked_lon - st.session_state.selected_lon) > 0.001:
        st.session_state.selected_lat = clicked_lat
        st.session_state.selected_lon = clicked_lon
        st.session_state.selected_name = f"({clicked_lat:.3f}, {clicked_lon:.3f})"
        st.rerun()

# ==============================================================================
# SIDEBAR ECLIPSE DETAIL PANEL
# ==============================================================================
with st.sidebar:
    curr_lat = st.session_state.selected_lat
    curr_lon = st.session_state.selected_lon
    curr_name = st.session_state.selected_name

    st.markdown(f"### 📍 {curr_name}")
    st.caption(f"{curr_lat:.3f}, {curr_lon:.3f}")

    # Fetch cached eclipse details for selected point
    details = cached_compute_eclipse_details(curr_lat, curr_lon)

    # Timezone lookup for selected point
    display_name, _, _, tz_str = cached_resolve_location(f"{curr_lat}, {curr_lon}")
    tz = ZoneInfo(tz_str)

    if not details["visible"]:
        st.warning("No eclipse visible from this location on August 12, 2026.")
    else:
        cov_val = details["max_coverage"]
        mag_val = details["magnitude"]

        # Blue Status Card / Pill matching reference UI
        if details["is_total"]:
            tot_dur = format_duration(details["totality_seconds"])
            st.markdown(f"<div class='info-card'>🌑 100.00% total eclipse ({tot_dur})</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='info-card'>🌑 {cov_val:.2f}% partial eclipse</div>", unsafe_allow_html=True)

        # Timing Information
        st.markdown("#### **Timing (local time and UT):**")

        start_local, start_ut = format_full_time(details["start_time_utc"], tz)
        max_local, max_ut   = format_full_time(details["max_time_utc"], tz)
        end_local, end_ut     = format_full_time(details["end_time_utc"], tz)

        st.markdown(f"• **Start:** {start_local} {start_ut}")
        st.markdown(f"• **Max:** {max_local} {max_ut}")
        st.markdown(f"• **End:** {end_local} {end_ut}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**Magnitude:** {mag_val:.3f}")
        st.markdown(f"**Obscuration:** {cov_val:.2f}%")

# ==============================================================================
# FOOTER ATTRIBUTION
# ==============================================================================
st.markdown("<br><div style='text-align: center; color: #6B7280; font-size: 0.85rem;'>Astronomy: Skyfield + JPL DE421 ephemeris. Map tiles: OpenStreetMap. Path: computed umbra</div>", unsafe_allow_html=True)
