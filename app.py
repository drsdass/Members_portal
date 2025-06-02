import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash
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
    'First Bio Genetics LLC',
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC',
    'AMICO Dx LLC',
    'Enviro Labs LLC',
    'Stat Labs'
])

# --- Users with Unfiltered Access (now specifically for 'admin' role) ---
# Admins get full access regardless of their 'entities' list.
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS']

# --- User Management (In-memory, with individual names as usernames and their roles) ---
# For Physician/Provider, the 'username' key will be an internal identifier,
# and 'email' will be the primary login credential.
# For Patient, 'username' is internal, 'patient_details' holds login and patient_id.
users = {
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Example BDM
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': [e for e in MASTER_ENTITIES if e != 'Stat Labs'], 'role': 'business_dev_manager'}, # Example BDM
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Example BDM
    # Physician/Provider example with email login
    'Andrew_Phys': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'physician_provider', 'email': 'andrew@example.com'},
    'AndrewS_Phys': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'physician_provider', 'email': 'andrews@example.com'},
    # Patient users now have specific details for login AND a patient_id
    'House_Patient': {'password_hash': generate_password_hash('password9'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'House', 'dob': '1980-05-15', 'ssn4': '1234', 'patient_id': 'PAT001'}},
    'PatientUser1': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'Doe', 'dob': '1990-01-01', 'ssn4': '5678', 'patient_id': 'PAT002'}}, # Dedicated Patient User
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx LLC'], 'role': 'business_dev_manager'}, # Example BDM
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'physician_provider', 'email': 'sonnya@example.com'}, # Example Physician/Provider
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Example Admin
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx LLC'], 'role': 'business_dev_manager'}, # Example BDM
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'PhysicianUser1': {'password_hash': generate_password_hash('physicianpass'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'email': 'physician1@example.com'}, # Dedicated Physician User
    # CORRECTED: SalesUser1 role changed from 'sales_marketing' to 'business_dev_manager'
    'SalesUser1': {'password_hash': generate_password_hash('salespass1'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'},
    'MarketingUser1': {'password_hash': generate_password_hash('marketpass1'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Assuming Marketing is also BDM
}

# --- Define Report Types by Role ---
REPORT_TYPES_BY_ROLE = {
    'admin': [
        {'value': 'financials', 'name': 'Financials Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'},
        {'value': 'patient_reports', 'name': 'Patient Specific Reports'}
    ],
    'physician_provider': [
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'patient_reports', 'name': 'Patient Specific Reports'}
    ],
    'patient': [
        {'value': 'patient_reports', 'name': 'Patient Specific Reports'}
    ],
    'business_dev_manager': [ # This role now includes the reports previously under 'sales_marketing'
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'}
    ]
}

# --- Financial Report Definitions (for generating entity-specific filenames and display names) ---
FINANCIAL_REPORT_DEFINITIONS = [
    {'display_name_part': 'Profit and Loss account', 'basis': 'Accrual Basis', 'file_suffix': '-Profit and Loss account - Accrual basis'},
    {'display_name_part': 'Profit and Loss account', 'basis': 'Cash Basis', 'file_suffix': '-Profit and Loss account - Cash Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Accrual Basis', 'file_suffix': '-Balance Sheet - Accrual Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Cash Basis', 'file_suffix': '-Balance Sheet - Cash Basis'},
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
    """Allows user to select their role."""
    if request.method == 'POST':
        selected_role = request.form.get('role')
        # Validate the new role names
        if selected_role in ['physician_provider', 'patient', 'business_dev_manager', 'admin']:
            session['selected_role'] = selected_role
            return redirect(url_for('login'))
        else:
            flash("Invalid role selected.", "error")
            return render_template('role_selection.html')
    return render_template('role_selection.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login after a role has been selected.
    """
    if 'selected_role' not in session:
        return redirect(url_for('select_role')) # Ensure a role is selected first

    selected_role = session['selected_role']
    error_message = None

    if request.method == 'POST':
        if selected_role == 'patient':
            # Patient login uses Last Name, DOB, SSN4
            last_name = request.form.get('last_name')
            dob = request.form.get('dob')
            ssn4 = request.form.get('ssn4')

            found_patient = False
            for username_key, user_info in users.items(): # Iterate through users to find patient
                if user_info.get('role') == 'patient':
                    patient_details = user_info.get('patient_details')
                    if patient_details and \
                       patient_details['last_name'].lower() == last_name.lower() and \
                       patient_details['dob'] == dob and \
                       patient_details['ssn4'] == ssn4:
                        session['username'] = username_key # Store the internal username for the session
                        session['patient_id'] = patient_details['patient_id'] # Store patient_id in session
                        found_patient = True
                        break
            
            if found_patient:
                return redirect(url_for('patient_results')) # Redirect patients to their specific results page
            else:
                error_message = 'Invalid patient details.'
        elif selected_role == 'physician_provider':
            # Physician/Provider login uses Email and Password
            email = request.form.get('email')
            password = request.form.get('password')
            
            found_physician = False
            for username_key, user_info in users.items(): # Iterate through users to find physician by email
                if user_info.get('role') == 'physician_provider' and user_info.get('email') and user_info['email'].lower() == email.lower():
                    if check_password_hash(user_info['password_hash'], password):
                        session['username'] = username_key # Store the internal username for the session
                        found_physician = True
                        break
            
            if found_physician:
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid email or password.'
        else:
            # Other roles (Business Dev Manager, Admin) use Username and Password
            username = request.form.get('username')
            password = request.form.get('password')
            
            user_info = users.get(username)

            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid username or password.'
    
    # For GET request or failed POST, render login form with appropriate fields
    return render_template('login.html', error=error_message, selected_role=selected_role)

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation
        if not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template('register_physician.html')
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register_physician.html')
        
        # Check if email already exists for a physician
        for username_key, user_info in users.items():
            if user_info.get('role') == 'physician_provider' and user_info.get('email') and user_info['email'].lower() == email.lower():
                flash("Email already registered. Please login or use a different email.", "error")
                return render_template('register_physician.html')
        
        # Register the new physician
        # Generate a unique username key (e.g., from email or a counter)
        # For simplicity, let's use a sanitized version of the email as the username key
        # In a real app, you'd use a UUID or auto-incrementing ID from a database.
        new_username_key = email.replace('@', '_').replace('.', '_') + "_phys"
        
        # Ensure the generated username key is unique (simple check for demo)
        while new_username_key in users:
            new_username_key += "_new" # Append to make it unique if collision occurs

        users[new_username_key] = {
            'password_hash': generate_password_hash(password),
            'entities': [], # Newly registered physicians start with no specific entities, can be assigned later
            'role': 'physician_provider',
            'email': email.lower()
        }
        
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register_physician.html')


@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role']

    # Patients are redirected to patient_results, so they shouldn't access this directly unless intended.
    # If a patient somehow lands here, redirect them.
    if user_role == 'patient':
        return redirect(url_for('patient_results'))

    user_authorized_entities = users[username]['entities']

    # Admins get all entities regardless of their specific list
    if user_role == 'admin':
        display_entities = MASTER_ENTITIES
    else:
        display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Get report types based on the user's role
    available_report_types = REPORT_TYPES_BY_ROLE.get(user_role, [])

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
    years = list(range(current_year - 2, current_year + 2))

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        selected_entity = request.form.get('entity_name')
        selected_month = request.form.get('month')
        selected_year = request.form.get('year')

        if not report_type:
            flash("Please select a report type.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years
            )
        
        if not selected_entity: # Entity selection is required for non-patient roles here
            flash("Please select an entity.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years
            )

        # Authorization check: Ensure the selected entity is one the user is authorized for
        # Admins bypass this specific entity authorization check
        if user_role != 'admin' and selected_entity and selected_entity not in user_authorized_entities:
            flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity.", "error")
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
        master_entities=display_entities,
        available_report_types=available_report_types,
        months=months,
        years=years
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    user_role = users[rep]['role']

    # If a patient somehow lands here, redirect them to their specific page
    if user_role == 'patient':
        return redirect(url_for('patient_results'))
    
    # Define months and years for dropdowns
    months = [
        {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
        {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
        {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
        {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
        {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
        {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'}
    ]
    current_year = datetime.datetime.now().year
    years = list(range(current_year - 2, current_year + 2))

    if request.method == 'POST':
        selected_entity = request.form.get('entity_name')
        report_type = request.form.get('report_type')
        selected_month = int(request.form.get('month')) if request.form.get('month') else None
        selected_year = int(request.form.get('year')) if request.form.get('year') else None

        session['selected_entity'] = selected_entity
        session['selected_month'] = selected_month
        session['selected_year'] = selected_year
        session['report_type'] = report_type
    else:
        selected_entity = session.get('selected_entity')
        report_type = session.get('report_type')
        selected_month = session.get('selected_month')
        selected_year = session.get('selected_year')

    # Re-evaluate user's authorized entities for display in dropdowns
    user_authorized_entities = users[rep]['entities']
    if user_role == 'admin':
        display_entities = MASTER_ENTITIES
    else:
        display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Authorization check for selected entity (admins bypass specific entity auth)
    if user_role != 'admin' and selected_entity and selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
             flash(f"You do not have any entities assigned to view reports. Please contact support.", "error")
             return render_template(
                'unauthorized.html',
                message=f"You do not have any entities assigned to view reports. Please contact support."
            )
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for.", "error")
        return render_template(
            'select_report.html',
            master_entities=display_entities,
            available_report_types=REPORT_TYPES_BY_ROLE.get(user_role, []),
            months=months,
            years=years
        )

    filtered_data = pd.DataFrame()

    # Data filtering logic
    if rep in UNFILTERED_ACCESS_USERS and user_role == 'admin': # Only admin with unfiltered access gets all data
        if not df.empty:
            filtered_data = df.copy()
        print(f"User {rep} (Admin) has unfiltered access. Displaying all data.")
    elif not df.empty and 'Entity' in df.columns:
        if selected_entity: # Only filter by entity if one is selected
            filtered_data = df[df['Entity'] == selected_entity].copy()
        else: # If no entity is selected (e.g., for some admin views)
            filtered_data = df.copy()

        if selected_month and selected_year and 'Date' in filtered_data.columns:
            if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
            
            filtered_data = filtered_data[
                (filtered_data['Date'].dt.month == selected_month) &
                (filtered_data['Date'].dt.year == selected_year)
            ]
        
        if report_type == 'monthly_bonus' and 'Username' in filtered_data.columns:
            normalized_username = rep.strip().lower()
            filtered_data['Username'] = filtered_data['Username'].astype(str)
            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            print(f"User {rep} viewing monthly bonus report. Filtered by 'Username' column.")
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    # Render templates based on report_type
    if report_type == 'financials':
        files_to_display = {}
        
        years_to_process = [selected_year] if selected_year else range(current_year - 2, current_year + 2)

        for year_val in years_to_process:
            year_reports = []
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                display_name = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}"
                filename = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath_check = os.path.join('static', filename)

                if os.path.exists(filepath_check):
                    year_reports.append({
                        'name': display_name,
                        'webViewLink': url_for('static', filename=filename)
                    })
            if year_reports:
                files_to_display[year_val] = year_reports

        return render_template(
            'dashboard.html',
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display,
            master_entities=display_entities,
            years=years,
            selected_year=selected_year,
            months=months
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            master_entities=display_entities,
            months=months,
            years=years,
            selected_month=selected_month,
            selected_year=selected_year
        )
    elif report_type == 'requisitions':
        return render_template(
            'generic_report.html',
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development. Filtered data rows: {len(filtered_data)}"
        )
    elif report_type == 'marketing_material':
        return render_template(
            'generic_report.html',
            report_title="Marketing Material Report",
            message=f"Marketing Material for {selected_entity} is under development."
        )
    elif report_type == 'patient_reports': # This is now handled by patient_results route
        return redirect(url_for('patient_results'))
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
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

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
                '2025-03-01', # New row for multi-user test
                '2025-01-10', '2025-01-20', '2025-03-05', '2025-04-12' # Patient specific data
            ],
            'Location': [
                'CENTRAL KENTUCKY SPINE SURGERY - TOX', 'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA',
                'HOPESS RESIDENTIAL TREATMENT', 'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
                'TEST LOCATION A', 'TEST LOCATION B', 'TEST LOCATION C', 'TEST LOCATION D',
                'OLD LOCATION X', 'OLD LOCATION Y',
                'NEW CLINIC Z', 'URGENT CARE A', 'HOSPITAL B',
                'HEALTH CENTER C', 'WELLNESS SPA D',
                'BETA TEST LOCATION',
                'SHARED PERFORMANCE CLINIC',
                'PATIENT LAB A', 'PATIENT LAB B', 'PATIENT LAB C', 'PATIENT LAB D' # Patient specific data
            ],
            'Reimbursement': [1.98, 150.49, 805.13, 2466.87, 76542.07,
                              500.00, 750.00, 120.00, 900.00,
                              300.00, 450.00,
                              600.00, 150.00, 2500.00,
                              350.00, 80.00,
                              38.85,
                              1200.00,
                              100.00, 200.00, 150.00, 250.00], # Patient specific data
            'COGS': [50.00, 151.64, 250.00, 1950.00, 30725.00,
                     200.00, 300.00, 50.00, 400.00,
                     100.00, 150.00,
                     250.00, 70.00, 1800.00,
                     120.00, 30.00,
                     25.00,
                     500.00,
                     20.00, 40.00, 30.00, 50.00], # Patient specific data
            'Net': [-48.02, -1.15, 555.13, 516.87, 45817.07,
                               300.00, 450.00, 70.00, 500.00,
                               200.00, 300.00,
                               350.00, 80.00, 700.00,
                               230.00, 50.00,
                               13.85,
                               700.00,
                               80.00, 160.00, 120.00, 200.00], # Patient specific data
            'Commission': [-14.40, -0.34, 166.53, 155.06, 13745.12,
                               90.00, 135.00, 21.00, 150.00,
                               60.00, 90.00,
                               105.00, 24.00, 210.00,
                               69.00, 15.00,
                               4.16,
                               210.00,
                               24.00, 48.00, 36.00, 60.00], # Patient specific data
            'Entity': [
                'AIM Laboratories LLC', 'First Bio Lab of Illinois', 'Stat Labs', 'AMICO Dx LLC', 'Enviro Labs LLC',
                'First Bio Lab', 'AIM Laboratories LLC', 'First Bio Genetics LLC', 'Stat Labs',
                'Enviro Labs LLC', 'AMICO Dx LLC',
                'First Bio Lab', 'AIM Laboratories LLC', 'First Bio Lab of Illinois',
                'First Bio Genetics LLC', 'Enviro Labs LLC',
                'AIM Laboratories LLC',
                'First Bio Lab',
                'First Bio Lab', 'First Bio Lab', 'First Bio Lab', 'First Bio Lab' # Patient specific data
            ],
            'Associated Rep Name': [
                'House', 'House', 'Sonny A', 'Jay M', 'Bob S',
                'Satish D', 'ACG', 'Melinda C', 'Mina K',
                'Vince O', 'Nick C',
                'Ashlie T', 'Omar', 'Darang T',
                'Andrew', 'Jay M',
                'Andrew S',
                'Andrew S, Melinda C',
                'N/A', 'N/A', 'N/A', 'N/A' # Patient specific data
            ],
            'Username': [
                'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew_Phys', 'JayM',
                'AndrewS_Phys',
                'AndrewS_Phys,MelindaC',
                'House_Patient', 'House_Patient', 'PatientUser1', 'PatientUser1' # Patient specific data
            ],
            'PatientID': [ # New column for patient filtering
                'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A',
                'N/A',
                'PAT001', 'PAT001', 'PAT002', 'PAT002' # Link to patient_id in users dict
            ]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv('data.csv', index=False)
        print("Created dummy data.csv for demonstration.")

    app.run(debug=True)
