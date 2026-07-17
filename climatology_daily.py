import streamlit as st
import requests
import time
import pandas as pd
import datetime
import plotly.graph_objects as go

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

# Set page configuration for a wider layout and custom title
st.set_page_config(page_title="Climate Dashboard", layout="wide")

@st.cache_data(ttl=60*60*24)
def geocode_city(city):
    try:
        response = requests.get(GEO_URL, params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('results'):
            st.error(f"City '{city}' not found")
            return None

        return data['results'][0]
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return None

@st.cache_data(ttl=60*60*24)
def get_weather(years, lat, long):
    start_year = 2025 - years + 1
    end_year = 2025
    try:
        response = requests.get(WEATHER_URL, params={
            "latitude": lat,
            "longitude": long,
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        }, timeout=20)
        
        response.raise_for_status()
        data = response.json()
        
        if "daily" not in data:
            st.error("Daily weather data not found in API response.")
            return None

        return data
        
    except requests.exceptions.RequestException as e:
        st.error(f"Weather API Error: {e}")
        return None


# Helper function to convert day-of-year to month and day name
def doy_to_date_str(doy):
    ref = datetime.date(2025, 1, 1) + datetime.timedelta(days=doy - 1)
    return ref.strftime("%b %d")


# Sidebar / Columns layout for city input and years to average slider
col1, col2 = st.columns([3, 1])
with col1:
    city = st.text_input("City name", placeholder="Enter city name (e.g. Vienna)", key="city")
with col2:
    years = st.slider("Years of history to average", min_value=1, max_value=30, value=10, key="years")

# Create a placeholder container for the loader and results
results_placeholder = st.empty()

# Custom CSS for the premium dashboard metric cards
st.markdown("""
<style>
.metric-container {
    display: flex;
    justify-content: space-between;
    gap: 1.5rem;
    margin-top: 1.5rem;
    margin-bottom: 2rem;
    width: 100%;
}
.metric-card {
    background-color: #ffffff;
    border: 1px solid #eef2f6;
    border-radius: 12px;
    padding: 1.25rem;
    flex: 1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    min-width: 200px;
}
.metric-label {
    font-size: 0.85rem;
    color: #718096;
    margin-bottom: 0.4rem;
    font-weight: 500;
}
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #1a202c;
    margin-bottom: 0.5rem;
}
.metric-sub-green {
    display: inline-block;
    background-color: #c6f6d5;
    color: #22543d;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
}
.metric-sub-red {
    display: inline-block;
    background-color: #fed7d7;
    color: #742a2a;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

if city.strip():
    with results_placeholder.container():
        with st.spinner(f"fetching geo location for {city}..."):
            time.sleep(0.5)  # Slight delay to make the loader clearly visible
            city_data = geocode_city(city)
            
        if city_data:
            lat = city_data.get('latitude')
            lon = city_data.get('longitude')
            
            with st.spinner(f"fetching {years}-year weather archive for {city}..."):
                time.sleep(0.5)  # Slight delay for visual loader
                weather_data = get_weather(years, lat, lon)
                
            if weather_data:
                # Parse data with Pandas
                df = pd.DataFrame({
                    "date": pd.to_datetime(weather_data["daily"]["time"]),
                    "temp_max": weather_data["daily"]["temperature_2m_max"],
                    "temp_min": weather_data["daily"]["temperature_2m_min"]
                })
                
                df["month"] = df["date"].dt.month
                df["day"] = df["date"].dt.day
                
                # Collapse Feb 29 into Feb 28
                is_leap_day = (df["month"] == 2) & (df["day"] == 29)
                df.loc[is_leap_day, "day"] = 28
                
                # Group daily observations by month and day to get 365 days
                daily_stats = df.groupby(["month", "day"]).agg({
                    "temp_max": "mean",
                    "temp_min": "mean"
                }).reset_index()
                
                # Sort and set Day of Year (1..365)
                daily_stats = daily_stats.sort_values(["month", "day"]).reset_index(drop=True)
                daily_stats["doy"] = range(1, 366)
                
                # Periodic boundary padding for 7-day centered rolling mean
                padded_df = pd.concat([
                    daily_stats.tail(3),
                    daily_stats,
                    daily_stats.head(3)
                ]).reset_index(drop=True)
                
                padded_df["temp_max_smooth"] = padded_df["temp_max"].rolling(window=7, center=True).mean()
                padded_df["temp_min_smooth"] = padded_df["temp_min"].rolling(window=7, center=True).mean()
                
                # Sliced back to 365 days (no NaNs)
                smooth_stats = padded_df.iloc[3:-3].copy().reset_index(drop=True)
                
                # Determine today's day-of-year
                today = datetime.datetime.now()
                today_month = today.month
                today_day = today.day
                
                # Adjust for potential leap day reference
                check_month = today_month
                check_day = today_day
                if check_month == 2 and check_day == 29:
                    check_day = 28
                    
                ref_date = datetime.date(2025, check_month, check_day)
                today_doy = int(ref_date.strftime("%j"))
                
                # Extract Warmest Day of the Year
                warmest_idx = smooth_stats["temp_max_smooth"].idxmax()
                warmest_row = smooth_stats.loc[warmest_idx]
                warmest_date_str = doy_to_date_str(int(warmest_row["doy"]))
                warmest_temp = warmest_row["temp_max_smooth"]
                
                # Extract Coldest Day of the Year
                coldest_idx = smooth_stats["temp_min_smooth"].idxmin()
                coldest_row = smooth_stats.loc[coldest_idx]
                coldest_date_str = doy_to_date_str(int(coldest_row["doy"]))
                coldest_temp = coldest_row["temp_min_smooth"]
                
                # Extract today's typical high/low
                today_row = smooth_stats[smooth_stats["doy"] == today_doy].iloc[0]
                today_high = today_row["temp_max_smooth"]
                today_low = today_row["temp_min_smooth"]
                
                elevation = weather_data.get("elevation", 0.0)
                city_name = city_data.get('name')
                country_name = city_data.get('country')
                
                # Header
                st.markdown(f"## Climate profile for {city_name}, {country_name}")
                num_obs = len(df)
                start_year = 2025 - years + 1
                st.markdown(
                    f"<p style='color: #718096; margin-top: -15px;'>"
                    f"Averaged over {years} years ({start_year}-2025) • {num_obs:,} daily observations • smoothed with a 7-day rolling mean"
                    f"</p>", 
                    unsafe_allow_html=True
                )
                
                # Metrics Container (HTML)
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-card">
                        <div class="metric-label">Warmest day of year</div>
                        <div class="metric-value">{warmest_date_str}</div>
                        <div class="metric-sub-green">↑ {warmest_temp:.1f}°C avg high</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Coldest day of year</div>
                        <div class="metric-value">{coldest_date_str}</div>
                        <div class="metric-sub-red">↓ {coldest_temp:.1f}°C avg low</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Typical high today</div>
                        <div class="metric-value">{today_high:.1f}°C</div>
                        <div class="metric-sub-green">↑ low around {today_low:.1f}°C</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Elevation</div>
                        <div class="metric-value">{elevation:.1f} m</div>
                        <div class="metric-sub-green">↑ lat {lat:.2f}, lng {lon:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Setup custom ticks for months (approximate start of each month in non-leap year)
                tick_doys = list(range(1, 365, 30))
                tick_labels = [doy_to_date_str(d) for d in tick_doys]
                
                # Plotly Chart
                fig = go.Figure()
                
                # Add Average Low trace (first, so it acts as bottom baseline for fill)
                fig.add_trace(go.Scatter(
                    x=smooth_stats["doy"],
                    y=smooth_stats["temp_min_smooth"],
                    mode="lines",
                    name="Average Low",
                    line=dict(color="#3182ce", width=2)
                ))
                
                # Add Average High trace with fill to fill the band between them
                fig.add_trace(go.Scatter(
                    x=smooth_stats["doy"],
                    y=smooth_stats["temp_max_smooth"],
                    mode="lines",
                    name="Average High",
                    line=dict(color="#e53e3e", width=2),
                    fill="tonexty",
                    fillcolor="rgba(113, 128, 150, 0.12)"
                ))
                
                # Add vertical "Today" line
                fig.add_vline(
                    x=today_doy,
                    line_width=2,
                    line_dash="dash",
                    line_color="#dd6b20",
                    annotation_text="Today",
                    annotation_position="top",
                    annotation_font=dict(color="#dd6b20", size=12)
                )
                
                fig.update_layout(
                    title=dict(
                        text=f"Daily Climatology - {city_name}, {country_name}",
                        font=dict(size=16, color="#2d3748", family="Arial")
                    ),
                    xaxis=dict(
                        tickmode="array",
                        tickvals=tick_doys,
                        ticktext=tick_labels,
                        gridcolor="#edf2f7",
                        showline=True,
                        linecolor="#cbd5e0"
                    ),
                    yaxis=dict(
                        title="Temperature (°C)",
                        gridcolor="#edf2f7",
                        showline=True,
                        linecolor="#cbd5e0"
                    ),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=50, r=50, t=80, b=50),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Expandable map section at the bottom
                with st.expander("📍 Show location on map"):
                    map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
                    st.map(map_df, width="stretch" if hasattr(st, "map") else None)
                
            else:
                st.error("Could not load weather information.")
else:
    results_placeholder.empty()
