import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re # Import the regular expression module

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
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': [e for e in MASTER_ENTITIES if e != 'Stat Labs']},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES}, # Has unfiltered access
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES},
    'Andrew': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois', 'AIM Laboratories']},
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois', 'AIM Laboratories']},
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

@app.route('/dashboard', methods=['GET', 'POST']) # Allow POST requests to dashboard
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    
    # Define months and years for dropdowns (needed for both dashboard.html and monthly_bonus.html)
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
        # If coming from a form submission on monthly_bonus.html or dashboard.html
        selected_entity = request.form.get('entity_name')
        report_type = request.form.get('report_type')
        selected_month = int(request.form.get('month')) if request.form.get('month') else None
        selected_year = int(request.form.get('year')) if request.form.get('year') else None

        # Update session with new selections
        session['selected_entity'] = selected_entity
        session['selected_month'] = selected_month
        session['selected_year'] = selected_year
        session['report_type'] = report_type
    else:
        # If coming from initial redirect from select_report or direct GET
        selected_entity = session.get('selected_entity')
        report_type = session.get('report_type')
        selected_month = session.get('selected_month')
        selected_year = session.get('selected_year')

    # Authorization check for selected entity
    user_authorized_entities = users[rep]['entities']
    if selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
             return render_template(
                'unauthorized.html',
                message=f"You do not have any entities assigned to view reports. Please contact support."
            )
        return render_template(
            'select_report.html', # Redirect back to selection if not authorized for entity
            master_entities=MASTER_ENTITIES, # Use MASTER_ENTITIES for the initial selection page
            months=months,
            years=years,
            error=f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for."
        )


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
        
        # NEW FILTERING FOR MONTHLY BONUS REPORTS: Filter by 'Username' column for non-unfiltered users
        if report_type == 'monthly_bonus' and 'Username' in filtered_data.columns: # Changed to 'Username'
            normalized_username = rep.strip().lower()
            
            # Ensure 'Username' column is treated as string for .str methods
            filtered_data['Username'] = filtered_data['Username'].astype(str)

            # Updated logic: Check if the normalized_username is contained within the (potentially comma-separated) Username string
            # Using regex for word boundaries to avoid partial matches (e.g., 'and' matching 'andrewS')
            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    # Define financial files structure
    financial_files_data = {
        2023: [
            {'name': '2023 1Q Profit and Loss', 'filename': '2023_1Q_PL.pdf'},
            {'name': '2023 1Q Balance Sheet', 'filename': '2023_1Q_BS.pdf'},
            {'name': '2023 2Q Profit and Loss', 'filename': '2023_2Q_PL.pdf'},
            {'name': '2023 2Q Balance Sheet', 'filename': '2023_2Q_BS.pdf'},
            {'name': '2023 3Q Profit and Loss', 'filename': '2023_3Q_PL.pdf'},
            {'name': '2023 3Q Balance Sheet', 'filename': '2023_3Q_BS.pdf'},
            {'name': '2023 4Q Profit and Loss', 'filename': '2023_4Q_PL.pdf'},
            {'name': '2023 4Q Balance Sheet', 'filename': '2023_4Q_BS.pdf'},
            {'name': '2023 Annual Report', 'filename': '2023_Annual.pdf'}
        ],
        2024: [
            {'name': '2024 1Q Profit and Loss', 'filename': '2024_1Q_PL.pdf'},
            {'name': '2024 1Q Balance Sheet', 'filename': '2024_1Q_BS.pdf'},
            {'name': '2024 2Q Profit and Loss', 'filename': '2024_2Q_PL.pdf'},
            {'name': '2024 2Q Balance Sheet', 'filename': '2024_2Q_BS.pdf'},
            {'name': '2024 3Q Profit and Loss', 'filename': '2024_3Q_PL.pdf'},
            {'name': '2024 3Q Balance Sheet', 'filename': '2024_3Q_BS.pdf'},
            {'name': '2024 4Q Profit and Loss', 'filename': '2024_4Q_PL.pdf'},
            {'name': '2024 4Q Balance Sheet', 'filename': '2024_4Q_BS.pdf'},
            {'name': '2024 Annual Report', 'filename': '2024_Annual.pdf'}
        ],
        2025: [
            {'name': '2025 1Q Profit and Loss', 'filename': '2025_1Q_PL.pdf'}, # Corrected typo here
            {'name': '2025 1Q Balance Sheet', 'filename': '2025_1Q_BS.pdf'},
            {'name': '2025 2Q Profit and Loss', 'filename': '2025_2Q_PL.pdf'},
            {'name': '2025 2Q Balance Sheet', 'filename': '2025_2Q_BS.pdf'},
            {'name': '2025 3Q Profit and Loss', 'filename': '2025_3Q_PL.pdf'},
            {'name': '2025 3Q Balance Sheet', 'filename': '2025_3Q_BS.pdf'},
            {'name': '2025 4Q Profit and Loss', 'filename': '2025_4Q_PL.pdf'},
            {'name': '2025 4Q Balance Sheet', 'filename': '2025_4Q_BS.pdf'},
            {'name': '2025 Annual Report', 'filename': '2025_Annual.pdf'},
            {'name': '2025 YTD Report', 'filename': '2025_YTD.pdf'}
        ]
    }

    if report_type == 'financials':
        # Filter files based on selected_year if provided, otherwise show all years
        files_to_display = {}
        if selected_year:
            if selected_year in financial_files_data:
                files_to_display[selected_year] = [
                    {'name': item['name'], 'webViewLink': url_for('static', filename=item['filename'])}
                    for item in financial_files_data[selected_year]
                ]
            else:
                files_to_display = {} # No files for the selected year
        else:
            for year, reports in financial_files_data.items():
                files_to_display[year] = [
                    {'name': item['name'], 'webViewLink': url_for('static', filename=item['filename'])}
                    for item in reports
                ]

        return render_template(
            'dashboard.html',
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display, # Pass the structured files data
            master_entities=user_authorized_entities, # Only authorized entities for this user
            years=years, # Only years dropdown for financials
            selected_year=selected_year
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            master_entities=user_authorized_entities, # Only authorized entities for this user
            months=months,
            years=years,
            selected_month=selected_month,
            selected_year=selected_year
        )
    # NEW: Handle 'requisitions' and 'marketing_material'
    elif report_type == 'requisitions':
        # You would fetch or generate data/files relevant to requisitions here
        # For now, let's return a simple placeholder page or redirect
        return render_template(
            'generic_report.html', # Create a generic_report.html template for these
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development."
        )
    elif report_type == 'marketing_material':
        # You would fetch or generate data/files relevant to marketing material here
        return render_template(
            'generic_report.html', # Create a generic_report.html template for these
            report_title="Marketing Material Report",
            message=f"Marketing Material for {selected_entity} is under development."
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
    
    # Create dummy PDF files for financial reports
    financial_pdf_names = []
    for year in range(2023, 2026):
        for q in ['1Q', '2Q', '3Q', '4Q']:
            financial_pdf_names.append(f"{year}_{q}_PL.pdf")
            financial_pdf_names.append(f"{year}_{q}_BS.pdf")
        financial_pdf_names.append(f"{year}_Annual.pdf")
    financial_pdf_names.append("2025_YTD.pdf") # Add the 2025 YTD report

    for filename in financial_pdf_names:
        filepath = os.path.join('static', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file for {filename}")
            print(f"Created dummy file: {filepath}")

    # Create dummy data.csv if it doesn't exist, with new columns and example data
    if not os.path.exists('data.csv'):
        dummy_data = {
            'Date': [
                '2025-03-12', '2025-03-15', '2025-03-18', '2025-03-20', '2025-03-22', # March 2025 data
                '2025-04-01', '2025-04-05', '2025-04-10', '2025-04-15', # April 2025 data
                '2025-02-01', '2025-02-05', # February 2025 data
                '2025-03-25', '2025-03-28', '2025-03-30', # More March data
                '2025-04-20', '2025-04-22', # More April data
                '2025-02-01', # Specific row for AndrewS bonus report test
                '2025-03-01' # New row for multi-user test
            ],
            'Location': [
                'CENTRAL KENTUCKY SPINE SURGERY - TOX', 'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA',
                'HOPESS RESIDENTIAL TREATMENT', 'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
                'TEST LOCATION A', 'TEST LOCATION B', 'TEST LOCATION C', 'TEST LOCATION D',
                'OLD LOCATION X', 'OLD LOCATION Y',
                'NEW CLINIC Z', 'URGENT CARE A', 'HOSPITAL B',
                'HEALTH CENTER C', 'WELLNESS SPA D',
                'BETA TEST LOCATION', # Specific row for AndrewS bonus report test
                'SHARED PERFORMANCE CLINIC' # New row for multi-user test
            ],
            'Reimbursement': [1.98, 150.49, 805.13, 2466.87, 76542.07,
                              500.00, 750.00, 120.00, 900.00,
                              300.00, 450.00,
                              600.00, 150.00, 2500.00,
                              350.00, 80.00,
                              38.85,
                              1200.00], # New row for multi-user test
            'COGS': [50.00, 151.64, 250.00, 1950.00, 30725.00,
                     200.00, 300.00, 50.00, 400.00,
                     100.00, 150.00,
                     250.00, 70.00, 1800.00,
                     120.00, 30.00,
                     25.00,
                     500.00], # New row for multi-user test
            'Net': [-48.02, -1.15, 555.13, 516.87, 45817.07,
                               300.00, 450.00, 70.00, 500.00,
                               200.00, 300.00,
                               350.00, 80.00, 700.00,
                               230.00, 50.00,
                               13.85,
                               700.00], # New row for multi-user test
            'Commission': [-14.40, -0.34, 166.53, 155.06, 13745.12,
                               90.00, 135.00, 21.00, 150.00,
                               60.00, 90.00,
                               105.00, 24.00, 210.00,
                               69.00, 15.00,
                               4.16,
                               210.00], # New row for multi-user test
            'Entity': [
                'AIM Laboratories', 'First Bio Lab of Illinois', 'Stat Labs', 'AMICO Dx', 'Enviro Labs', # March data
                'First Bio Lab', 'AIM Laboratories', 'First Bio Genetics', 'Stat Labs', # April data
                'Enviro Labs', 'AMICO Dx', # Feb data
                'First Bio Lab', 'AIM Laboratories', 'First Bio Lab of Illinois', # More March data
                'First Bio Genetics', 'Enviro Labs', # More April data
                'AIM Laboratories', # Specific row for AndrewS bonus report test
                'First Bio Lab' # New row for multi-user test
            ],
            'Associated Rep Name': [ # This is for display in the table
                'House', 'House', 'Sonny A', 'Jay M', 'Bob S',
                'Satish D', 'ACG', 'Melinda C', 'Mina K',
                'Vince O', 'Nick C',
                'Ashlie T', 'Omar', 'Darang T',
                'Andrew', 'Jay M',
                'Andrew S', # Specific row for AndrewS bonus report test
                'Andrew S, Melinda C' # New row for multi-user test
            ],
            'Username': [ # NEW COLUMN - For filtering, must match login username
                'House', 'House', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew', 'JayM',
                'AndrewS', # Matches AndrewS login username
                'AndrewS,MelindaC' # Allows both AndrewS and MelindaC to see this line
            ]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv('data.csv', index=False)
        print("Created dummy data.csv for demonstration.")

    app.run(debug=True)
