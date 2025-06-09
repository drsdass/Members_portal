
import pandas as pd

try:
    access_df = pd.read_csv('access.csv')
except Exception as e:
    access_df = pd.DataFrame()
    print(f"Error loading access.csv: {e}")

# Rest of the app code placeholder
print("App code starts here.")
