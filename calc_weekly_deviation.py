import pandas as pd

# Read the CSV file
df = pd.read_csv(r'd:\temp\tci.txt', header=None, names=['cbs_code', 'date', 'tci'])

# Parse date and derive helper columns
df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
df['year'] = df['date'].dt.year
df['week_start'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='D')

# Weekly average TCI per cbs_code
weekly_avg = (
    df.groupby(['cbs_code', 'week_start'])['tci']
    .mean()
    .reset_index()
    .rename(columns={'tci': 'tci_weekly_avg'})
)

# Yearly average TCI per cbs_code
yearly_avg = (
    df.groupby(['cbs_code', 'year'])['tci']
    .mean()
    .reset_index()
    .rename(columns={'tci': 'tci_yearly_avg'})
)

# Attach the year to weekly data so we can join the yearly average
weekly_avg['year'] = weekly_avg['week_start'].dt.year
weekly_avg = weekly_avg.merge(yearly_avg, on=['cbs_code', 'year'])

# Deviation = weekly average minus yearly average, then scale within each municipality/year to [-2, 2]
weekly_avg['deviation_raw'] = weekly_avg['tci_weekly_avg'] - weekly_avg['tci_yearly_avg']

def scale_to_range_2(series):
    min_val = series.min()
    max_val = series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return 4 * (series - min_val) / (max_val - min_val) - 2

weekly_avg['deviation'] = (
    weekly_avg.groupby(['cbs_code', 'year'])['deviation_raw']
    .transform(scale_to_range_2)
)

# Keep and order the output columns
result = weekly_avg[['cbs_code', 'week_start', 'tci_yearly_avg', 'deviation']].copy()
result = result.sort_values(['cbs_code', 'week_start']).reset_index(drop=True)

# Format week_start as YYYYMMdd and keep a compact scaled deviation value
result['week_start'] = result['week_start'].dt.strftime('%Y%m%d')
result['tci_yearly_avg'] = result['tci_yearly_avg'].round().astype(int)
result['deviation'] = result['deviation'].round(2)

# Write to CSV
output_path = r'd:\temp\tci_weekly_deviation.csv'
result.to_csv(output_path, index=False)
print(f"Written {len(result)} rows to {output_path}")
print(result.head(10).to_string(index=False))
