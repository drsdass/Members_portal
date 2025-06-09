
import pandas as pd
from flask import Flask

app = Flask(__name__)

# Load access.csv with error handling
try:
    access_df = pd.read_csv('access.csv')
except Exception as e:
    print(f"Failed to load access.csv: {e}")
    access_df = pd.DataFrame()
