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

# --- Master List of All Entities (RESTRICTED to the 7 core company/lab entities, updated with LLC) ---
MASTER_ENTITIES = sorted([
    'First Bio Lab',
    'First Bio Genetics LLC', # Updated based on file names
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC',   # Updated based on file names
    'AMICO Dx LLC',           # Updated based on file names
    'AMICO Dx',
    'Enviro Labs LLC',        # Updated based on file names
    'Stat Labs'
])

# --- Users with Unfiltered Access ---
UNFILTERED_ACCESS_USERS = ['AshlieT', 'MinaK', 'BobS', 'SatishD']

# --- User Management (In-memory, with individual names as usernames and their roles) ---
users = {
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'members'}, # Has unfiltered access
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'members'},
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'members'}, # Has unfiltered access
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': [e for e in MASTER_ENTITIES if e != 'Stat Labs'], 'role': 'members'},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'members'}, # Has unfiltered access
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES, 'role': 'members'}, # JayM has access to MASTER_ENTITIES
    'Andrew': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'members'}, # Updated entities
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'members'}, # Updated entities
    'House': {'password_hash': generate_password_hash('password9'), 'entities': [], 'role': 'members'},
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx LLC'], 'role': 'members'}, # Updated entity
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'members'}, # Updated entity
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'members'},
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx LLC'], 'role': 'members'}, # Updated entity
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'members'},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'members'},
    # Sales & Marketing Users
    'SalesUser1': {'password_hash': generate_password_hash('salespass1'), 'entities': MASTER_ENTITIES, 'role': 'sales_marketing'}, # Can see all entities for demo
    'MarketingUser1': {'password_hash': generate_password_hash('marketpass1'), 'entities': MASTER_ENTITIES, 'role': 'sales_marketing'}, # Can see all entities for demo
}

# --- Define Report Types by Role ---
REPORT_TYPES_BY_ROLE = {
    'members': [
        {'value': 'financials', 'name': 'Financials Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'}
    ],
    'sales_marketing': [
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'} # Monthly bonus for sales/marketing too
    ]
}

# --- Financial Report Definitions (for generating entity-specific filenames and display names) ---
# Each entry now specifies the display name part, the accounting basis, and the file suffix.
# The file_suffix now matches the actual file names provided by the user.
FINANCIAL_REPORT_DEFINITIONS = [
    {'display_name_part': 'Profit and Loss account', 'basis': 'Accrual Basis', 'file_suffix': '-Profit and Loss account - Accrual basis'},
    {'display_name_part': 'Profit and Loss account', 'basis': 'Cash Basis', 'file_suffix': '-Profit and Loss account - Cash Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Accrual Basis', 'file_suffix': '-Balance Sheet - Accrual Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Cash Basis', 'file_suffix': '-Balance Sheet - Cash Basis'},
    # New report added as per user request
    {'display_name_part': 'YTD Management Report', 'basis': 'Cash Basis', 'file_suffix': '-YTD Management Report - Cash Basis', 'applicable_years': [2025]}
]


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

