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
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS', 'NickT',]

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
    'NickT': {'password_hash': generate_password_hash('jntlaw'), 'entities': MASTER_ENTELLCITIES, 'role': 'admin'}, # Confirmed full access

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
    'Andrew_Phys': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'admin', 'email': 'andrew@example.com'},
    'PhysicianUser1': {'password_hash': generate_password_hash('physicianpass'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'email': 'physician1@example.com'},

    # Patient users (no change)
    'House_Patient': {'password_hash': generate_password_hash('password9'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'House', 'dob': '1980-05-15', 'ssn4': '1234', 'patient_id': 'PAT001'}},
    'PatientUser1': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient', 'patient_details': {'last_name': 'Doe', 'dob': '1990-01-01', 'ssn4': '5678', 'patient_id': 'PAT002'}},

    # Sample user for Business Dev
    'sample_business_dev': {'password_hash': generate_password_hash('dev_password'), 'entities': MASTER_ENTITIES, 'role': 'business_dev_manager'},
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
FINANCIAL_REPORT_DEFINITIONS = [
    {'display_name_part': 'Profit and Loss account', 'basis': 'Accrual Basis', 'file_suffix': '-Profit and Loss account - Accrual basis'},
    {'display_name_part': 'Profit and Loss account', 'basis': 'Cash Basis', 'file_suffix': '-Profit and Loss account - Cash Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Accrual Basis', 'file_suffix': '-Balance Sheet - Accrual Basis'},
    {'display_name_part': 'Balance Sheet', 'basis': 'Cash Basis', 'file_suffix': '-Balance Sheet - Cash Basis'},
    {'display_name_part': 'YTD Management Report', 'basis': 'Cash Basis', 'file_suffix': '-YTD Management Report - Cash Basis', 'applicable_years': [2025]}
]

# --- Marketing Report Definitions ---
MARKETING_REPORT_DEFINITIONS = [
    {'display_name_part': 'Product Catalog', 'file_suffix': '-Product Catalog'},
    {'display_name_part': 'Service Brochure', 'file_suffix': '-Service Brochure'},
    {'display_name_part': 'Company Profile', 'file_suffix': '-Company Profile'}
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
    df = pd.read_csv('data.csv', parse_dates=['Date']) # Parse 'Date' column as datetime objects
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

    if df.empty or 'PatientID' not in df.columns or 'Date' not in df.columns:
        flash("Patient data is not available or incorrectly structured. Please contact support.", "error")
        return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos={})

    patient_data = df[df['PatientID'] == patient_id].copy()

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
        dummy_pdf_filename = f"Patient_{patient_id}_DOS_{dos}_Report_{index}.pdf"
        
        results_by_dos[dos].append({
            'name': report_name,
            'webViewLink': url_for('static', filename=dummy_pdf_filename)
        })
        filepath = os.path.join('static', dummy_pdf_filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file for Patient {patient_id}, DOS {dos}, Result {index}.")
            print(f"Created dummy patient result file: {filepath}")

    return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos=results_by_dos)


@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role']
    user_authorized_entities = users[username]['entities']

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
                selected_month=selected_month,
                selected_year=selected_year
            )
        
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
                selected_month=selected_month,
                selected_year=selected_year
            )
        
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
        selected_entity=session.get('selected_entity'), # Pre-select if already in session
        selected_report_type=session.get('report_type'), # Pre-select if already in session
        selected_month=session.get('selected_month'),
        selected_year=session.get('selected_year')
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    user_role = users[rep]['role']
    
    # Get selections from session (or from POST request if coming from a form on dashboard/monthly_bonus)
    if request.method == 'POST':
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
        selected_entity = session.get('selected_entity')
        report_type = session.get('report_type')
        selected_month = session.get('selected_month')
        selected_year = session.get('selected_year')

    # Ensure an entity is selected for non-patient reports
    if report_type != 'patient_reports' and not selected_entity:
        flash("Please select an entity to view this report.", "error")
        return redirect(url_for('select_report'))

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
            print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    if report_type == 'financials':
        files_to_display = {}
        
        years_to_process = [selected_year] if selected_year else range(CURRENT_APP_YEAR - 2, CURRENT_APP_YEAR + 2)

        for year_val in years_to_process:
            year_reports = []
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                filename_to_create = f"{selected_entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath_check = os.path.join('static', filename_to_create)

                if os.path.exists(filepath_check):
                    year_reports.append({
                        'name': f"{report_def['display_name_part']} - {year_val} - {report_def['basis']}",
                        'webViewLink': url_for('static', filename=filename_to_create)
                    })
            if year_reports:
                files_to_display[year_val] = year_reports

        return render_template(
            'dashboard.html',
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display,
            data=filtered_data.to_dict(orient='records') # Pass filtered_data for the table
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            selected_entity=selected_entity,
            report_type=report_type,
            selected_month=selected_month,
            selected_year=selected_year
        )
    elif report_type == 'requisitions':
        return render_template(
            'generic_report.html',
            report_title="Requisitions Report",
            message=f"Requisitions report for {selected_entity} is under development."
        )
    elif report_type == 'marketing_material':
        files_to_display = {}
        if selected_entity:
            entity_files = []
            for report_def in MARKETING_REPORT_DEFINITIONS:
                filename = f"{selected_entity} - {report_def['display_name_part']}.pdf"
                filepath_check = os.path.join('static', filename)
                if os.path.exists(filepath_check):
                    entity_files.append({
                        'name': f"{report_def['display_name_part']} for {selected_entity}",
                        'webViewLink': url_for('static', filename=filename)
                    })
            if entity_files:
                files_to_display[selected_entity] = entity_files
        else:
            # Fallback for displaying all entities' marketing materials if no specific entity is chosen
            for entity in MASTER_ENTITIES:
                entity_files = []
                for report_def in MARKETING_REPORT_DEFINITIONS:
                    filename = f"{entity} - {report_def['display_name_part']}.pdf"
                    filepath_check = os.path.join('static', filename)
                    if os.path.exists(filepath_check):
                        entity_files.append({
                            'name': f"{report_def['display_name_part']} for {entity}",
                            'webViewLink': url_for('static', filename=filename)
                        })
                if entity_files:
                    files_to_display[entity] = entity_files

        return render_template(
            'dashboard.html',
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display,
            data=[]
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
    
    # Create dummy PDF files for financial reports (entity-specific)
    for year_val in range(CURRENT_APP_YEAR - 2, CURRENT_APP_YEAR + 2):
        for entity in MASTER_ENTITIES: # Loop through all master entities
            for report_def in FINANCIAL_REPORT_DEFINITIONS:
                if 'applicable_years' in report_def and year_val not in report_def['applicable_years']:
                    continue

                filename_to_create = f"{entity} - {report_def['display_name_part']} - {year_val} - {report_def['basis']}.pdf"
                filepath = os.path.join('static', filename_to_create)
                
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"This is a dummy PDF file for {entity} - {year_val} {report_def['display_name_part']} ({report_def['basis']})")
                    print(f"Created dummy file: {filepath}")

    # Create dummy PDF files for marketing materials (entity-specific)
    for entity in MASTER_ENTITIES:
        for report_def in MARKETING_REPORT_DEFINITIONS:
            filename_to_create = f"{entity} - {report_def['display_name_part']}.pdf"
            filepath = os.path.join('static', filename_to_create)

            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"This is a dummy PDF file for {entity} - {report_def['display_name_part']}.")
                print(f"Created dummy file: {filepath}")

    # Create dummy PDF files for patient results
    dummy_patient_ids = [details['patient_id'] for user, details in users.items() if details.get('role') == 'patient' and 'patient_details' in details]
    dummy_locations_for_patients = ['Main Lab', 'Satellite Clinic', 'Remote Testing Site']
    if dummy_patient_ids:
        for pid in dummy_patient_ids:
            for i in range(1, 4): # Create a few reports per patient
                # Ensure date is valid for dummy data
                report_date = (datetime.date(2025, 1, 1) + datetime.timedelta(days=i*10)).strftime('%Y-%m-%d')
                location = dummy_locations_for_patients[i % len(dummy_locations_for_patients)]
                dummy_pdf_filename = f"Patient_{pid}_DOS_{report_date}_Report_{i}.pdf"
                filepath = os.path.join('static', dummy_pdf_filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"This is a dummy PDF file for Patient {pid}, DOS {report_date}, Report {i} from {location}.")
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
                '2025-03-01', # New row for multi-user test
                '2025-01-10', '2025-02-15', '2025-03-20', '2025-04-25' # Patient data
            ],
            'Location': [
                'CENTRAL KENTUCKY SPINE SURGERY - TOX', 'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA',
                'HOPESS RESIDENTIAL TREATMENT', 'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
                'TEST LOCATION A', 'TEST LOCATION B', 'TEST LOCATION C', 'TEST LOCATION D',
                'OLD LOCATION X', 'OLD LOCATION Y',
                'NEW CLINIC Z', 'URGENT CARE A', 'HOSPITAL B',
                'HEALTH CENTER C', 'WELLNESS SPA D',
                'BETA TEST LOCATION', # Specific row for AndrewS bonus report test
                'SHARED PERFORMANCE CLINIC', # New row for multi-user test
                'Main Lab', 'Satellite Clinic', 'Main Lab', 'Satellite Clinic' # Patient data
            ],
            'Entity': [
                'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC',
                'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab', 'First Bio Genetics LLC',
                'AIM Laboratories LLC', 'AMICO Dx LLC',
                'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab',
                'First Bio Genetics LLC', 'First Bio Lab of Illinois',
                'AIM Laboratories LLC', # Entity for AndrewS bonus report test
                'First Bio Lab', # Entity for multi-user test
                'First Bio Lab', 'First Bio Lab', 'First Bio Lab', 'First Bio Lab' # Patient data
            ],
            'Bonus': [
                1000, 1500, 800, 2000, 1200,
                1100, 900, 1300, 1600,
                700, 1800,
                1400, 950, 1700,
                600, 1050,
                5000, # Bonus for AndrewS
                7500, # Bonus for multi-user test
                0, 0, 0, 0 # Patient data (no bonus)
            ],
            'Sales Representative': [
                'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew', 'JayM',
                'Andrew S', # Specific row for AndrewS bonus report test
                'Andrew S, Melinda C', # New row for multi-user test
                'N/A', 'N/A', 'N/A', 'N/A' # Patient data
            ],
            'Username': [ # NEW COLUMN - For filtering, must match login username
                'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew', 'JayM',
                'AndrewS', # Matches AndrewS login username
                'AndrewS,MelindaC', # Allows both AndrewS and MelindaC to see this line
                'House_Patient', 'House_Patient', 'PatientUser1', 'PatientUser1' # Patient data
            ],
            'PatientID': [
                'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A',
                'N/A',
                'PAT001', 'PAT001', 'PAT002', 'PAT002' # Patient data
            ],
            'TestResult': [
                'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A',
                'N/A',
                'Positive', 'Negative', 'Positive', 'Negative' # Patient data
            ]
        }
        pd.DataFrame(dummy_data).to_csv('data.csv', index=False)
        print("Created dummy data.csv file.")

    app.run(debug=True)
