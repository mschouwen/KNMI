import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file
df = pd.read_csv(r'd:\temp\tci.txt', header=None, names=['cbs_code', 'date', 'tci'])

# Filter for cbs_code
code = 590
df_filtered = df[df['cbs_code'] == code].copy()

# Convert date to datetime
df_filtered['date'] = pd.to_datetime(df_filtered['date'], format='%Y%m%d')

# Sort by date
df_filtered = df_filtered.sort_values('date')

# Calculate weekly average (ISO week, week starts Monday)
df_filtered['week_start'] = df_filtered['date'] - pd.to_timedelta(df_filtered['date'].dt.dayofweek, unit='D')
df_filtered['year'] = df_filtered['date'].dt.year
weekly_avg = df_filtered.groupby('week_start')['tci'].mean().reset_index()
weekly_avg.columns = ['week_start', 'tci_avg']

# Calculate yearly average and merge onto weekly data
yearly_avg = df_filtered.groupby('year')['tci'].mean().rename('tci_yearly_avg')
weekly_avg['year'] = weekly_avg['week_start'].dt.year
weekly_avg = weekly_avg.merge(yearly_avg, on='year')

# Deviation of weekly average from the yearly average
weekly_avg['deviation'] = weekly_avg['tci_avg'] - weekly_avg['tci_yearly_avg']

# Plot deviation per week
colors = ['steelblue' if v >= 0 else 'tomato' for v in weekly_avg['deviation']]
plt.figure(figsize=(14, 6))
plt.bar(weekly_avg['week_start'], weekly_avg['deviation'], width=5, align='edge',
        color=colors, edgecolor='white')
plt.axhline(0, color='black', linewidth=0.8)
plt.xlabel('Week starting (Monday)')
plt.ylabel('TCI deviation from yearly average')
plt.title(f'Weekly TCI vs Yearly Average — CBS Code {code}')
plt.grid(True, axis='y', alpha=0.3)
plt.xticks(weekly_avg['week_start'], weekly_avg['week_start'].dt.strftime('%Y-%m-%d'), rotation=45, ha='right')
plt.tight_layout()
plt.show()