@app.route('/')
def index():
    """Redirects to the role selection page."""
    return redirect(url_for('select_role'))

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    """Allows user to select their role (Members or Sales & Marketing)."""
    if request.method == 'POST':
        selected_role = request.form.get('role')
        if selected_role in ['members', 'sales_marketing']:
            session['selected_role'] = selected_role
            return redirect(url_for('login'))
        else:
            # Handle invalid role selection, though buttons should prevent this
            return render_template('role_selection.html', error="Invalid role selected.")
    return render_template('role_selection.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login after a role has been selected.
    """
    if 'selected_role' not in session:
        return redirect(url_for('select_role')) # Ensure a role is selected first

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_info = users.get(username) # Get user info from the flat dictionary

        # Check if user exists and if their role matches the selected session role
        if user_info and user_info.get('role') == session['selected_role'] and check_password_hash(user_info['password_hash'], password):
            session['username'] = username
            session['user_role'] = user_info['role'] # Store the user's role in session
            return redirect(url_for('select_report'))
        else:
            return render_template('login.html', error='Invalid username or password.'), 401
    
    # For GET request, render login form
    return render_template('login.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role'] # Get the user's role
    user_authorized_entities = users[username]['entities']

    # Filter master entities based on the user's authorized entities
    # This ensures the dropdown only shows entities the user can access
    display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Get report types based on the user's role
    available_report_types = REPORT_TYPES_BY_ROLE.get(user_role, [])

    # Generate lists for months and years for the dropdowns (for monthly bonus and financials)
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
                master_entities=display_entities, # Use filtered entities here
                available_report_types=available_report_types, # Pass filtered report types
                months=months,
                years=years,
                error="Please select both a report type and an entity."
            )

        # Authorization check: Ensure the selected entity is one the user is authorized for
        if selected_entity not in user_authorized_entities:
            return render_template(
                'unauthorized.html',
                message=f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity."
            )
        
        # Store selections in session
        session['report_type'] = report_type
        session['selected_entity'] = selected_entity
        session['selected_month'] = int(selected_month) if selected_month else None
        session['selected_year'] = int(selected_year) if selected_year else None
        
        return redirect(url_for('dashboard'))
    
    return render_template(
        'select_report.html',
        master_entities=display_entities, # Pass filtered entities to template
        available_report_types=available_report_types, # Pass filtered report types to template
        months=months,
        years=years
    )

@app.route('/dashboard', methods=['GET', 'POST']) # Allow POST requests to dashboard
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    
    # Define months and years for dropdowns (needed for dashboard.html and monthly_bonus.html)
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
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Pass authorized entities
            available_report_types=REPORT_TYPES_BY_ROLE.get(users[rep]['role'], []), # Pass role-specific reports
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

            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    if report_type == 'financials':
        files_to_display = {}
        
        # Determine which years to process (all relevant years or just the selected one)
        years_to_process = [selected_year] if selected_year else range(current_year - 2, current_year + 2)

        for year_val in years_to_process:
            year_reports = []
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                # Check if report is applicable for the current year (if 'applicable_years' is defined)
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                # Construct the display name (e.g., "AIM Laboratories LLC - Balance Sheet - 2024 - Cash Basis")
                display_name = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}"
                
                # Construct the filename exactly as provided by the user:
                # "AIM Laboratories LLC - Balance Sheet - 2024 - Cash Basis.pdf"
                filename = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath_check = os.path.join('static', filename)

                if os.path.exists(filepath_check): # Only add if the file actually exists in static folder
                    year_reports.append({
                        'name': display_name,
                        'webViewLink': url_for('static', filename=filename)
                    })
            if year_reports: # Only add the year if there are reports for it
                files_to_display[year_val] = year_reports

        return render_template(
            'dashboard.html',
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display, # Pass the structured files data
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Only authorized entities for this user
            years=years, # Years dropdown for financials
            selected_year=selected_year,
            months=months # Pass months for display in dashboard if needed
        )
    # --- Other Report Types Logic (remains the same) ---
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Only authorized entities for this user
            months=months,
            years=years,
            selected_month=selected_month,
            selected_year=selected_year
        )
    elif report_type == 'requisitions':
        # Placeholder for Requisitions report
        return render_template(
            'generic_report.html',
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development."
        )
    elif report_type == 'marketing_material':
        # Placeholder for Marketing Material report
        return render_template(
            'generic_report.html',
            report_title="Marketing Material Report",
            message=f"Marketing Material for {selected_entity} is under development."
        )
    else:
        return redirect(url_for('select_report'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Run the application and create dummy files ---
if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    
    current_app_year = datetime.datetime.now().year
    
    # Create dummy PDF files for financial reports (entity-specific)
    for year_val in range(current_app_year - 2, current_app_year + 2):
        for entity in MASTER_ENTITIES:
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                # Check if report is applicable for the current year (if 'applicable_years' is defined)
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                # Construct the filename exactly as it should be in the static folder:
                # "Entity Name - Report Type - Year - Basis.pdf"
                filename_to_create = f"{entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath = os.path.join('static', filename_to_create)
                
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"This is a dummy PDF file for {entity} - {year_val} {report_def['display_name_part']} ({report_def['basis']})")
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
                'AIM Laboratories LLC', 'First Bio Lab of Illinois', 'Stat Labs', 'AMICO Dx LLC', 'Enviro Labs LLC',
                'First Bio Lab', 'AIM Laboratories LLC', 'First Bio Genetics LLC', 'Stat Labs',
                'Enviro Labs LLC', 'AMICO Dx LLC',
                'First Bio Lab', 'AIM Laboratories LLC', 'First Bio Lab of Illinois',
                'First Bio Genetics LLC', 'Enviro Labs LLC',
                'AIM Laboratories LLC',
                'First Bio Lab'
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
