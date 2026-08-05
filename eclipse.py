"""
Visualizing the 2026 Eclipse with Python: Day 1 - Command-line eclipse info tool
Date of eclipse: August 12, 2026

Calculates solar eclipse contact times (C1, C2, Max, C3, C4), Sun coverage percentage,
eclipse magnitude, and totality duration using Skyfield astronomical ephemerides.
"""

# ==============================================================================
# SECTION 1: IMPORTS & INITIALIZATION
# ==============================================================================
import datetime
import math
import sys
from zoneinfo import ZoneInfo

from geopy.geocoders import Nominatim
import numpy as np
from rich.console import Console
from rich import box
from rich.table import Table
import skyfield_data
from skyfield.api import Loader, wgs84
from timezonefinder import TimezoneFinder

# Initialize Skyfield loader with skyfield_data offline path
load = Loader(skyfield_data.get_skyfield_data_path())
ts = load.timescale()
eph = load('de421.bsp')

sun = eph['sun']
moon = eph['moon']
earth = eph['earth']

# Rich console for terminal UI output
console = Console()

# Timezone finder engine
tf = TimezoneFinder()

# Physical constants for celestial radii (in km)
R_SUN_KM = 696340.0
R_MOON_KM = 1737.4

# ==============================================================================
# SECTION 2: CONSTANTS & PRESET PATH CITIES
# ==============================================================================
PRESET_CITIES = [
    {"name": "Reykjavik",  "country": "Iceland",  "lat": 64.1466, "lon": -21.9426},
    {"name": "Isafjordur", "country": "Iceland",  "lat": 66.0749, "lon": -23.1241},
    {"name": "Bilbao",     "country": "Spain",    "lat": 43.2630, "lon": -2.9350},
    {"name": "Santander",  "country": "Spain",    "lat": 43.4623, "lon": -3.8099},
    {"name": "Burgos",     "country": "Spain",    "lat": 42.3440, "lon": -3.6969},
    {"name": "Leon",       "country": "Spain",    "lat": 42.5987, "lon": -5.5671},
    {"name": "Valladolid", "country": "Spain",    "lat": 41.6523, "lon": -4.7245},
    {"name": "Zaragoza",   "country": "Spain",    "lat": 41.6488, "lon": -0.8891},
    {"name": "Palma",      "country": "Spain",    "lat": 39.5696, "lon": 2.6502},
    {"name": "Barcelona",  "country": "Spain",    "lat": 41.3851, "lon": 2.1734},
    {"name": "Madrid",     "country": "Spain",    "lat": 40.4168, "lon": -3.7038},
    {"name": "Lisbon",     "country": "Portugal", "lat": 38.7223, "lon": -9.1393},
]

