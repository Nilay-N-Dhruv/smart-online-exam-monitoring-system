import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime

# Example data
phases = ["Planning", "Research", "Design", "Development", "Monitoring Setup",
          "Data Handling", "System Testing", "Deployment", "Documentation"]
start_dates = ["2025-10-14", "2025-10-22", "2025-10-29", "2025-11-05", 
               "2025-11-19", "2025-11-26", "2025-12-03", "2025-12-10", "2025-12-17"]
end_dates = ["2025-10-21", "2025-10-28", "2025-11-04", "2025-11-18", 
             "2025-11-25", "2025-12-02", "2025-12-09", "2025-12-16", "2025-12-20"]

# Convert to datetime
start_dates = pd.to_datetime(start_dates)
end_dates = pd.to_datetime(end_dates)

# Plot
fig, ax = plt.subplots(figsize=(12,6))  # Increase figure width to add space
for i, phase in enumerate(phases):
    ax.barh(phase, (end_dates[i] - start_dates[i]).days, left=start_dates[i], color='skyblue')

# Format x-axis
ax.xaxis_date()
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))  # space between ticks
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
plt.xticks(rotation=45, ha='right')  # rotate dates for clarity

# Add grid
ax.grid(True, which='major', axis='x', linestyle='--', color='gray', alpha=0.7)

ax.set_xlabel("Timeline")
ax.set_ylabel("Project Phases")
ax.set_title("Project Gantt Chart (Date-based Timeline)")
plt.tight_layout()
plt.show()
