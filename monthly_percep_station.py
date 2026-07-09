import pandas as pd
from pathlib import Path
from collections import defaultdict
from config import data_path

# Read the station_data.txt file
input_path = data_path("station_data.txt")
df = pd.read_csv(str(input_path))

# Convert YYYYMMDD to datetime format and extract year-month
df['YYYYMMDD'] = df['YYYYMMDD'].astype(str).str.zfill(8)
df['Year_Month'] = df['YYYYMMDD'].str[:6]

# Replace NaN values in RH with 0
df['RH'] = df['RH'].fillna(0)

# Group by station and year-month, then sum the precipitation
monthly_precip = df.groupby(['STN', 'Year_Month'])['RH'].sum().reset_index()
monthly_precip.columns = ['STN', 'Year_Month', 'Monthly_Precipitation']

# Remove stations that only have zero precipitation across all months.
all_zero_station = monthly_precip.groupby('STN')['Monthly_Precipitation'].transform(lambda s: (s == 0).all())
monthly_precip = monthly_precip[~all_zero_station]

# Write to output file
with open(data_path('montly_percep_station.txt'), 'w') as f:
    f.write('STN Year_Month Monthly_Precipitation\n')
    for _, row in monthly_precip.iterrows():
        f.write(f"{row['STN']} {row['Year_Month']} {row['Monthly_Precipitation']}\n")

print("Monthly precipitation aggregated and saved to montly_percep_station.txt")
