import pandas as pd
import os
import importlib.util
from functools import lru_cache
from pathlib import Path
from datetime import timedelta
from time import perf_counter
from config import TCI_START_DATE, TCI_END_DATE


def _load_local_tci_function():
    """Load calculate_tci_from_weather_data from local tci.py reliably."""
    tci_path = Path(__file__).with_name("tci.py")
    spec = importlib.util.spec_from_file_location("knmi_local_tci", tci_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module spec from {tci_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    try:
        return module.calculate_tci_from_weather_data
    except AttributeError as exc:
        raise ImportError(
            f"Function calculate_tci_from_weather_data not found in {tci_path}"
        ) from exc


calculate_tci_from_weather_data = _load_local_tci_function()

# Configuration
DATA_DIR = r'd:\temp'
OUTPUT_FILE = os.path.join(DATA_DIR, 'tci.txt')

# Load data files
dist_municipality_station = pd.read_csv(os.path.join(DATA_DIR, 'dist_municipality_station.txt'))
station_data = pd.read_csv(os.path.join(DATA_DIR, 'station_data.txt'))
monthly_precip = pd.read_csv(os.path.join(DATA_DIR, 'montly_percep_station.txt'))

station_data['YYYYMMDD'] = station_data['YYYYMMDD'].astype(str).str.zfill(8)

WEATHER_COLUMNS = ('TX', 'TG', 'RH', 'UG', 'SQ', 'FG')
WEATHER_COLUMN_INDEX = {column: idx for idx, column in enumerate(WEATHER_COLUMNS)}


def _parse_station_list(station_value):
    return [int(station_id.strip()) for station_id in str(station_value).split(':') if station_id.strip()]


# Precompute municipality -> ordered station list once.
MUNICIPALITY_STATION_MAP = {
    row.cbs_code: _parse_station_list(row.station_id)
    for row in dist_municipality_station.itertuples(index=False)
}

# Precompute fast (station, date) -> weather tuple lookup once.
station_data_lookup = {
    (int(row.STN), row.YYYYMMDD): tuple(row[2:])
    for row in station_data[['STN', 'YYYYMMDD', *WEATHER_COLUMNS]].itertuples(index=False)
}

# Precompute fast (station, year_month) -> monthly precipitation lookup once.
monthly_precip_lookup = {
    (int(row.STN), int(row.Year_Month)): row.Monthly_Precipitation
    for row in monthly_precip[['STN', 'Year_Month', 'Monthly_Precipitation']].itertuples(index=False)
}


@lru_cache(maxsize=None)
def _get_station_value_cached(cbs_code, column, yyyymmdd):
    stations = MUNICIPALITY_STATION_MAP.get(cbs_code, [])
    if not stations:
        return None

    column_idx = WEATHER_COLUMN_INDEX.get(column)
    if column_idx is None:
        return None

    for station_id in stations:
        weather_values = station_data_lookup.get((station_id, yyyymmdd))
        if weather_values is None:
            continue

        value = weather_values[column_idx]
        if pd.notna(value):
            return value

    return None

def get_station_value(cbs_code, column, station_data, yyyymmdd):
    """Get value from closest available station for a given municipality and date."""
    _ = station_data  # Kept for signature compatibility.
    return _get_station_value_cached(cbs_code, column, yyyymmdd)

def get_monthly_precipitation(cbs_code, year, month, monthly_precip):
    """Get monthly precipitation from closest available station."""
    _ = monthly_precip  # Kept for signature compatibility.
    station_list = MUNICIPALITY_STATION_MAP.get(cbs_code, [])
    if not station_list:
        return None

    year_month = int(f"{year:04d}{month:02d}")

    for station_id in station_list:
        value = monthly_precip_lookup.get((station_id, year_month))
        if pd.notna(value):
            return value
    
    return None

# Generate results
results = []
start_date = TCI_START_DATE
end_date = TCI_END_DATE
current_date = start_date

municipalities = dist_municipality_station['cbs_code'].unique()

print(f"Calculating TCI from {start_date.date()} to {end_date.date()}...")
while current_date <= end_date:
    date_start_time = perf_counter()
    year = current_date.year
    month = current_date.month
    date_str = current_date.strftime('%Y%m%d')
    print(f"Processing date: {current_date.date()}")
    for cbs_code in municipalities:
        # Retrieve weather variables
        t_max = 0.1 * get_station_value(cbs_code, 'TX', station_data, date_str) # 0.1 unit
        t_mean = 0.1 * get_station_value(cbs_code, 'TG', station_data, date_str) # 0.1 unit
        rh_mean = 0.1 * get_station_value(cbs_code, 'RH', station_data, date_str) # 0.1 unit
        avg_humidity = get_station_value(cbs_code, 'UG', station_data, date_str)
        daily_sun = 0.1 * get_station_value(cbs_code, 'SQ', station_data, date_str) # 0.1 unit
        wind_speed = 0.1 * get_station_value(cbs_code, 'FG', station_data, date_str) # 0.1 unit
        monthly_rain = 0.1 * get_monthly_precipitation(cbs_code, year, month, monthly_precip)
        # Calculate TCI if all required variables are available
        if all(v is not None for v in [t_max, t_mean, rh_mean, avg_humidity, daily_sun, wind_speed, monthly_rain]):
            tci = calculate_tci_from_weather_data(
                t_max=t_max,
                t_mean=t_mean,
                rh_mean=rh_mean,
                avg_humidity=avg_humidity,
                daily_sun=daily_sun,
                wind_speed=wind_speed,
                monthly_rain=monthly_rain
            )
            results.append({
                'cbs_code': cbs_code,
                'date': date_str,
                'tci': tci
            })

    elapsed_seconds = perf_counter() - date_start_time
    print(f"Finished date: {current_date.date()} in {elapsed_seconds:.2f} seconds")
    
    current_date += timedelta(days=1)

# Save results
output_df = pd.DataFrame(results)
output_df.to_csv(OUTPUT_FILE, index=False, header=False)
print(f"TCI calculations saved to {OUTPUT_FILE}")
