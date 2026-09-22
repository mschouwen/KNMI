import csv
import math
from config import data_path


MIN_DUTCH_LAT = 50.0
MAX_DUTCH_LAT = 54.0
MIN_DUTCH_LON = 3.0
MAX_DUTCH_LON = 8.0


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def is_dutch_coordinate(lat, lon):
    return MIN_DUTCH_LAT <= lat <= MAX_DUTCH_LAT and MIN_DUTCH_LON <= lon <= MAX_DUTCH_LON

# Read gemeente.txt
gemeente_data = {}
skipped_municipalities = 0
with open(data_path('gemeente_spatial.txt'), 'r', encoding='utf-8', newline='') as f:
    reader = csv.reader(f)
    next(reader, None)
    for row in reader:
        if not row:
            continue

        cbs_code = row[3].strip()
        municipality_name = row[2].strip()
        geom_x = float(row[-2])
        geom_y = float(row[-1])

        if not is_dutch_coordinate(geom_y, geom_x):
            skipped_municipalities += 1
            continue

        gemeente_data[cbs_code] = {
            'municipality_name': municipality_name,
            'lat': geom_y,
            'lon': geom_x,
        }

# Read station_locations.txt
stations_data = {}
skipped_stations = 0
with open(data_path('station_locations.txt'), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        stn = row['STN']
        lat = float(row['LAT'])
        lon = float(row['LON'])

        if not is_dutch_coordinate(lat, lon):
            skipped_stations += 1
            continue

        stations_data[stn] = (lat, lon)

# Calculate distance ranking for each municipality
results = []
for cbs_code, municipality in gemeente_data.items():
    gem_lat = municipality['lat']
    gem_lon = municipality['lon']
    station_distances = []

    for stn, (sta_lat, sta_lon) in stations_data.items():
        distance = haversine_distance(gem_lat, gem_lon, sta_lat, sta_lon)
        station_distances.append((stn, distance))

    station_distances.sort(key=lambda item: item[1])
    sorted_station_ids = ":".join(station_id for station_id, _ in station_distances)
    results.append({
        'cbs_code': cbs_code,
        'municipality_name': municipality['municipality_name'],
        'station_id': sorted_station_ids,
    })

results.sort(key=lambda row: row['cbs_code'])

# Write results to file
with open(data_path('dist_municipality_station.txt'), 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['cbs_code', 'municipality_name', 'station_id'])
    writer.writeheader()
    writer.writerows(results)

print(f"Distance calculation completed. Results written to {data_path('dist_municipality_station.txt')}")
print(f"Skipped municipalities with invalid coordinates: {skipped_municipalities}")
print(f"Skipped stations with invalid coordinates: {skipped_stations}")
