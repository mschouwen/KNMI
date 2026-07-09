import pandas as pd
import os
import importlib.util
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
YEAR = 2025
DATA_DIR = r'd:\temp'
OUTPUT_FILE = os.path.join(DATA_DIR, 'tci.txt')

# Load data files
dist_municipality_station = pd.read_csv(os.path.join(DATA_DIR, 'dist_municipality_station.txt'))
station_data = pd.read_csv(os.path.join(DATA_DIR, 'station_data.txt'))
monthly_precip = pd.read_csv(os.path.join(DATA_DIR, 'montly_percep_station.txt'))

station_data['YYYYMMDD'] = station_data['YYYYMMDD'].astype(str).str.zfill(8)

def get_station_value(cbs_code, column, station_data, yyyymmdd):
    """Get value from closest available station for a given municipality and date."""
    stations = dist_municipality_station[dist_municipality_station['cbs_code'] == cbs_code]['station_id'].values
    
    if len(stations) == 0:
        return None
    
    station_list = stations[0].split(':')
    
    for station_id in station_list:
        station_id = int(station_id.strip())
        station_row = station_data[
            (station_data['STN'] == station_id) &
            (station_data['YYYYMMDD'] == yyyymmdd)
        ]
        
        if not station_row.empty and column in station_row.columns:
            value = station_row[column].values[0]
            if pd.notna(value):
                return value
    
    return None

def get_monthly_precipitation(cbs_code, year, month, monthly_precip):
    """Get monthly precipitation from closest available station."""
    stations = dist_municipality_station[dist_municipality_station['cbs_code'] == cbs_code]['station_id'].values
    
    if len(stations) == 0:
        return None
    
    station_list = stations[0].split(':')
    year_month = f"{year:04d}{month:02d}"
    
    for station_id in station_list:
        station_id = int(station_id.strip())
        precip_row = monthly_precip[(monthly_precip['STN'] == station_id) & 
                                    (monthly_precip['Year_Month'] == int(year_month))]
        
        if not precip_row.empty:
            return precip_row['Monthly_Precipitation'].values[0]
    
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
