import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# --- Master List of All Entities (RESTRICTED to the 7 core company/lab entities) ---
MASTER_ENTITIES = sorted([
    'First Bio Lab',
    'First Bio Genetics',
    'First Bio Lab of Illinois',
    'AIM Laboratories',
    'AMICO Dx',
    'Enviro Labs',
    'Stat Labs'
])

# --- Users with Unfiltered Access ---
UNFILTERED_ACCESS_USERS = ['AshlieT', 'MinaK', 'BobS', 'SatishD']

# --- User Management (In-memory, with individual names as usernames) ---
users = {
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES}, # Has unfiltered access
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES},
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES}, # Has unfiltered access
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': MASTER_ENTITIES},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES}, # Has unfiltered access
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES},
    'Andrew': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics']},
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois']},
    'House': {'password_hash': generate_password_hash('password9'), 'entities': []},
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx']},
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories']},
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES},
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx']},
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES}, # Has unfiltered access
}

# --- Data Loading (Optimized: Load once at app startup) ---
df = pd.DataFrame() # Initialize as empty to avoid error if file not found
try:
    df = pd.read_csv('data.csv', parse_dates=['Date']) # Parse 'Date' column as datetime objects
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py. Dummy data will be created.")
except Exception as e:
    print(f"An error occurred while loading data.csv: {e}")

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_info = users.get(username)
        if user_info and check_password_hash(user_info['password_hash'], password):
            session['username'] = username
            return redirect(url_for('select_report'))
        else:
            return render_template('login.html', error='Invalid username or password.'), 401
    return render_template('login.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_authorized_entities = users[username]['entities']

    # Generate lists for months and years for the dropdowns
    months = [
        {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
        {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
        {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
        {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
        {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
        {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'}
    ]
    current_year = datetime.datetime.now().year
    years = list(range(current_year - 2, current_year + 2)) # e.g., 2023, 2024, 2025, 2026

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        selected_entity = request.form.get('entity_name')
        selected_month = request.form.get('month')
        selected_year = request.form.get('year')

        if not report_type or not selected_entity:
            return render_template(
                'select_report.html',
                master_entities=MASTER_ENTITIES,
                months=months,
                years=years,
                error="Please select both a report type and an entity."
            )

        if selected_entity not in user_authorized_entities:
            if not user_authorized_entities:
                return render_template(
                    'unauthorized.html',
                    message=f"You do not have any entities assigned to view reports. Please contact support."
                )
            return render_template(
                'select_report.html',
                master_entities=MASTER_ENTITIES,
                months=months,
                years=years,
                error=f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for."
            )
        
        # Store selections in session
        session['report_type'] = report_type
        session['selected_entity'] = selected_entity
        session['selected_month'] = int(selected_month) if selected_month else None
        session['selected_year'] = int(selected_year) if selected_year else None
        
        return redirect(url_for('dashboard'))
    
    return render_template('select_report.html', master_entities=MASTER_ENTITIES, months=months, years=years)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session or 'report_type' not in session or 'selected_entity' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    selected_entity = session['selected_entity']
    report_type = session.get('report_type')
    selected_month = session.get('selected_month')
    selected_year = session.get('selected_year')

    filtered_data = pd.DataFrame()

    # Check if the current user has unfiltered access
    if rep in UNFILTERED_ACCESS_USERS:
        if not df.empty:
            filtered_data = df.copy() # Provide a copy of the entire DataFrame
        print(f"User {rep} has unfiltered access. Displaying all data.")
    elif not df.empty and 'Entity' in df.columns:
        # Existing filtering logic for other users
        filtered_data = df[df['Entity'] == selected_entity].copy()

        if selected_month and selected_year and 'Date' in filtered_data.columns:
            if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
            
            filtered_data = filtered_data[
                (filtered_data['Date'].dt.month == selected_month) &
                (filtered_data['Date'].dt.year == selected_year)
            ]
        
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    if report_type == 'financials':
        files = [
            {'name': '2023 Full Report.pdf', 'webViewLink': url_for('static', filename='example1.pdf')},
            {'name': '2024 Full Report.pdf', 'webViewLink': url_for('static', filename='example2.pdf')},
            {'name': '2025 YTD Financials.pdf', 'webViewLink': url_for('static', filename='example1.pdf')},
            {'name': '2025 Last Month Financials.pdf', 'webViewLink': url_for('static', filename='example2.pdf')}
        ]
        return render_template(
            'dashboard.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type
        )
    else:
        return redirect(url_for('select_report'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Run the application ---
if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    for filename in ['example1.pdf', 'example2.pdf']:
        filepath = os.path.join('static', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file: {filename}")
            print(f"Created dummy file: {filepath}")

    # Create dummy data.csv if it doesn't exist, with new columns and example data
    if not os.path.exists('data.csv'):
        dummy_data = {
            'Date': [
                '2025-03-10', '2025-03-12', '2025-03-15', '2025-03-18', '2025-03-20', '2025-03-22', # March 2025 data
                '2025-04-01', '2025-04-05', '2025-04-10', '2025-04-15', # April 2025 data
                '2025-02-01', '2025-02-05' # February 2025 data
            ],
            'Location': [
                'BIRCH TREE RECOVERY', 'CENTRAL KENTUCKY SPINE SURGERY - TOX', 'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA',
                'HOPESS RESIDENTIAL TREATMENT', 'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
                'TEST LOCATION A', 'TEST LOCATION B', 'TEST LOCATION C', 'TEST LOCATION D',
                'OLD LOCATION X', 'OLD LOCATION Y'
            ],
            'Reimbursement': [186.49, 1.98, 150.49, 805.13, 2466.87, 76542.07,
                              500.00, 750.00, 120.00, 900.00,
                              300.00, 450.00],
            'COGS': [150, 50, 151.64, 250, 1950, 30725,
                     200.00, 300.00, 50.00, 400.00,
                     100.00, 150.00],
            'Net Commission': [36.49, -48.02, -1.15, 555.13, 516.87, 45817.07,
                               300.00, 450.00, 70.00, 500.00,
                               200.00, 300.00],
            'Entity': [
                'First Bio Lab', 'AIM Laboratories', 'First Bio Lab of Illinois', 'Stat Labs', 'AMICO Dx', 'Enviro Labs', # Matching your example Reps to Entities
                'First Bio Lab', 'AIM Laboratories', 'First Bio Genetics', 'Stat Labs', # April data for various entities
                'Enviro Labs', 'AMICO Dx' # Feb data for various entities
            ],
            'Associated Rep Name': [ # This column will now contain the individual names
                'AndrewS', 'House', 'House', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC'
            ]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv('data.csv', index=False)
        print("Created dummy data.csv for demonstration.")

    app.run(debug=True)
