import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re

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
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': ['AIM Laboratories LLC', 'First Bio Genetics LLC'], 'role': 'rep'}, # Changed role from admin to rep as per previous turns
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Admins with Specific Limited Access (based on your latest instructions)
    'AghaA': {'password_hash': generate_password_hash('agapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'Wenjun': {'password_hash': generate_password_hash('wenpass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'AndreaM': {'password_hash': generate_password_hash('andreapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'BenM': {'password_hash': generate_password_hash('benpass'), 'entities': ['Enviro Labs LLC'], 'role': 'admin'},
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin', 'email': 'sonnya@example.com'},
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
    'rep': [ # Added 'rep' role as per previous turns
        {'value': 'financials', 'name': 'Financials'},
        {'value': 'requisitions', 'name': 'Requisitions'},
        {'value': 'marketing_material', 'name': 'Marketing Material'}
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


# --- Data Loading (Optimized: Load once at app startup) ---
df = pd.DataFrame() # Initialize as empty to avoid error if file not found
try:
    df = pd.read_csv('data.csv', parse_dates=['Date']) # Parse 'Date' column as datetime objects
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py. Dummy data will be created.")
except Exception as e:
    print(f"An error occurred while loading data.csv: {e}")

# --- Helper function to get available report types for a user role ---
def get_available_report_types(user_role):
    return REPORT_TYPES_BY_ROLE.get(user_role, [])

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
        if selected_role in ['physician_provider', 'patient', 'business_dev_manager', 'admin', 'rep']: # Added 'rep'
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
        return redirect(url_for('select_role'))

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
                        found_physician = True
                        break
            
            if found_physician:
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid email or password.'
        else:
            # All other roles (now 'admin', 'rep', and 'business_dev_manager') use Username and Password
            username = request.form.get('username')
            password = request.form.get('password')
            
            user_info = users.get(username)

            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
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

    # Use helper function to get available report types
    available_report_types = get_available_report_types(user_role)

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

        if not report_type or not selected_entity:
            flash("Please select both a report type and an entity.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years
            )
        
        if selected_entity not in user_authorized_entities:
            if not user_authorized_entities:
                flash("You do not have any entities assigned to view reports. Please contact support.", "error")
                return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
            flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for.", "error")
            return render_template(
                'select_report.html',
                master_entities=display_entities,
                available_report_types=available_report_types,
                months=months,
                years=years
            )
        
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

    username = session['username'] # Changed 'rep' to 'username' for consistency
    user_role = users[username]['role'] # Changed 'rep' to 'username'
    
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

    user_authorized_entities = users[username]['entities'] # Changed 'rep' to 'username'
    display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    if selected_entity and selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
            flash("You do not have any entities assigned to view reports. Please contact support.", "error")
            return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity.", "error")
        return render_template(
            'select_report.html',
            master_entities=display_entities,
            available_report_types=get_available_report_types(user_role), # Use helper function
            months=months,
            years=years
        )

    filtered_data = pd.DataFrame()
    if username in UNFILTERED_ACCESS_USERS: # Changed 'rep' to 'username'
        if not df.empty:
            filtered_data = df.copy()
            print(f"User {username} has unfiltered access. Displaying all data.") # Changed 'rep' to 'username'
    elif not df.empty and 'Entity' in df.columns:
        if selected_entity:
            filtered_data = df[df['Entity'] == selected_entity].copy()
        else:
            filtered_data = df.copy()

    if selected_month and selected_year and 'Date' in filtered_data.columns:
        if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
            filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
        filtered_data = filtered_data[
            (filtered_data['Date'].dt.month == selected_month) & \
            (filtered_data['Date'].dt.year == selected_year)
        ]

    if report_type == 'monthly_bonus' and 'Username' in filtered_data.columns:
        normalized_username = username.strip().lower() # Changed 'rep' to 'username'
        filtered_data['Username'] = filtered_data['Username'].astype(str)
        regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
        filtered_data = filtered_data[
            filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
        ]
        print(f"User {username} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.") # Changed 'rep' to 'username'
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    current_app_year = datetime.datetime.now().year
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
            {'name': '2025 1Q Profit and Loss', 'filename': '2025_1Q_PL.pdf'},
            {'name': '2025 1Q Balance Sheet', 'filename': '2025_1Q_BS.pdf'}
        ]
    }
    
    files = []
    if report_type == 'financials':
        if selected_year and selected_year in financial_files_data:
            files = financial_files_data[selected_year]
        else:
            flash("No financial reports available for the selected year.", "info")
    elif report_type == 'monthly_bonus':
        if not filtered_data.empty:
            files = [
                {'name': f"Monthly Bonus Report - {row['Entity']} - {row['Date'].strftime('%Y-%m')}",
                 'filename': f"monthly_bonus_report_{row['Entity']}_{row['Date'].strftime('%Y%m')}.pdf"}
                for index, row in filtered_data.iterrows()
            ]
        else:
            flash("No monthly bonus reports found for your selection criteria.", "info")
    elif report_type == 'requisitions':
        # Dummy requisitions data
        files = [
            {'name': 'Requisition Form 1', 'filename': 'requisition_form_1.pdf'},
            {'name': 'Requisition Guidelines', 'filename': 'requisition_guidelines.pdf'}
        ]
    elif report_type == 'marketing_material':
        # Dummy marketing material data
        files = [
            {'name': 'Brochure - Services', 'filename': 'brochure_services.pdf'},
            {'name': 'Company Profile', 'filename': 'company_profile.pdf'}
        ]
    elif report_type == 'patient_reports':
        # This will be handled by the patient_results route, but kept here for completeness
        files = [] # No files directly displayed here, link to patient_results route instead
    
    data = {}
    if not filtered_data.empty:
        # For simplicity, just passing the first few rows or aggregated data
        data = filtered_data.head().to_dict(orient='records')
    
    return render_template(
        'dashboard.html',
        current_username=session['username'],
        selected_entity=selected_entity,
        report_type=report_type,
        months=months, # Pass months
        years=years,   # Pass years
        selected_month=selected_month, # Pass selected_month
        selected_year=selected_year,   # Pass selected_year
        files=files,
        data=data,
        master_entities=display_entities, # Changed user_authorized_entities to master_entities to match template
        available_report_types=get_available_report_types(user_role) # Use helper function
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('selected_role', None)
    session.pop('patient_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
