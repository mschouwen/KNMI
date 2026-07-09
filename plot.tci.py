import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV file
df = pd.read_csv(r'd:\temp\tci.txt', header=None, names=['cbs_code', 'date', 'count'])

# Filter for cbs_code 8XXX
code = 590
df_filtered = df[df['cbs_code'] == code].copy()

# Convert date to datetime for better plotting
df_filtered['date'] = pd.to_datetime(df_filtered['date'], format='%Y%m%d')

# Sort by date
df_filtered = df_filtered.sort_values('date')

# Create the plot
plt.figure(figsize=(10, 6))
plt.plot(df_filtered['date'], df_filtered['count'], marker='o', linestyle='-', linewidth=2)
plt.xlabel('Date')
plt.ylabel('Count')
plt.title('Count vs Date for CBS Code:' + str(code))
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
