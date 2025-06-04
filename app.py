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
    'First Bio Genetics LLC', # Updated based on file names
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC',   # Updated based on file names
    'AMICO Dx LLC',           # Updated based on file names
    'AMICO Dx', # Keeping this for now as it was in the original list, but actual files use LLC
    'Enviro Labs LLC',        # Updated based on file names
    'Stat Labs'
])

# --- Users with Unfiltered Access (for existing 'members' role) ---
UNFILTERED_ACCESS_USERS = ['AshlieT', 'MinaK', 'BobS', 'SatishD']

# --- User Management (In-memory, with individual names as usernames and their roles) ---
# NOTE: For 'patient' role, 'username' is not used for login, but 'last_name', 'dob', 'ssn4'
# For 'physician_provider', 'email' is used as the username.
users = {
    # Existing 'members' role users
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Changed to admin for full access
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Changed role
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Changed to admin
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': [e for e in MASTER_ENTITIES if e != 'Stat Labs'], 'role': 'business_dev_manager'}, # Changed role
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Changed to admin
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Changed role
    'Andrew': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'business_dev_manager'}, # Changed role
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'business_dev_manager'}, # Changed role
    'House': {'password_hash': generate_password_hash('password9'), 'entities': [], 'role': 'business_dev_manager'}, # Changed role
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx LLC'], 'role': 'business_dev_manager'}, # Changed role
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'business_dev_manager'}, # Changed role
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Changed role
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx LLC'], 'role': 'business_dev_manager'}, # Changed role
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'}, # Changed role
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Changed to admin

    # New roles and example users
    # Physician/Provider users (login with email)
    'dr.smith@example.com': {'password_hash': generate_password_hash('docpass'), 'entities': ['First Bio Lab', 'AIM Laboratories LLC'], 'role': 'physician_provider'},
    'dr.jones@example.com': {'password_hash': generate_password_hash('jonespass'), 'entities': ['First Bio Genetics LLC'], 'role': 'physician_provider'},

    # Patient users (login with last_name, dob, ssn4)
    'patient_doe': {'last_name': 'Doe', 'dob': '1990-01-15', 'ssn4_hash': generate_password_hash('1234'), 'patient_id': 'P001', 'role': 'patient'},
    'patient_smith': {'last_name': 'Smith', 'dob': '1985-05-20', 'ssn4_hash': generate_password_hash('5678'), 'patient_id': 'P002', 'role': 'patient'},

    # Business Development Manager (already covered by some existing users now, but explicitly here)
    'bdm_user': {'password_hash': generate_password_hash('bdm_pass'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'},

    # Admin user
    'admin_user': {'password_hash': generate_password_hash('admin_pass'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
}

# --- Define Report Types by Role ---
REPORT_TYPES_BY_ROLE = {
    'physician_provider': [
        {'value': 'patient_results', 'name': 'Patient Results'},
        {'value': 'financials', 'name': 'Financials Report'} # For their own practice financials
    ],
    'patient': [
        {'value': 'patient_results', 'name': 'My Test Results'}
    ],
    'business_dev_manager': [
        {'value': 'financials', 'name': 'Financials Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'}
    ],
    'admin': [
        {'value': 'financials', 'name': 'Financials Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'},
        {'value': 'user_management', 'name': 'User Management'} # Placeholder for future
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

patient_df = pd.DataFrame() # Initialize patient data
try:
    patient_df = pd.read_csv('patient_data.csv', parse_dates=['DateOfService', 'PatientDOB'])
    print("patient_data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: patient_data.csv not found. Dummy patient data will be created.")
except Exception as e:
    print(f"An error occurred while loading patient_data.csv: {e}")


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
        # Validate the selected role against the allowed roles
        allowed_roles = [
            'physician_provider', 'patient',
            'business_dev_manager', 'admin'
        ]
        if selected_role in allowed_roles:
            session['selected_role'] = selected_role
            flash(f"Role '{selected_role.replace('_', ' ').title()}' selected. Please log in.", 'success')
            return redirect(url_for('login'))
        else:
            flash("Invalid role selected. Please try again.", 'error')
            return render_template('role_selection.html', error="Invalid role selected.")
    return render_template('role_selection.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login based on the selected role.
    """
    if 'selected_role' not in session:
        flash("Please select a role first.", 'error')
        return redirect(url_for('select_role'))

    selected_role = session['selected_role']

    if request.method == 'POST':
        if selected_role == 'patient':
            last_name = request.form.get('last_name')
            dob = request.form.get('dob') # YYYY-MM-DD
            ssn4 = request.form.get('ssn4')

            # Find patient by last name and DOB
            # Note: In a real app, you'd query a database. Here, we iterate through dummy users.
            found_user = None
            for user_key, user_info in users.items():
                if user_info.get('role') == 'patient' and \
                   user_info.get('last_name', '').lower() == last_name.lower() and \
                   user_info.get('dob') == dob:
                    # Check SSN4 hash
                    if check_password_hash(user_info['ssn4_hash'], ssn4):
                        found_user = user_key
                        break
            
            if found_user:
                session['username'] = found_user # Store the dummy username (e.g., 'patient_doe')
                session['user_role'] = 'patient'
                session['patient_id'] = users[found_user]['patient_id'] # Store patient_id
                session['patient_name'] = f"{last_name}" # Store patient's last name for display
                flash(f"Welcome, {last_name}! You are logged in as a Patient.", 'success')
                return redirect(url_for('patient_results')) # Redirect patients to their specific results page
            else:
                flash('Invalid login credentials for Patient.', 'error')
                return render_template('login.html', selected_role=selected_role, error='Invalid login credentials.'), 401

        elif selected_role == 'physician_provider':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user_info = users.get(email)
            if user_info and user_info.get('role') == 'physician_provider' and check_password_hash(user_info['password_hash'], password):
                session['username'] = email # Store email as username for physicians
                session['user_role'] = 'physician_provider'
                flash(f"Welcome, {email}! You are logged in as a Physician/Provider.", 'success')
                return redirect(url_for('select_report'))
            else:
                flash('Invalid email or password for Physician/Provider.', 'error')
                return render_template('login.html', selected_role=selected_role, error='Invalid email or password.'), 401
        
        else: # For 'business_dev_manager' and 'admin' roles
            username = request.form.get('username')
            password = request.form.get('password')
            
            user_info = users.get(username)
            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                session['user_role'] = user_info['role']
                flash(f"Welcome, {username}! You are logged in as an {user_info['role'].replace('_', ' ').title()}.", 'success')
                return redirect(url_for('select_report'))
            else:
                flash(f'Invalid username or password for {selected_role.replace("_", " ").title()}.', 'error')
                return render_template('login.html', selected_role=selected_role, error='Invalid username or password.'), 401
    
    return render_template('login.html', selected_role=selected_role)

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords do not match.", 'error')
            return render_template('register_physician.html'), 400
        
        if email in users:
            flash("Email already registered. Please login or use a different email.", 'error')
            return render_template('register_physician.html'), 409

        # Register new physician
        users[email] = {
            'password_hash': generate_password_hash(password),
            'entities': [], # Newly registered physicians start with no entities, admin assigns them later
            'role': 'physician_provider'
        }
        flash("Registration successful! You can now log in.", 'success')
        return redirect(url_for('login'))
    return render_template('register_physician.html')


@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_role = session['user_role'] # Get the user's role from session
    
    # Redirect patient role directly to patient_results
    if user_role == 'patient':
        return redirect(url_for('patient_results'))

    user_authorized_entities = users[username]['entities']

    # Filter master entities based on the user's authorized entities
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

    selected_entity = session.get('selected_entity')
    selected_month = session.get('selected_month')
    selected_year = session.get('selected_year')
    selected_report_type = session.get('report_type')

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        selected_entity_from_form = request.form.get('entity_name') # Use a different variable name
        selected_month_from_form = request.form.get('month')
        selected_year_from_form = request.form.get('year')

        # For non-patient roles, entity selection is required
        if not selected_entity_from_form and user_role != 'patient':
            flash("Please select an entity.", 'error')
            return render_template(
                'select_report.html',
                current_username=username,
                user_role=user_role,
                user_authorized_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years,
                selected_entity=selected_entity, # Pass back previous selection
                selected_report_type=selected_report_type # Pass back previous selection
            )

        if not report_type:
            flash("Please select a report type.", 'error')
            return render_template(
                'select_report.html',
                current_username=username,
                user_role=user_role,
                user_authorized_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years,
                selected_entity=selected_entity,
                selected_report_type=selected_report_type
            )

        # Authorization check for selected entity (only if an entity was selected)
        if selected_entity_from_form and selected_entity_from_form not in user_authorized_entities:
            flash(f"You are not authorized to view reports for '{selected_entity_from_form}'. Please select an authorized entity.", 'error')
            return render_template(
                'select_report.html',
                current_username=username,
                user_role=user_role,
                user_authorized_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years,
                selected_entity=selected_entity,
                selected_report_type=selected_report_type
            )
        
        # Store selections in session
        session['report_type'] = report_type
        session['selected_entity'] = selected_entity_from_form
        session['selected_month'] = int(selected_month_from_form) if selected_month_from_form else None
        session['selected_year'] = int(selected_year_from_form) if selected_year_from_form else None
        
        return redirect(url_for('dashboard'))
    
    return render_template(
        'select_report.html',
        current_username=username,
        user_role=user_role,
        user_authorized_entities=display_entities, # Pass filtered entities to template
        available_report_types=available_report_types, # Pass filtered report types to template
        months=months,
        years=years,
        selected_entity=selected_entity,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_report_type=selected_report_type
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    user_role = session['user_role']
    
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

    # Authorization check for selected entity (not applicable for patient role here)
    user_authorized_entities = users[rep]['entities'] if user_role != 'patient' else [] # Patients don't have 'entities' in this context
    if user_role != 'patient' and selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
             flash(f"You do not have any entities assigned to view reports. Please contact support.", 'error')
             return render_template(
                'unauthorized.html',
                message=f"You do not have any entities assigned to view reports. Please contact support."
            )
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for.", 'error')
        return redirect(url_for('select_report')) # Redirect back to selection if not authorized for entity

    filtered_data = pd.DataFrame()

    # Data filtering logic
    if report_type == 'monthly_bonus':
        if not df.empty:
            filtered_data = df.copy()

            # Filter by selected entity if applicable (not for unfiltered access users)
            if rep not in UNFILTERED_ACCESS_USERS and 'Entity' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['Entity'] == selected_entity].copy()

            # Filter by month and year
            if selected_month and selected_year and 'Date' in filtered_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                    filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
                
                filtered_data = filtered_data[
                    (filtered_data['Date'].dt.month == selected_month) &
                    (filtered_data['Date'].dt.year == selected_year)
                ]
            
            # Filter by 'Username' column for non-unfiltered users
            if rep not in UNFILTERED_ACCESS_USERS and 'Username' in filtered_data.columns:
                normalized_username = rep.strip().lower()
                filtered_data['Username'] = filtered_data['Username'].astype(str)
                regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
                filtered_data = filtered_data[
                    filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
                ]
                print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
        else:
            print(f"Warning: data.csv is empty. Cannot filter for monthly bonus report.")

        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            current_username=rep,
            user_role=user_role,
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities],
            months=months,
            years=years,
            selected_month=selected_month,
            selected_year=selected_year
        )

    elif report_type == 'financials':
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
            current_username=rep,
            user_role=user_role,
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Only authorized entities for this user
            years=years, # Years dropdown for financials
            selected_year=selected_year,
            months=months # Pass months for display in dashboard if needed
        )
    
    elif report_type == 'requisitions':
        return render_template(
            'generic_report.html',
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development.",
            current_username=rep,
            user_role=user_role
        )
    elif report_type == 'marketing_material':
        return render_template(
            'generic_report.html',
            report_title="Marketing Material Report",
            message=f"Marketing Material for {selected_entity} is under development.",
            current_username=rep,
            user_role=user_role
        )
    elif report_type == 'user_management':
        return render_template(
            'generic_report.html',
            report_title="User Management",
            message=f"User Management features are under development.",
            current_username=rep,
            user_role=user_role
        )
    else:
        # Fallback if no report type is selected or recognized
        flash("Please select a valid report type.", 'error')
        return redirect(url_for('select_report'))


@app.route('/patient_results', methods=['GET'])
def patient_results():
    if 'username' not in session or session.get('user_role') != 'patient':
        flash("You must be logged in as a patient to view this page.", 'error')
        return redirect(url_for('login'))

    patient_id = session.get('patient_id')
    patient_name = session.get('patient_name')

    results_by_dos = {}
    if not patient_df.empty and 'PatientID' in patient_df.columns:
        patient_specific_results = patient_df[patient_df['PatientID'] == patient_id].copy()
        
        if not patient_specific_results.empty:
            # Sort by DateOfService
            patient_specific_results = patient_specific_results.sort_values(by='DateOfService', ascending=False)

            for index, row in patient_specific_results.iterrows():
                dos = row['DateOfService'].strftime('%Y-%m-%d')
                report_name = row['ReportName']
                report_file = row['ReportFile'] # Assuming this is the filename in static

                if dos not in results_by_dos:
                    results_by_dos[dos] = []
                
                # Check if the report file exists
                filepath_check = os.path.join('static', report_file)
                if os.path.exists(filepath_check):
                    results_by_dos[dos].append({
                        'name': report_name,
                        'webViewLink': url_for('static', filename=report_file)
                    })
                else:
                    print(f"Warning: Patient report file not found: {filepath_check}")
                    results_by_dos[dos].append({
                        'name': f"{report_name} (File Missing)",
                        'webViewLink': "#" # Or a link to a placeholder/error page
                    })
        else:
            flash("No test results found for your account.", 'info')

    return render_template(
        'patient_results.html',
        patient_name=patient_name,
        results_by_dos=results_by_dos,
        current_username=session['username'], # Pass for base_dashboard
        user_role=session['user_role'] # Pass for base_dashboard
    )


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('select_role')) # Redirect to role selection after logout

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

    # Create dummy patient_data.csv if it doesn't exist
    if not os.path.exists('patient_data.csv'):
        patient_dummy_data = {
            'PatientID': ['P001', 'P001', 'P002', 'P001'],
            'PatientLastName': ['Doe', 'Doe', 'Smith', 'Doe'],
            'PatientDOB': ['1990-01-15', '1990-01-15', '1985-05-20', '1990-01-15'],
            'DateOfService': ['2024-05-01', '2024-04-10', '2024-05-05', '2024-03-20'],
            'ReportName': ['Comprehensive Metabolic Panel', 'Complete Blood Count', 'Thyroid Panel', 'Urinalysis'],
            'ReportFile': ['patient_report_P001_CMP_20240501.pdf', 'patient_report_P001_CBC_20240410.pdf', 'patient_report_P002_Thyroid_20240505.pdf', 'patient_report_P001_Urinalysis_20240320.pdf']
        }
        patient_dummy_df = pd.DataFrame(patient_dummy_data)
        patient_dummy_df.to_csv('patient_data.csv', index=False)
        print("Created dummy patient_data.csv for demonstration.")

        # Create dummy patient PDF files
        for index, row in patient_dummy_df.iterrows():
            filepath = os.path.join('static', row['ReportFile'])
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"This is a dummy patient report for {row['PatientLastName']} (ID: {row['PatientID']}) - {row['ReportName']} on {row['DateOfService']}")
                print(f"Created dummy patient report file: {filepath}")

    app.run(debug=True)
