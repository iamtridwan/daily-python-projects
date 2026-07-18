import streamlit as st
import requests
import time
import pandas as pd
import datetime
import plotly.graph_objects as go

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

# Set page configuration for a wider layout and custom title
st.set_page_config(page_title="Climate Comparison Dashboard", layout="wide")

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
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
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


# Helper to process a single city's daily climate data
def process_city_data(city_name, years):
    city_data = geocode_city(city_name)
    if not city_data:
        return None
        
    lat = city_data.get('latitude')
    lon = city_data.get('longitude')
    weather_data = get_weather(years, lat, lon)
    if not weather_data:
        return None
        
    df = pd.DataFrame({
        "date": pd.to_datetime(weather_data["daily"]["time"]),
        "temp_max": weather_data["daily"]["temperature_2m_max"],
        "temp_min": weather_data["daily"]["temperature_2m_min"],
        "precipitation_sum": weather_data["daily"].get("precipitation_sum", [0.0] * len(weather_data["daily"]["time"]))
    })
    df["precipitation_sum"] = df["precipitation_sum"].fillna(0.0)
    
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
    
    return {
        "city_metadata": city_data,
        "weather_data": weather_data,
        "df": df,
        "smooth_stats": smooth_stats,
        "lat": lat,
        "lon": lon
    }


# Header
st.markdown("## ☀️ Climate Comparison Dashboard")
st.markdown(
    "Compare the year-round climate of any two (or three) cities on the same chart. "
    "Powered by free historical weather data from [Open-Meteo](https://open-meteo.com/)."
)

# Sidebar / Columns layout for city input and years to average slider
col1, col2, col3, col4 = st.columns([3, 3, 3, 2])
with col1:
    city1 = st.text_input("City 1", value="Vienna", key="city1")
with col2:
    city2 = st.text_input("City 2", value="Tirana", key="city2")
with col3:
    city3 = st.text_input("City 3 (optional)", placeholder="Leave blank for 2-city view", key="city3")
with col4:
    years = st.slider("Years", min_value=1, max_value=30, value=10, key="years")

# Custom CSS for the bottom city info cards
st.markdown("""
<style>
.city-card-container {
    display: flex;
    justify-content: space-between;
    gap: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 2rem;
    width: 100%;
    flex-wrap: wrap;
}
.city-card {
    border-radius: 12px;
    padding: 1.5rem;
    flex: 1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    min-width: 280px;
    background-color: #ffffff;
}
.city-card-vienna {
    border: 2px solid #805ad5;
}
.city-card-tirana {
    border: 2px solid #319795;
}
.city-card-city3 {
    border: 2px solid #dd6b20;
}
.city-card-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
}
.city-card-vienna .city-card-title {
    color: #805ad5;
}
.city-card-tirana .city-card-title {
    color: #319795;
}
.city-card-city3 .city-card-title {
    color: #dd6b20;
}
.city-card-stat {
    font-size: 0.9rem;
    color: #4a5568;
    margin-bottom: 0.4rem;
}
.city-card-stat strong {
    color: #1a202c;
}
</style>
""", unsafe_allow_html=True)

# Build a list of active inputs
input_cities = [c.strip() for c in [city1, city2, city3] if c.strip()]

