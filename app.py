
from flask import Flask
import pandas as pd

app = Flask(__name__)

# Load access.csv with fallback
try:
    access_df = pd.read_csv('access.csv')
except Exception as e:
    access_df = pd.DataFrame()
    print(f"Error loading access.csv: {e}")

@app.route("/")
def index():
    return "Flask app is running successfully!"

if __name__ == '__main__':
    app.run(debug=True)

# Ensure Gunicorn can find the app
app = app