# ==============================================================================
# SECTION 3: ASTRONOMY MATHEMATICS & GEOMETRY
# ==============================================================================
def get_sun_moon_geometry_array(lat: float, lon: float, times_utc: list[datetime.datetime]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized calculation of separation and radii across an array of UTC datetimes."""
    t_arr = ts.from_datetimes(times_utc)
    topos = earth + wgs84.latlon(lat, lon)

    ast_sun = topos.at(t_arr).observe(sun).apparent()
    ast_moon = topos.at(t_arr).observe(moon).apparent()

    sep_rads = ast_sun.separation_from(ast_moon).radians
    d_sun = ast_sun.distance().km
    d_moon = ast_moon.distance().km

    r_sun_rads = np.arcsin(R_SUN_KM / d_sun)
    r_moon_rads = np.arcsin(R_MOON_KM / d_moon)

    return sep_rads, r_sun_rads, r_moon_rads


def calculate_coverage_and_magnitude_vec(sep: np.ndarray, r_sun: np.ndarray, r_moon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized calculation of solar disk coverage percentage and eclipse magnitude."""
    magnitude = (r_sun + r_moon - sep) / (2.0 * r_sun)
    magnitude = np.maximum(0.0, magnitude)

    coverage = np.zeros_like(sep)

    no_overlap = sep >= (r_sun + r_moon)
    total_or_annular = sep <= np.abs(r_sun - r_moon)
    partial = ~no_overlap & ~total_or_annular

    if np.any(total_or_annular):
        tot_mask = total_or_annular & (r_moon >= r_sun)
        ann_mask = total_or_annular & (r_moon < r_sun)
        coverage[tot_mask] = 100.0
        coverage[ann_mask] = (r_moon[ann_mask] / r_sun[ann_mask]) ** 2 * 100.0

    if np.any(partial):
        d = sep[partial]
        r1 = r_sun[partial]
        r2 = r_moon[partial]

        arg1 = np.clip((d**2 + r1**2 - r2**2) / (2 * d * r1), -1.0, 1.0)
        arg2 = np.clip((d**2 + r2**2 - r1**2) / (2 * d * r2), -1.0, 1.0)

        part1 = r1**2 * np.arccos(arg1)
        part2 = r2**2 * np.arccos(arg2)
        part3 = 0.5 * np.sqrt(np.maximum(0.0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))

        intersection_area = part1 + part2 - part3
        sun_area = np.pi * r1**2
        coverage[partial] = (intersection_area / sun_area) * 100.0

    return np.clip(coverage, 0.0, 100.0), magnitude


def compute_eclipse_details(lat: float, lon: float) -> dict:
    """
    Scans the August 12, 2026 eclipse window (14:00 to 21:30 UTC) to find contact times
    (C1, C2, Max, C3, C4), max coverage, magnitude, and totality duration.
    """
    start_window = datetime.datetime(2026, 8, 12, 14, 0, tzinfo=datetime.timezone.utc)
    end_window = datetime.datetime(2026, 8, 12, 21, 30, tzinfo=datetime.timezone.utc)

    # 30-second grid scan across search window (901 steps)
    step_seconds = 30
    num_steps = int((end_window - start_window).total_seconds() / step_seconds)
    times = [start_window + datetime.timedelta(seconds=i * step_seconds) for i in range(num_steps + 1)]

    seps, r_suns, r_moons = get_sun_moon_geometry_array(lat, lon, times)
    coverages, magnitudes = calculate_coverage_and_magnitude_vec(seps, r_suns, r_moons)

    max_idx = int(np.argmax(coverages))
    max_cov = float(coverages[max_idx])

    if max_cov < 0.0001:
        return {
            "visible": False,
            "max_coverage": 0.0,
            "magnitude": 0.0,
            "max_time_utc": None,
            "start_time_utc": None,
            "end_time_utc": None,
            "totality_start_utc": None,
            "totality_end_utc": None,
            "totality_seconds": 0,
            "is_total": False,
        }

    # Refine max eclipse time to 1-second accuracy around max_idx
    best_time = times[max_idx]
    fine_max_times = [best_time + datetime.timedelta(seconds=off) for off in range(-30, 31)]
    fm_seps, fm_rs, fm_rm = get_sun_moon_geometry_array(lat, lon, fine_max_times)
    fm_covs, fm_mags = calculate_coverage_and_magnitude_vec(fm_seps, fm_rs, fm_rm)

    f_max_idx = int(np.argmin(fm_seps))
    refined_max_time = fine_max_times[f_max_idx]
    max_cov = float(fm_covs[f_max_idx])
    best_mag = float(fm_mags[f_max_idx])
    best_r_sun = float(fm_rs[f_max_idx])
    best_r_moon = float(fm_rm[f_max_idx])
    min_sep = float(fm_seps[f_max_idx])

    # C1 (Eclipse start: sep crosses r_sun + r_moon going down)
    c1_time = None
    partial_mask = seps < (r_suns + r_moons)
    c1_indices = np.where(partial_mask[:max_idx])[0]
    if len(c1_indices) > 0:
        first_p_idx = c1_indices[0]
        t_start = times[max(0, first_p_idx - 1)]
        c1_fine_times = [t_start + datetime.timedelta(seconds=s) for s in range(61)]
        c1_seps, c1_rs, c1_rm = get_sun_moon_geometry_array(lat, lon, c1_fine_times)
        c1_mask = c1_seps < (c1_rs + c1_rm)
        if np.any(c1_mask):
            c1_idx = int(np.where(c1_mask)[0][0])
            c1_time = c1_fine_times[c1_idx]

    # C4 (Eclipse end: sep crosses r_sun + r_moon going up)
    c4_time = None
    c4_indices = np.where(partial_mask[max_idx:])[0]
    if len(c4_indices) > 0:
        last_p_idx = max_idx + c4_indices[-1]
        t_end = times[min(len(times) - 1, last_p_idx)]
        c4_fine_times = [t_end + datetime.timedelta(seconds=s) for s in range(61)]
        c4_seps, c4_rs, c4_rm = get_sun_moon_geometry_array(lat, lon, c4_fine_times)
        c4_mask = c4_seps >= (c4_rs + c4_rm)
        if np.any(c4_mask):
            c4_idx = int(np.where(c4_mask)[0][0])
            c4_time = c4_fine_times[c4_idx]

    # Totality check
    is_total = (best_r_moon > best_r_sun) and (min_sep <= (best_r_moon - best_r_sun))
    c2_time = None
    c3_time = None
    totality_seconds = 0

    if is_total:
        tot_mask = seps <= (r_moons - r_suns)
        tot_indices = np.where(tot_mask)[0]

        # C2 (Totality start)
        if len(tot_indices) > 0:
            first_t_idx = tot_indices[0]
            t_c2_start = times[max(0, first_t_idx - 1)]
            c2_fine_times = [t_c2_start + datetime.timedelta(seconds=s) for s in range(61)]
            c2_seps, c2_rs, c2_rm = get_sun_moon_geometry_array(lat, lon, c2_fine_times)
            c2_mask_fine = c2_seps <= (c2_rm - c2_rs)
            if np.any(c2_mask_fine):
                c2_idx = int(np.where(c2_mask_fine)[0][0])
                c2_time = c2_fine_times[c2_idx]

            # C3 (Totality end)
            last_t_idx = tot_indices[-1]
            t_c3_start = times[last_t_idx]
            c3_fine_times = [t_c3_start + datetime.timedelta(seconds=s) for s in range(61)]
            c3_seps, c3_rs, c3_rm = get_sun_moon_geometry_array(lat, lon, c3_fine_times)
            c3_mask_fine = c3_seps > (c3_rm - c3_rs)
            if np.any(c3_mask_fine):
                c3_idx = int(np.where(c3_mask_fine)[0][0])
                c3_time = c3_fine_times[c3_idx]
            else:
                c3_time = c3_fine_times[-1]

        if c2_time and c3_time and c3_time > c2_time:
            totality_seconds = int(round((c3_time - c2_time).total_seconds()))
        else:
            is_total = False

    return {
        "visible": True,
        "max_coverage": max_cov,
        "magnitude": best_mag,
        "max_time_utc": refined_max_time,
        "start_time_utc": c1_time,
        "end_time_utc": c4_time,
        "totality_start_utc": c2_time,
        "totality_end_utc": c3_time,
        "totality_seconds": totality_seconds,
        "is_total": is_total,
    }

# ==============================================================================
# SECTION 4: GEOCODING & TIMEZONE LOOKUP
# ==============================================================================
def resolve_location(query: str) -> tuple[str, float, float, ZoneInfo]:
    """
    Parses a location query string (either coordinates 'lat, lon' or city name).
    Returns (display_name, lat, lon, ZoneInfo timezone).
    """
    query = query.strip()

    # Coordinates query e.g. "43.26, -2.94"
    if "," in query:
        parts = query.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                tz_name = tf.timezone_at(lat=lat, lng=lon) or "UTC"
                geolocator = Nominatim(user_agent="eclipse_2026_cli_tool")
                display_name = f"{lat:.3f}, {lon:.3f}"
                try:
                    rev = geolocator.reverse((lat, lon), language="en")
                    if rev and rev.address:
                        display_name = rev.address
                except Exception:
                    pass
                return display_name, lat, lon, ZoneInfo(tz_name)
            except ValueError:
                pass

    # City name geocoding using Nominatim
    geolocator = Nominatim(user_agent="eclipse_2026_cli_tool")
    location = geolocator.geocode(query, language="en")
    if not location:
        console.print(f"[red]Error: Could not find location for '{query}'.[/red]\n")
        sys.exit(1)

    lat = location.latitude
    lon = location.longitude
    tz_name = tf.timezone_at(lat=lat, lng=lon) or "UTC"
    display_name = location.address

    return display_name, lat, lon, ZoneInfo(tz_name)

# ==============================================================================
# SECTION 5: RICH TERMINAL UI & DISPLAY FORMATTING
# ==============================================================================
def format_duration(seconds: int) -> str:
    """Formats seconds into readable string (e.g. '1m 45s' or '35s')."""
    if seconds <= 0:
        return "0s"
    m = seconds // 60
    s = seconds % 60
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def format_local_time(dt_utc: datetime.datetime, tz: ZoneInfo) -> str:
    """Converts UTC datetime to local timezone string (e.g. '20:27 CEST', '17:48 GMT')."""
    if not dt_utc:
        return "N/A"
    dt_local = dt_utc.astimezone(tz)
    tz_abbr = dt_local.strftime("%Z")
    return f"{dt_local.strftime('%H:%M')} {tz_abbr}"


def format_full_time(dt_utc: datetime.datetime, tz: ZoneInfo) -> tuple[str, str]:
    """Formats full HH:MM:SS local and UT times for detailed report."""
    if not dt_utc:
        return "N/A", "N/A"
    dt_local = dt_utc.astimezone(tz)
    tz_abbr = dt_local.strftime("%Z")
    local_str = f"{dt_local.strftime('%H:%M:%S')} {tz_abbr}"
    ut_str = f"({dt_utc.strftime('%H:%M:%S')} UT)"
    return local_str, ut_str


def print_header():
    """Prints top title header matching Image 1 & Image 2."""
    console.print("[bold gold3]# 2026 August 12 Total Solar Eclipse[/bold gold3]")
    console.print("[dim]First mainland-Europe totality since 1999. Path: Greenland -> Iceland -> N Spain -> Balearic Sea.[/dim]\n")


def print_summary_table():
    """Renders colored summary table for major preset path cities (Image 1)."""
    print_header()
    console.print("[dim]No location given. Showing summary for cities in the path.[/dim]")
    console.print('[dim]Tip: `python eclipse.py "Palma de Mallorca"` for one city, or `python eclipse.py "43.26, -2.94"` for coords.[/dim]\n')

    console.print("                  [bold gold3]Cities along the eclipse path[/bold gold3]")

    # Create Rich table with box.SQUARE matching image 1
    table = Table(
        box=box.SQUARE,
        show_header=True,
        header_style="bold default",
        padding=(0, 1)
    )

    table.add_column("City", style="cyan", justify="left")
    table.add_column("Country", style="dim", justify="left")
    table.add_column("Max coverage", justify="right")
    table.add_column("Max time (local)", justify="left")
    table.add_column("Totality?", justify="left")

    for city in PRESET_CITIES:
        tz_name = tf.timezone_at(lat=city["lat"], lng=city["lon"]) or "UTC"
        tz = ZoneInfo(tz_name)

        details = compute_eclipse_details(city["lat"], city["lon"])
        max_cov = details["max_coverage"]
        max_time_str = format_local_time(details["max_time_utc"], tz)

        # Coverage % styling
        if max_cov >= 99.99:
            cov_str = f"[bold green]{max_cov:.2f}%[/bold green]"
        elif max_cov >= 99.0:
            cov_str = f"[olive]{max_cov:.2f}%[/olive]"
        else:
            cov_str = f"[yellow]{max_cov:.2f}%[/yellow]"

        # Totality column styling
        if details["is_total"]:
            totality_str = f"[bold green]{format_duration(details['totality_seconds'])}[/bold green]"
        else:
            totality_str = "[dim]partial[/dim]"

        time_str_styled = f"[bold default]{max_time_str}[/bold default]"

        table.add_row(
            city["name"],
            city["country"],
            cov_str,
            time_str_styled,
            totality_str
        )

    console.print(table)


def print_detailed_report(query: str):
    """Renders detailed eclipse report for a specific location query (Image 2)."""
    print_header()
    console.print(f"[dim]Looking up '{query}'...[/dim]\n")

    display_name, lat, lon, tz = resolve_location(query)
    details = compute_eclipse_details(lat, lon)

    console.print(f"[bold cyan]{display_name}[/bold cyan]")
    console.print(f"[cyan]{lat:.3f}, {lon:.3f}[/cyan]")
    console.print("[dim]------------------------------------------------------------[/dim]")

    if not details["visible"]:
        console.print("[yellow]No eclipse visible from this location on August 12, 2026.[/yellow]")
        return

    start_local, start_ut = format_full_time(details["start_time_utc"], tz)
    max_local, max_ut   = format_full_time(details["max_time_utc"], tz)
    end_local, end_ut     = format_full_time(details["end_time_utc"], tz)

    cov_val = details["max_coverage"]
    mag_val = details["magnitude"]

    cov_str = f"[bold green]{cov_val:.2f}%[/bold green]"
    mag_str = f"[cyan](magnitude {mag_val:.3f})[/cyan]"

    if details["is_total"]:
        tot_duration = format_duration(details["totality_seconds"])
        totality_str = f"[bold green]Yes ({tot_duration})[/bold green]"
    else:
        totality_str = "[dim]No (partial only)[/dim]"

    console.print(f"Eclipse start:    [bold green]{start_local:<12}[/bold green] [dim]{start_ut}[/dim]")
    console.print(f"Maximum eclipse:  [bold green]{max_local:<12}[/bold green] [dim]{max_ut}[/dim]")
    console.print(f"Eclipse end:      [bold green]{end_local:<12}[/bold green] [dim]{end_ut}[/dim]")
    console.print(f"Sun coverage:     {cov_str}  {mag_str}")
    console.print(f"Path of totality: {totality_str}")

# ==============================================================================
# SECTION 6: CLI ENTRY POINT
# ==============================================================================
def main():
    if len(sys.argv) == 1:
        print_summary_table()
    else:
        location_arg = " ".join(sys.argv[1:])
        print_detailed_report(location_arg)


if __name__ == "__main__":
    main()