if len(input_cities) >= 2:
    processed_cities = []
    
    # Process each city with loaders
    results_placeholder = st.empty()
    with results_placeholder.container():
        for c_name in input_cities:
            with st.spinner(f"Loading and processing data for {c_name}..."):
                time.sleep(0.3)  # Short delay for visual loader feedback
                res = process_city_data(c_name, years)
                if res:
                    processed_cities.append(res)
    results_placeholder.empty()
    
    if len(processed_cities) >= 2:
        month_names_long = {
            1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
        }
        start_year = 2025 - years + 1
        num_obs_total = sum(len(c["df"]) for c in processed_cities)
        st.markdown(
            f"<p style='color: #718096; margin-top: -15px; font-size: 0.9rem;'>"
            f"Comparing {len(processed_cities)} cities • averaged over {years} years ({start_year}-2025) • "
            f"smoothed with a 7-day rolling mean"
            f"</p>", 
            unsafe_allow_html=True
        )
        
        # Plotly Setup
        fig = go.Figure()
        
        # Color schemes mapping
        themes = [
            # City 1: Purple
            {"high": "#805ad5", "low": "#b794f4", "fill": "rgba(128, 90, 213, 0.08)"},
            # City 2: Teal/Green
            {"high": "#2f855a", "low": "#48bb78", "fill": "rgba(47, 133, 90, 0.08)"},
            # City 3: Orange
            {"high": "#dd6b20", "low": "#fbd38d", "fill": "rgba(221, 107, 32, 0.08)"}
        ]
        
        for idx, city_res in enumerate(processed_cities):
            city_name = city_res["city_metadata"]["name"]
            smooth_stats = city_res["smooth_stats"]
            color_high = themes[idx]["high"]
            color_low = themes[idx]["low"]
            fill_color = themes[idx]["fill"]
            
            # Low Trace
            fig.add_trace(go.Scatter(
                x=smooth_stats["doy"],
                y=smooth_stats["temp_min_smooth"],
                mode="lines",
                name=f"{city_name} - Low",
                line=dict(color=color_low, width=1.5),
                legendgroup=city_name
            ))
            
            # High Trace with fill
            fig.add_trace(go.Scatter(
                x=smooth_stats["doy"],
                y=smooth_stats["temp_max_smooth"],
                mode="lines",
                name=f"{city_name} - High",
                line=dict(color=color_high, width=2),
                fill="tonexty",
                fillcolor=fill_color,
                legendgroup=city_name
            ))
            
            # Find peak to place the floating label
            peak_idx = smooth_stats["temp_max_smooth"].idxmax()
            peak_row = smooth_stats.loc[peak_idx]
            peak_doy = peak_row["doy"]
            peak_temp = peak_row["temp_max_smooth"]
            
            # Add text label above peak
            fig.add_trace(go.Scatter(
                x=[peak_doy],
                y=[peak_temp + 1.2],
                mode="text",
                text=[city_name],
                textfont=dict(color=color_high, size=12, family="Arial Black"),
                showlegend=False
            ))
            
        # Determine today's day-of-year
        today = datetime.datetime.now()
        today_month = today.month
        today_day = today.day
        
        check_month = today_month
        check_day = today_day
        if check_month == 2 and check_day == 29:
            check_day = 28
            
        ref_date = datetime.date(2025, check_month, check_day)
        today_doy = int(ref_date.strftime("%j"))
        
        # Add vertical "Today" line
        fig.add_vline(
            x=today_doy,
            line_width=2,
            line_dash="dash",
            line_color="#e53e3e",
            annotation_text="Today",
            annotation_position="top",
            annotation_font=dict(color="#e53e3e", size=12)
        )
        
        # Setup custom ticks for months (approximate start of each month in non-leap year)
        tick_doys = list(range(1, 365, 30))
        tick_labels = [doy_to_date_str(d) for d in tick_doys]
        
        fig.update_layout(
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
            height=550
        )
        
        st.markdown("### Annual Climate Comparison")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Heatmap Section ---
        st.markdown("### Climate Distribution Heatmap")
        heatmap_metric = st.selectbox(
            "Select Heatmap Metric:", 
            options=["Average High Temperature (°C)", "Average Precipitation / Rainfall (mm)"], 
            key="heatmap_metric"
        )
        
        # Build Heatmap Data Matrix
        months_names_short = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        y_cities = [c["city_metadata"]["name"] for c in processed_cities]
        z_values = []
        
        for city_res in processed_cities:
            city_smooth = city_res["smooth_stats"]
            if "Temperature" in heatmap_metric:
                # Group by month and calculate average temperature
                monthly_val = city_smooth.groupby("month")["temp_max_smooth"].mean().tolist()
            else:
                # Group by year and month, sum precipitation, then group by month and average
                df_raw = city_res["df"]
                df_raw["year"] = df_raw["date"].dt.year
                monthly_totals = df_raw.groupby(["year", "month"])["precipitation_sum"].sum().reset_index()
                monthly_val = monthly_totals.groupby("month")["precipitation_sum"].mean().tolist()
            z_values.append(monthly_val)
            
        colorscale = "Blues" if "Precipitation" in heatmap_metric else "YlOrRd"
        colorbar_title = "mm" if "Precipitation" in heatmap_metric else "°C"
        
        fig_hm = go.Figure(data=go.Heatmap(
            z=z_values,
            x=months_names_short,
            y=y_cities,
            colorscale=colorscale,
            colorbar=dict(title=colorbar_title),
            hoverongaps=False,
            text=[[f"{val:.1f}" for val in row] for row in z_values],
            texttemplate="%{text}",
            textfont={"size": 11, "family": "Arial"}
        ))
        
        fig_hm.update_layout(
            xaxis=dict(title="Month", showgrid=False),
            yaxis=dict(title="City", showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=80, r=50, t=20, b=50),
            height=150 + (60 * len(processed_cities))
        )
        
        st.plotly_chart(fig_hm, use_container_width=True)
        
        # --- Prose Insights Section (Comparing City 1 and City 2) ---
        c1_res = processed_cities[0]
        c2_res = processed_cities[1]
        c1_name = c1_res["city_metadata"]["name"]
        c2_name = c2_res["city_metadata"]["name"]
        c1_smooth = c1_res["smooth_stats"]
        c2_smooth = c2_res["smooth_stats"]
        
        # Today's Comparison
        t1_today = c1_smooth.loc[c1_smooth["doy"] == today_doy, "temp_max_smooth"].values[0]
        t2_today = c2_smooth.loc[c2_smooth["doy"] == today_doy, "temp_max_smooth"].values[0]
        diff_today = abs(t1_today - t2_today)
        warmer_today = c1_name if t1_today > t2_today else c2_name
        colder_today = c2_name if t1_today > t2_today else c1_name
        temp_warm_today = t1_today if t1_today > t2_today else t2_today
        temp_cold_today = t2_today if t1_today > t2_today else t1_today
        # Compute monthly average highs for both cities
        monthly_highs_c1 = c1_smooth.groupby("month")["temp_max_smooth"].mean()
        monthly_highs_c2 = c2_smooth.groupby("month")["temp_max_smooth"].mean()

        # Calculate monthly differences
        monthly_diffs = monthly_highs_c1 - monthly_highs_c2
        abs_monthly_diffs = monthly_diffs.abs()



        # Find the month with the maximum average gap
        max_gap_month_num = abs_monthly_diffs.idxmax()
        max_gap_month_name = month_names_long[max_gap_month_num]
        max_gap_val = abs_monthly_diffs.loc[max_gap_month_num]
        warmer_max_gap_city = c1_name if monthly_diffs.loc[max_gap_month_num] > 0 else c2_name
        temp_c1_max_gap = monthly_highs_c1.loc[max_gap_month_num]
        temp_c2_max_gap = monthly_highs_c2.loc[max_gap_month_num]

        # Find the month with the minimum average gap
        min_gap_month_num = abs_monthly_diffs.idxmin()
        min_gap_month_name = month_names_long[min_gap_month_num]
        min_gap_val = abs_monthly_diffs.loc[min_gap_month_num]
        warmer_min_gap_city = c1_name if monthly_diffs.loc[min_gap_month_num] > 0 else c2_name
        temp_c1_min_gap = monthly_highs_c1.loc[min_gap_month_num]
        temp_c2_min_gap = monthly_highs_c2.loc[min_gap_month_num]
        
        # Biggest Gap
        diff_series = c1_smooth["temp_max_smooth"] - c2_smooth["temp_max_smooth"]
        abs_diff_series = diff_series.abs()
        max_diff_idx = abs_diff_series.idxmax()
        max_diff_val = abs_diff_series.loc[max_diff_idx]
        gap_row = c1_smooth.loc[max_diff_idx]
        gap_date_str = doy_to_date_str(int(gap_row["doy"]))
        warmer_gap_city = c1_name if diff_series.loc[max_diff_idx] > 0 else c2_name
        
        # Crossing logic
        sign_changes = (diff_series > 0).diff().dropna()
        curves_cross = sign_changes.any()
        
        if not curves_cross:
            if (diff_series > 0).all():
                warmer_always = c1_name
                colder_always = c2_name
            else:
                warmer_always = c2_name
                colder_always = c1_name
            crossing_insight = (
                f"📌 <strong>{warmer_always} is warmer than {colder_always} every single day of the year on average</strong> "
                f"— their curves never cross."
            )
        else:
            cross_idx = sign_changes[sign_changes].index[0]
            cross_month_num = c1_smooth.loc[cross_idx, "month"]
            cross_month_name = month_names_long[cross_month_num]
            crossing_insight = f"📌 Their temperature curves cross during the year, for example in <strong>{cross_month_name}</strong>."
            
        today_date_str = today.strftime("%b %d")
        
        st.markdown("### 🔍 Insights")
        st.markdown(f"""
        📍 **Right now ({today_date_str})**, **{warmer_today} is typically warmer by {diff_today:.1f}°C** ({colder_today}: {temp_cold_today:.1f}°C vs {warmer_today}: {temp_warm_today:.1f}°C, average highs).
        
        ☀️ **The biggest average monthly gap** is in **{max_gap_month_name}**, when **{warmer_max_gap_city}** is warmer by **{max_gap_val:.1f}°C** ({c1_name}: {temp_c1_max_gap:.1f}°C, {c2_name}: {temp_c2_max_gap:.1f}°C).
        
        ❄️ **The closest monthly averages** occur in **{min_gap_month_name}**, when the gap is only **{min_gap_val:.1f}°C** ({c1_name}: {temp_c1_min_gap:.1f}°C, {c2_name}: {temp_c2_min_gap:.1f}°C).
        
        📈 The **biggest gap** of the year is around **{gap_date_str}**, when **{warmer_gap_city} is {max_diff_val:.1f}°C warmer**.
        
        {crossing_insight}
        """, unsafe_allow_html=True)
        
        # --- Monthly comparison table showing exact numbers ---
        st.markdown("### Monthly average high temperatures (°C)")
        
        month_labels_short = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
        }
        
        monthly_rows = []
        for m in range(1, 13):
            row_data = {"Month": month_labels_short[m]}
            for city_res in processed_cities:
                c_name = city_res["city_metadata"]["name"]
                c_smooth = city_res["smooth_stats"]
                avg_high = c_smooth[c_smooth["month"] == m]["temp_max_smooth"].mean()
                row_data[c_name] = round(avg_high, 1)
            monthly_rows.append(row_data)
            
        df_monthly = pd.DataFrame(monthly_rows).set_index("Month")
        st.table(df_monthly)
        
        # --- Bottom City Info Cards Styled in Each City's Color ---
        st.markdown("### City Climate Profiles")
        
        card_styles = ["city-card-vienna", "city-card-tirana", "city-card-city3"]
        
        cards_html = '<div class="city-card-container">'
        
        for idx, city_res in enumerate(processed_cities):
            c_meta = city_res["city_metadata"]
            c_name = c_meta["name"]
            c_country = c_meta.get("country", "")
            c_smooth = city_res["smooth_stats"]
            lat_val = city_res["lat"]
            lon_val = city_res["lon"]
            elevation_val = city_res["weather_data"].get("elevation", 0.0)
            
            # Hottest day
            w_idx = c_smooth["temp_max_smooth"].idxmax()
            w_row = c_smooth.loc[w_idx]
            w_date = doy_to_date_str(int(w_row["doy"]))
            w_temp = w_row["temp_max_smooth"]
            
            # Coldest day
            c_idx = c_smooth["temp_min_smooth"].idxmin()
            c_row = c_smooth.loc[c_idx]
            c_date = doy_to_date_str(int(c_row["doy"]))
            c_temp = c_row["temp_min_smooth"]
            
            # Wettest month calculation
            df_raw = city_res["df"]
            df_raw["year"] = df_raw["date"].dt.year
            monthly_totals = df_raw.groupby(["year", "month"])["precipitation_sum"].sum().reset_index()
            monthly_avg_precip = monthly_totals.groupby("month")["precipitation_sum"].mean()
            
            wettest_month_num = monthly_avg_precip.idxmax()
            wettest_month_name = month_names_long[wettest_month_num]
            wettest_precip_val = monthly_avg_precip.loc[wettest_month_num]
            
            range_val = w_temp - c_temp
            card_class = card_styles[idx]
            
            cards_html += f'<div class="city-card {card_class}">'
            cards_html += f'<div class="city-card-title">{c_name}, {c_country}</div>'
            cards_html += f'<div class="city-card-stat"><strong>Latitude:</strong> {lat_val:.2f}° | <strong>Longitude:</strong> {lon_val:.2f}°</div>'
            cards_html += f'<div class="city-card-stat"><strong>Elevation:</strong> {elevation_val:.1f} m</div>'
            cards_html += f'<div class="city-card-stat"><strong>Warmest Day:</strong> {w_date} ({w_temp:.1f}°C avg high)</div>'
            cards_html += f'<div class="city-card-stat"><strong>Coldest Day:</strong> {c_date} ({c_temp:.1f}°C avg low)</div>'
            cards_html += f'<div class="city-card-stat"><strong>Annual Range:</strong> {range_val:.1f}°C</div>'
            cards_html += f'<div class="city-card-stat"><strong>Wettest Month:</strong> {wettest_month_name} ({wettest_precip_val:.1f} mm avg)</div>'
            cards_html += '</div>'
            
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)
        
    else:
        st.warning("Could not process climate data for the entered cities. Please check the spelling.")
else:
    st.info("Please enter at least two cities to view the climate comparison.")
