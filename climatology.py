import streamlit as st
import requests
import time
import pandas as pd
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


# Sidebar / Columns layout for city input and years to average slider
col1, col2 = st.columns([3, 1])
with col1:
    city = st.text_input("City:", placeholder="Enter city name (e.g. Vienna)", key="city")
with col2:
    years = st.slider("Years to average:", min_value=1, max_value=30, value=5, key="years")

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
            
            with st.spinner(f"fetching weather data for {city} over {years} years..."):
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
                monthly_stats = df.groupby("month").agg({
                    "temp_max": "mean",
                    "temp_min": "mean"
                })
                
                month_names = {
                    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
                }
                
                # Calculations
                hottest_month_num = monthly_stats["temp_max"].idxmax()
                hottest_month = month_names[hottest_month_num]
                hottest_temp = monthly_stats.loc[hottest_month_num, "temp_max"]
                
                coldest_month_num = monthly_stats["temp_min"].idxmin()
                coldest_month = month_names[coldest_month_num]
                coldest_temp = monthly_stats.loc[coldest_month_num, "temp_min"]
                
                annual_range = hottest_temp - coldest_temp
                elevation = weather_data.get("elevation", 0.0)
                
                city_name = city_data.get('name')
                country_name = city_data.get('country')
                
                # Header
                st.markdown(f"## Climate summary for {city_name}, {country_name}")
                start_year = 2025 - years + 1
                num_obs = len(df)
                st.markdown(f"<p style='color: #718096; margin-top: -15px;'>Averaged over {years} years ({start_year}-2025) • {num_obs:,} daily observations</p>", unsafe_allow_html=True)
                
                # Metrics Container (HTML)
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-card">
                        <div class="metric-label">Hottest month</div>
                        <div class="metric-value">{hottest_month}</div>
                        <div class="metric-sub-green">↑ {hottest_temp:.1f}°C avg high</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Coldest month</div>
                        <div class="metric-value">{coldest_month}</div>
                        <div class="metric-sub-red">↓ {coldest_temp:.1f}°C avg low</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Annual range</div>
                        <div class="metric-value">{annual_range:.1f}°C</div>
                        <div class="metric-sub-green">↑ peak-to-peak</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Elevation</div>
                        <div class="metric-value">{elevation:.1f} m</div>
                        <div class="metric-sub-green">↑ lat {lat:.2f}, lng {lon:.2f}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Plotly Chart
                months = [month_names[m] for m in monthly_stats.index]
                avg_highs = monthly_stats["temp_max"].tolist()
                avg_lows = monthly_stats["temp_min"].tolist()
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=months,
                    y=avg_highs,
                    mode="lines+markers",
                    name="Average High",
                    line=dict(color="#e53e3e", width=3),
                    marker=dict(size=8, color="#e53e3e")
                ))
                
                fig.add_trace(go.Scatter(
                    x=months,
                    y=avg_lows,
                    mode="lines+markers",
                    name="Average Low",
                    line=dict(color="#3182ce", width=3),
                    marker=dict(size=8, color="#3182ce")
                ))
                
                fig.update_layout(
                    title=dict(
                        text=f"Monthly Average Temperature - {city_name}, {country_name}",
                        font=dict(size=16, color="#2d3748", family="Arial")
                    ),
                    xaxis=dict(
                        title="Month",
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
                    height=450
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error("Could not load weather information.")
else:
    results_placeholder.empty()







