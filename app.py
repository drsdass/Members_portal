
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

# --- Master List of All Entities ---
MASTER_ENTITIES = sorted([
    'First Bio Lab',
    'First Bio Genetics LLC',
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC',
    'AMICO Dx LLC',
    'Enviro Labs LLC',
    'Stat Labs'
])

# --- Users with Unfiltered Access (for monthly bonus reports - remains unchanged) ---
# These specific admins will still get all data for bonus reports regardless of 'entities' filter.
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS']

# --- User Management (In-memory, with granular entity assignments for all roles) ---
users = {
    # Full Access Admins (those explicitly confirmed for full access in previous turns)
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Confirmed full access
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Confirmed full access
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': MASTER_ENTITIES, 'role': 'admin'}, # Confirmed full access

    # Admins with Specific Limited Access (based on your latest instructions)
    'AghaA': {'password_hash': generate_password_hash('agapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'Wenjun': {'password_hash': generate_password_hash('wenpass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'AndreaM': {'password_hash': generate_password_hash('andreapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'BenM': {'password_hash': generate_password_hash('benpass'), 'entities': ['Enviro Labs LLC'], 'role': 'admin'},
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin', 'email': 'sonnya@example.com'}, # 'SonnyN' mapped to 'SonnyA'
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx LLC'], 'role': 'admin'},
    'BobSilverang': {'password_hash': generate_password_hash('silverpass'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'Enviro Labs LLC'], 'role': 'admin'},
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx LLC'], 'role': 'admin'},
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'admin', 'email': 'andrews@example.com'},

    # Existing users not explicitly mentioned in the latest list (retain their existing roles/access)
    'Andrew_Phys': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'physician_provider', 'email': 'andrew@example.com'},
    'PhysicianUser1': {'password_hash': generate_password_hash('physicianpass'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'email': 'physician1@example.com'},

    # Patient users (no change for this set, but PatientID column removed from data.csv)
    'House_Patient': {'password_hash': generate_password_hash('password9'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'House', 'dob': '1980-05-15', 'ssn4': '1234', 'patient_id': 'PAT001'}},
    'PatientUser1': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'Doe', 'dob': '1990-01-01', 'ssn4': '5678', 'patient_id': 'PAT002'}},
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
    'business_dev_manager': [
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'}
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


# Global lists for months and years (for dropdowns)
MONTHS = [
    {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
    {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
    {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
    {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
    {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
    {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'}
]
CURRENT_APP_YEAR = datetime.datetime.now().year
YEARS = list(range(CURRENT_APP_YEAR - 2, CURRENT_APP_YEAR + 2)) # e.g., 2023, 2024, 2025, 2026


# --- Data Loading (Optimized: Load once at app startup) ---
df = pd.DataFrame() # Initialize as empty to avoid error if file not found
try:
    # Ensure 'Date' column is parsed as datetime objects upon loading
    df = pd.read_csv('data.csv', parse_dates=['Date'])
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py. Dummy data will be created.")
except Exception as e:
    print(f"An error occurred while loading data.csv: {e}")


# --- Context Processor to inject global data into all templates ---
@app.context_processor
def inject_global_data():
    if 'username' in session:
        username = session['username']
        user_info = users.get(username)
        if user_info:
            user_role = user_info['role']
            user_authorized_entities = user_info['entities']
            available_report_types = REPORT_TYPES_BY_ROLE.get(user_role, [])
            return dict(
                user_role=user_role,
                user_authorized_entities=user_authorized_entities,
                MASTER_ENTITIES=MASTER_ENTITIES,
                available_report_types=available_report_types,
                months=MONTHS,
                years=YEARS,
                current_app_year=CURRENT_APP_YEAR,
                current_username=username # Pass current username for display in base template
            )
    return dict(
        MASTER_ENTITIES=MASTER_ENTITIES,
        months=MONTHS,
        years=YEARS,
        current_app_year=CURRENT_APP_YEAR,
        current_username=None # No user logged in
    )

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
            flash("Invalid role selected.", "error") # Flash error message
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
            for username_key, user_info in users.items():
                if user_info.get('role') == 'patient':
                    patient_details = user_info.get('patient_details')
                    if patient_details and \
                       patient_details['last_name'].lower() == last_name.lower() and \
                       patient_details['dob'] == dob and \
                       patient_details['ssn4'] == ssn4:
                        session['username'] = username_key
                        session['patient_id'] = patient_details['patient_id']
                        session['user_role'] = user_info['role'] # Store role in session
                        found_patient = True
                        break

            if found_patient:
                return redirect(url_for('patient_results'))
            else:
                error_message = 'Invalid patient details.'
        elif selected_role == 'physician_provider':
            # Physician/Provider login uses Email and Password
            email = request.form.get('email')
            password = request.form.get('password')

            found_physician = False
            for username_key, user_info in users.items():
                if user_info.get('role') == 'physician_provider' and user_info.get('email') and user_info['email'].lower() == email.lower():
                    if check_password_hash(user_info['password_hash'], password):
                        session['username'] = username_key
                        session['user_role'] = user_info['role'] # Store role in session
                        found_physician = True
                        break

            if found_physician:
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid email or password.'
        else:
            # All other roles (admin, business_dev_manager) use Username and Password
            username = request.form.get('username')
            password = request.form.get('password')

            user_info = users.get(username)

            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                session['user_role'] = user_info['role'] # Store role in session
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid username or password.'

    return render_template('login.html', error=error_message, selected_role=selected_role)

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template('register_physician.html')

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template('register_physician.html')

        for username_key, user_info in users.items():
            if user_info.get('role') == 'physician_provider' and user_info.get('email') and user_info['email'].lower() == email.lower():
                flash("Email already registered. Please login or use a different email.", "error")
                return render_template('register_physician.html')

        new_username_key = email.replace('@', '_').replace('.', '_') + "_phys"
        while new_username_key in users:
            new_username_key += "_new"

        users[new_username_key] = {
            'password_hash': generate_password_hash(password),
            'entities': [], # Newly registered physicians start with no specific entities, can be assigned later
            'role': 'physician_provider',
            'email': email.lower()
        }

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('register_physician.html')

@app.route('/patient_results')
def patient_results():
    if 'username' not in session or users[session['username']]['role'] != 'patient':
        flash("Access denied. Please log in as a patient.", "error")
        return redirect(url_for('login'))

    patient_username = session['username']
    patient_id = session.get('patient_id')
    patient_last_name = users[patient_username]['patient_details']['last_name']

    # Note: PatientID column was removed from data.csv, this logic relies on it.
    # It will need to be re-evaluated or adapted if PatientID is truly removed from data.csv.
    if df.empty or 'Date' not in df.columns: # Removed 'PatientID' check here
        flash("Patient data is not available or incorrectly structured. Please contact support.", "error")
        return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos={})

    # Filtering by PatientID might fail if the column is entirely removed from df.
    # This assumes 'PatientID' is still conceptually available or derivable from other columns.
    patient_data = df[df['Username'].str.contains(patient_username, na=False)].copy() # Filter by username for now

    if patient_data.empty:
        return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos={}, message="No results found for your patient ID.")

    if not pd.api.types.is_datetime64_any_dtype(patient_data['Date']):
        patient_data['Date'] = pd.to_datetime(patient_data['Date'])

    patient_data = patient_data.sort_values(by='Date', ascending=False)

    results_by_dos = {}
    for index, row in patient_data.iterrows():
        dos = row['Date'].strftime('%Y-%m-%d')
        if dos not in results_by_dos:
            results_by_dos[dos] = []

        report_name = f"Lab Result - {row['Location']} - {dos}"
        # Dummy PDF filename generation - needs PatientID if actual file naming depends on it.
        # For now, let's use a generic ID if PatientID is not in data.
        current_pid = row.get('PatientID', 'GenericPatientID') # Use PatientID if available, else generic
        dummy_pdf_filename = f"Patient_{current_pid}_DOS_{dos}_Report_{index}.pdf"

        results_by_dos[dos].append({
            'name': report_name,
            'webViewLink': url_for('static', filename=dummy_pdf_filename)
        })
        filepath = os.path.join('static', dummy_pdf_filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file for Patient {current_pid}, DOS {dos}, Result {index}.")
            print(f"Created dummy patient result file: {filepath}")

    return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos=results_by_dos)


@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role']
    user_role = users[username]['role'] # Get the user's role
    user_authorized_entities = users[username]['entities']

    # Filter master entities based on the user's authorized entities
    # This ensures the dropdown only shows entities the user can access
    display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Handle direct links from sidebar (GET request with query parameters)
    if request.method == 'GET':
        pre_selected_report_type = request.args.get('report_type')
        pre_selected_entity = request.args.get('entity')
        pre_selected_month = request.args.get('month')
        pre_selected_year = request.args.get('year')

        if pre_selected_report_type:
            session['report_type'] = pre_selected_report_type
            # If an entity is pre-selected or already in session, use it. Otherwise, user must select.
            if pre_selected_entity:
                session['selected_entity'] = pre_selected_entity
            elif 'selected_entity' not in session and user_authorized_entities:
                # If no entity selected yet, and user has authorized entities, pick the first one as default
                session['selected_entity'] = user_authorized_entities[0]
            
            session['selected_month'] = int(pre_selected_month) if pre_selected_month else None
            session['selected_year'] = int(pre_selected_year) if pre_selected_year else None
            
            # Redirect to the appropriate dashboard/report page if all necessary info is present
            if pre_selected_report_type == 'patient_reports' and user_role == 'patient':
                return redirect(url_for('patient_results'))
            elif session.get('selected_entity'): # Ensure an entity is selected for other reports
                return redirect(url_for('dashboard'))
            else:
                # If report type is selected but no entity (and needed), stay on select_report
                flash("Please select an entity for this report.", "error")
                return render_template(
                    'select_report.html',
                    master_entities=display_entities,
                    selected_entity=session.get('selected_entity'), # Pass selected_entity back to template
                    selected_report_type=session.get('report_type'), # Pass selected_report_type back to template
                    selected_month=session.get('selected_month'),
                    selected_year=session.get('selected_year')
                )

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
            flash("Please select both a report type and an entity.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                selected_entity=selected_entity,
                selected_report_type=report_type,
                master_entities=display_entities, # Use filtered entities here
                available_report_types=available_report_types, # Pass filtered report types
                months=months,
                years=years,
                selected_entity=selected_entity, # Retain selection on error
                selected_report_type=report_type, # Retain selection on error
                selected_month=selected_month,
                selected_year=selected_year
            )
        

        # Authorization check: Ensure the selected entity is one the user is authorized for
        if selected_entity not in user_authorized_entities:
            if not user_authorized_entities:
                flash("You do not have any entities assigned to view reports. Please contact support.", "error")
                return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
            
            flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                selected_entity=selected_entity,
                selected_report_type=report_type,
                available_report_types=available_report_types,
                months=months,
                years=years,
                selected_entity=selected_entity, # Retain selection on error
                selected_report_type=report_type, # Retain selection on error
                selected_month=selected_month,
                selected_year=selected_year
            )

        # Store selections in session
        session['report_type'] = report_type
        session['selected_entity'] = selected_entity
        session['selected_month'] = int(selected_month) if selected_month else None
        session['selected_year'] = int(selected_year) if selected_year else None

        if report_type == 'patient_reports' and user_role == 'patient':
            return redirect(url_for('patient_results'))
        else:
            return redirect(url_for('dashboard'))

    # For initial GET request or after an error
    return render_template(
        'select_report.html',
        master_entities=display_entities,
        master_entities=display_entities, # Pass filtered entities to template
        available_report_types=available_report_types, # Pass filtered report types to template
        months=months,
        years=years,
        selected_entity=session.get('selected_entity'), # Pre-select if already in session
        selected_report_type=session.get('report_type'), # Pre-select if already in session
        selected_month=session.get('selected_month'),
        selected_year=session.get('selected_year')
    )

@app.route('/dashboard', methods=['GET', 'POST'])
@app.route('/dashboard', methods=['GET', 'POST']) # Allow POST requests to dashboard
def dashboard():
    if 'username' not in session:
        flash("Access denied. Please log in.", "error")
        return redirect(url_for('login'))

    rep = session['username']
    user_role = users[rep]['role']

    # Get selections from session (or from POST request if coming from a form on dashboard/monthly_bonus)
    # Define months and years for dropdowns (needed for dashboard.html and monthly_bonus.html)
    months = MONTHS # Use the global MONTHS list
    years = YEARS   # Use the global YEARS list
    current_app_year = CURRENT_APP_YEAR # Use the global CURRENT_APP_YEAR

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

    # Ensure an entity is selected for non-patient reports
    if report_type != 'patient_reports' and not selected_entity:
        flash("Please select an entity to view this report.", "error")
        return redirect(url_for('select_report'))

    # Authorization check for selected entity
    user_authorized_entities = users[rep]['entities']
    
    if selected_entity and selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
             flash("You do not have any entities assigned to view reports. Please contact support.", "error")
             return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity.", "error")
        return redirect(url_for('select_report')) # Redirect back to selection page with error


    filtered_data = pd.DataFrame()

    if rep in UNFILTERED_ACCESS_USERS:
        if not df.empty:
            filtered_data = df.copy()
        print(f"User {rep} has unfiltered access. Displaying all data.")
    elif not df.empty and 'Entity' in df.columns:
        if selected_entity:
            filtered_data = df[df['Entity'] == selected_entity].copy()
        else:
            filtered_data = df.copy() # Should not happen if selected_entity is validated above
    try:
        # Check if the current user has unfiltered access
        if rep in UNFILTERED_ACCESS_USERS:
            if not df.empty:
                filtered_data = df.copy() # Provide a copy of the entire DataFrame
            print(f"User {rep} has unfiltered access. Displaying all data.")
        elif not df.empty and 'Entity' in df.columns:
            # Existing filtering logic for other users
            if selected_entity:
                filtered_data = df[df['Entity'] == selected_entity].copy()
            else:
                # This case should ideally not be reached if validation in select_report is robust
                filtered_data = df.copy() 
            
            print(f"Initial filtered data for {selected_entity}:\n{filtered_data.head()}")

        if selected_month and selected_year and 'Date' in filtered_data.columns:
            if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
            if selected_month and selected_year and 'Date' in filtered_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                    filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
                
                # Apply date filter
                filtered_data = filtered_data[
                    (filtered_data['Date'].dt.month == selected_month) &
                    (filtered_data['Date'].dt.year == selected_year)
                ]
                print(f"Data after month/year filter ({selected_month}/{selected_year}):\n{filtered_data.head()}")

            filtered_data = filtered_data[
                (filtered_data['Date'].dt.month == selected_month) &
                (filtered_data['Date'].dt.year == selected_year)
            ]
        
        # --- Date Formatting for Display ---
        if 'Date' in filtered_data.columns and pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
            filtered_data['Date'] = filtered_data['Date'].dt.strftime('%B %Y') # e.g., 'April 2025'
        # --- End Date Formatting ---

        if report_type == 'monthly_bonus' and 'Username' in filtered_data.columns:
            normalized_username = rep.strip().lower()
            filtered_data['Username'] = filtered_data['Username'].astype(str)
            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")
            # --- Date Formatting for Display (applies to all filtered_data before specific report type logic) ---
            if 'Date' in filtered_data.columns and pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                # Only format if the column exists and is datetime type
                # This line could cause an issue if filtered_data is empty and 'Date' column is not datetime.
                # However, the `is_datetime64_any_dtype` check should prevent that.
                filtered_data['Date'] = filtered_data['Date'].dt.strftime('%B %Y') # e.g., 'April 2025'
            # --- End Date Formatting ---

            # NEW FILTERING FOR MONTHLY BONUS REPORTS: Filter by 'Username' column for non-unfiltered users
            if report_type == 'monthly_bonus' and 'Username' in filtered_data.columns:
                normalized_username = rep.strip().lower()
                
                # Ensure 'Username' column is treated as string for .str methods
                filtered_data['Username'] = filtered_data['Username'].astype(str)

                # Updated logic: Check if the normalized_username is contained within the (potentially comma-separated) Username string
                # Using regex for word boundaries to avoid partial matches (e.g., 'and' matching 'andrewS')
                regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
                filtered_data = filtered_data[
                    filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
                ]
                print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column. Final data count: {len(filtered_data)}")
        else:
            print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")
            flash("Data is not available or incorrectly structured. Please contact support.", "error")

    except Exception as e:
        print(f"An unexpected error occurred during data filtering: {e}")
        flash(f"An error occurred while processing your report: {e}", "error")
        return redirect(url_for('select_report')) # Redirect to selection page on error

    # Define financial files structure
    financial_files_data = {
        2023: [
            {'name': '2023 Profit and Loss account - Accrual Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2023 - Accrual Basis.pdf'},
            {'name': '2023 Profit and Loss account - Cash Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2023 - Cash Basis.pdf'},
            {'name': '2023 Balance Sheet - Accrual Basis', 'filename': 'First Bio Lab - Balance Sheet - 2023 - Accrual Basis.pdf'},
            {'name': '2023 Balance Sheet - Cash Basis', 'filename': 'First Bio Lab - Balance Sheet - 2023 - Cash Basis.pdf'},
            # Add more 2023 reports if needed
        ],
        2024: [
            {'name': '2024 Profit and Loss account - Accrual Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2024 - Accrual Basis.pdf'},
            {'name': '2024 Profit and Loss account - Cash Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2024 - Cash Basis.pdf'},
            {'name': '2024 Balance Sheet - Accrual Basis', 'filename': 'First Bio Lab - Balance Sheet - 2024 - Accrual Basis.pdf'},
            {'name': '2024 Balance Sheet - Cash Basis', 'filename': 'First Bio Lab - Balance Sheet - 2024 - Cash Basis.pdf'},
            # Add more 2024 reports if needed
        ],
        2025: [
            {'name': '2025 Profit and Loss account - Accrual Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2025 - Accrual Basis.pdf'},
            {'name': '2025 Profit and Loss account - Cash Basis', 'filename': 'First Bio Lab - Profit and Loss account - 2025 - Cash Basis.pdf'},
            {'name': '2025 Balance Sheet - Accrual Basis', 'filename': 'First Bio Lab - Balance Sheet - 2025 - Accrual Basis.pdf'},
            {'name': '2025 Balance Sheet - Cash Basis', 'filename': 'First Bio Lab - Balance Sheet - 2025 - Cash Basis.pdf'},
            {'name': '2025 YTD Management Report - Cash Basis', 'filename': 'First Bio Lab - YTD Management Report - 2025 - Cash Basis.pdf'}
        ]
    }

    if report_type == 'financials':
        files_to_display = {}

        years_to_process = [selected_year] if selected_year else range(CURRENT_APP_YEAR - 2, CURRENT_APP_YEAR + 2)

        for year_val in years_to_process:
            year_reports = []
            # Iterate through FINANCIAL_REPORT_DEFINITIONS to find matching files for the selected entity
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                filename_to_create = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath_check = os.path.join('static', filename_to_create)
                # Construct the filename based on the selected entity and report definition
                filename_to_find = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath_check = os.path.join('static', filename_to_find)

                if os.path.exists(filepath_check):
                    year_reports.append({
                        'name': f"{report_def['display_name_part']} - {year_val} - {report_def['basis']}",
                        'webViewLink': url_for('static', filename=filename_to_create)
                        'webViewLink': url_for('static', filename=filename_to_find)
                    })
            if year_reports:
                files_to_display[year_val] = year_reports

        return render_template(
            'dashboard.html',
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display,
            data=filtered_data.to_dict(orient='records') # Pass filtered_data for the table
            files=files_to_display, # Pass the structured files data
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Only authorized entities for this user
            years=YEARS, # Years dropdown for financials
            selected_year=selected_year,
            months=MONTHS # Pass months for display in dashboard if needed
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            master_entities=[entity for entity in MASTER_ENTITIES if entity in user_authorized_entities], # Only authorized entities for this user
            months=MONTHS,
            years=YEARS,
            selected_month=selected_month,
            selected_year=selected_year
        )
    # NEW: Handle 'requisitions' and 'marketing_material'
    elif report_type == 'requisitions':
        # You would fetch or generate data/files relevant to requisitions here
        # For now, let's return a simple placeholder page or redirect
        return render_template(
            'generic_report.html',
            'generic_report.html', # Create a generic_report.html template for these
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development."
        )
    elif report_type == 'marketing_material':
        # You would fetch or generate data/files relevant to marketing material here
        return render_template(
            'generic_report.html',
            'generic_report.html', # Create a generic_report.html template for these
            report_title="Marketing Material Report",
            message=f"Marketing Material for {selected_entity} is under development."
        )
    elif report_type == 'patient_reports':
        # This case should ideally be handled by redirecting to patient_results directly from select_report
        # But as a fallback, if somehow reached here, redirect
        return redirect(url_for('patient_results'))
    else:
        flash("Invalid report type selected.", "error")
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
        for entity in MASTER_ENTITIES: # Loop through all master entities
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

    # Create dummy PDF files for patient results
    dummy_patient_ids = [details['patient_id'] for user, details in users.items() if details.get('role') == 'patient' and 'patient_details' in details]
    dummy_locations_for_patients = ['Main Lab', 'Satellite Clinic', 'Remote Testing Site']
    # Initialize results_by_dos outside the loop if it's meant to accumulate across multiple runs or be global
    results_by_dos_for_dummy_creation = [] 
    if dummy_patient_ids:
        for pid in dummy_patient_ids:
            for i in range(1, 4): # Create a few reports per patient
                # Ensure date is valid for dummy data
                report_date = (datetime.date(2025, 1, 1) + datetime.timedelta(days=i*10)).strftime('%Y-%m-%d')
                location = dummy_locations_for_patients[i % len(dummy_locations_for_patients)]
                dummy_pdf_filename = f"Patient_{pid}_DOS_{report_date}_Report_{i}.pdf"

                results_by_dos_for_dummy_creation.append({ # Use the local list for dummy creation
                    'name': f"Lab Result - {location} - {report_date}",
                    'webViewLink': url_for('static', filename=dummy_pdf_filename)
                })

                filepath = os.path.join('static', dummy_pdf_filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"This is a dummy PDF file for Patient {pid}, DOS {report_date}, Result {i}.")
                    print(f"Created dummy patient result file: {filepath}")


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
                'Andrew', 'JayM', # Matches JayM login username
                'AndrewS', # Matches AndrewS login username
                'AndrewS,MelindaC' # Allows both AndrewS and MelindaC to see this line
            ]
        }
    pd.DataFrame(dummy_data).to_csv('data.csv', index=False)
    app.run(debug=True)
