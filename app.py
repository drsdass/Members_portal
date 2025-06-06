import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_moment import Moment
import datetime
import re
from functools import wraps

# Initialize the Flask application
app = Flask(__name__)
moment = Moment(app) # Initialize Flask-Moment here

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
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS', 'NickT',]

# --- User Management (In-memory, with granular entity assignments for all roles) ---
users = {
    # Full Access Admins
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'NickT': {'password_hash': generate_password_hash('jntlaw'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Admins with Specific Limited Access
    'AghaA': {'password_hash': generate_password_hash('agapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'Wenjun': {'password_hash': generate_password_hash('wenpass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'AndreaM': {'password_hash': generate_password_hash('andreapass'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin'},
    'BenM': {'password_hash': generate_password_hash('benpass'), 'entities': ['Enviro Labs LLC'], 'role': 'admin'},
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories LLC'], 'role': 'admin', 'email': 'sonnya@example.com'},
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx LLC'], 'role': 'admin'},
    'BobSilverang': {'password_hash': generate_password_hash('silverpass'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'Enviro Labs LLC'], 'role': 'admin'},
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx LLC'], 'role': 'admin'},
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'admin', 'email': 'andrews@example.com'},

    # Existing users not explicitly mentioned in the latest list
    'Andrew_Phys': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'admin', 'email': 'andrew@example.com'},
    'PhysicianUser1': {'password_hash': generate_password_hash('physicianpass'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'email': 'physician1@example.com'},

    # Patient users
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
    # Create dummy data.csv if it doesn't exist, with new columns and example data
    dummy_data = {
        'Date': [
            '2025-03-12', '2025-03-15', '2025-03-18', '2025-03-20', '2025-03-22', # March 2025 data
            '2025-04-01', '2025-04-05', '2025-04-10', '2025-04-15', # April 2025 data
            '2025-02-01', '2025-02-05', # February 2025 data
            '2025-03-25', '2025-03-28', '2025-03-30', # More March data
            '2025-04-20', '2025-04-22', # More April data
            '2025-02-01', # Specific row for AndrewS bonus report test
            '2025-03-01', # New row for multi-user test
            '2025-01-10', '2025-02-15', '2025-03-20', '2025-04-25', # Patient data
            '2025-05-01' # New row for sample_business_dev
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
            'Main Lab', 'Satellite Clinic', 'Main Lab', 'Satellite Clinic', # Patient data
            'BUSINESS DEV OFFICE' # New row for sample_business_dev
        ],
        'Entity': [
            'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC',
            'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab', 'First Bio Genetics LLC',
            'AIM Laboratories LLC', 'AMICO Dx LLC',
            'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab',
            'First Bio Genetics LLC', 'First Bio Lab of Illinois',
            'AIM Laboratories LLC', # Entity for AndrewS bonus report test
            'First Bio Lab', # Entity for multi-user test
            'First Bio Lab', 'First Bio Lab', 'First Bio Lab', 'First Bio Lab', # Patient data
            'First Bio Lab' # New row for sample_business_dev, choose an entity available to this user
        ],
        'Bonus': [
            1000, 1500, 800, 2000, 1200,
            1100, 900, 1300, 1600,
            700, 1800,
            1400, 950, 1700,
            600, 1050,
            5000, # Bonus for AndrewS
            7500, # Bonus for multi-user test
            0, 0, 0, 0, # Patient data (no bonus)
            0 # Bonus for sample_business_dev (adjust as needed)
        ],
        'Sales Representative': [
            'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
            'SatishD', 'ACG', 'MelindaC', 'MinaK',
            'VinceO', 'NickC',
            'AshlieT', 'Omar', 'DarangT',
            'Andrew', 'JayM',
            'Andrew S', # Specific row for AndrewS bonus report test
            'Andrew S, Melinda C', # New row for multi-user test
            'N/A', 'N/A', 'N/A', 'N/A', # Patient data
            'Sample Business Dev' # New row for sample_business_dev
        ],
        'Username': [ # NEW COLUMN - For filtering, must match login username
            'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
            'SatishD', 'ACG', 'MelindaC', 'MinaK',
            'VinceO', 'NickC',
            'AshlieT', 'Omar', 'DarangT',
            'Andrew', 'JayM',
            'AndrewS', # Matches AndrewS login username
            'AndrewS,MelindaC', # Allows both AndrewS and MelindaC to see this line
            'House_Patient', 'House_Patient', 'PatientUser1', 'PatientUser1', # Patient data
            'sample_business_dev' # New row for sample_business_dev
        ],
        'PatientID': [
            'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A',
            'N/A',
            'PAT001', 'PAT001', 'PAT002', 'PAT002', # Patient data
            'N/A' # New row for sample_business_dev
        ],
        'TestResult': [
            'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A',
            'N/A',
            'Positive', 'Negative', 'Positive', 'Negative', # Patient data
            'N/A' # TestResult for sample_business_dev
        ],
         'Reimbursement': [ # Added back Reimbursement, COGS, Net, Commission for Monthly Bonus Report
            1.98, 150.49, 805.13, 2466.87, 76542.07,
            500.00, 750.00, 120.00, 900.00,
            300.00, 450.00,
            600.00, 150.00, 2500.00,
            350.00, 80.00,
            38.85,
            1200.00,
            100.00, 200.00, 150.00, 250.00,
            750.00 # New row for sample_business_dev
        ],
        'COGS': [
            50.00, 151.64, 250.00, 1950.00, 30725.00,
            200.00, 300.00, 50.00, 400.00,
            100.00, 150.00,
            250.00, 70.00, 1800.00,
            120.00, 30.00,
            25.00,
            500.00,
            20.00, 40.00, 30.00, 50.00,
            200.00 # New row for sample_business_dev
        ],
        'Net': [
            -48.02, -1.15, 555.13, 516.87, 45817.07,
            300.00, 450.00, 70.00, 500.00,
            200.00, 300.00,
            350.00, 80.00, 700.00,
            230.00, 50.00,
            13.85,
            700.00,
            80.00, 160.00, 120.00, 200.00,
            550.00 # New row for sample_business_dev
        ],
        'Commission': [
            -14.40, -0.34, 166.53, 155.06, 13745.12,
            90.00, 135.00, 21.00, 150.00,
            60.00, 90.00,
            105.00, 24.00, 210.00,
            69.00, 15.00,
            4.16,
            210.00,
            24.00, 48.00, 36.00, 60.00,
            165.00 # New row for sample_business_dev
        ]
    }
    df = pd.DataFrame(dummy_data)
    df.to_csv('data.csv', index=False)
    print("Created dummy data.csv file.")
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
                current_username=username,
                moment=moment # Pass the moment object to all templates
            )
    return dict(
        MASTER_ENTITIES=MASTER_ENTITIES,
        months=MONTHS,
        years=YEARS,
        current_app_year=CURRENT_APP_YEAR,
        current_username=None,
        moment=moment # Pass the moment object even if no user is logged in
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
        return redirect(url_for('select_role'))

    selected_role = session['selected_role']
    error_message = None

    if request.method == 'POST':
        if selected_role == 'patient':
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
                        session['user_role'] = user_info['role']
                        found_patient = True
                        break
            
            if found_patient:
                return redirect(url_for('patient_results'))
            else:
                error_message = 'Invalid patient details.'
        elif selected_role == 'physician_provider':
            email = request.form.get('email')
            password = request.form.get('password')
            
            found_physician = False
            for username_key, user_info in users.items():
                if user_info.get('role') == 'physician_provider' and user_info.get('email') and user_info['email'].lower() == email.lower():
                    if check_password_hash(user_info['password_hash'], password):
                        session['username'] = username_key
                        session['user_role'] = user_info['role']
                        found_physician = True
                        break
            
            if found_physician:
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid email or password.'
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user_info = users.get(username)

            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                session['user_role'] = user_info['role']
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
            'entities': [],
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
            if pre_selected_entity:
                session['selected_entity'] = pre_selected_entity
            elif 'selected_entity' not in session and user_authorized_entities:
                session['selected_entity'] = user_authorized_entities[0]
            
            session['selected_month'] = int(pre_selected_month) if pre_selected_month else None
            session['selected_year'] = int(pre_selected_year) if pre_selected_year else None
            
            if pre_selected_report_type == 'patient_reports' and user_role == 'patient':
                return redirect(url_for('patient_results'))
            elif session.get('selected_entity'):
                return redirect(url_for('dashboard'))
            else:
                flash("Please select an entity for this report.", "error")
                return render_template(
                    'select_report.html',
                    master_entities=display_entities,
                    selected_entity=session.get('selected_entity'),
                    selected_report_type=session.get('report_type'),
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
    
    return render_template(
        'select_report.html',
        master_entities=display_entities,
        selected_entity=session.get('selected_entity'),
        selected_report_type=session.get('report_type'),
        selected_month=session.get('selected_month'),
        selected_year=session.get('selected_year')
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    user_role = users[rep]['role']
    
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

    if report_type != 'patient_reports' and not selected_entity:
        flash("Please select an entity to view this report.", "error")
        return redirect(url_for('select_report'))

    user_authorized_entities = users[rep]['entities']
    
    if selected_entity and selected_entity not in user_authorized_entities:
        if not user_authorized_entities:
             flash("You do not have any entities assigned to view reports. Please contact support.", "error")
             return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity.", "error")
        return redirect(url_for('select_report'))


    filtered_data = pd.DataFrame()

    if report_type == 'monthly_bonus':
        if not df.empty:
            filtered_data = df.copy()
            for col in ['Reimbursement', 'COGS', 'Net', 'Commission']:
                filtered_data[col] = pd.to_numeric(filtered_data[col], errors='coerce').fillna(0)
            
            if not pd.api.types.is_datetime64_any_dtype(filtered_data['Date']):
                filtered_data['Date'] = pd.to_datetime(filtered_data['Date'], errors='coerce')
            filtered_data.dropna(subset=['Date'], inplace=True)

            if 'Month' not in filtered_data.columns:
                 filtered_data['Month'] = filtered_data['Date'].dt.to_period('M')
            if 'Year' not in filtered_data.columns:
                filtered_data['Year'] = filtered_data['Date'].dt.year

            if rep in UNFILTERED_ACCESS_USERS:
                print(f"User {rep} has unfiltered access. Displaying all data.")
            elif 'Entity' in filtered_data.columns:
                if selected_entity:
                    filtered_data = filtered_data[filtered_data['Entity'] == selected_entity].copy()
                else:
                    print(f"Warning: Selected entity not found. Cannot filter for entity '{selected_entity}'. Displaying all authorized data.")
                    filtered_data = filtered_data[filtered_data['Entity'].isin(user_authorized_entities)].copy()
            else:
                print(f"Warning: 'Entity' column not found in data.csv. Cannot filter by entity.")
        else:
            print("Warning: data.csv is empty. No data to filter for monthly bonus report.")


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
            data=[], # Ensure no data overview is passed for financials
            user_role=user_role
        )
    elif report_type == 'monthly_bonus':
        if 'Username' in filtered_data.columns:
            normalized_username = rep.strip().lower()
            filtered_data['Username'] = filtered_data['Username'].astype(str)
            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            print(f"User {rep} (non-unfiltered) viewing monthly bonus report. Filtered by 'Username' column.")
        
        if selected_month and selected_month != '-- Select Month --' and 'Month' in filtered_data.columns:
            try:
                filtered_data = filtered_data[filtered_data['Month'] == pd.Period(f"{selected_year}-{str(selected_month).zfill(2)}")]
            except Exception as e:
                flash(f"Error filtering by month: {e}", "error")
                print(f"Error filtering by month: {e}")
        if selected_year and selected_year != '-- Select Year --' and 'Year' in filtered_data.columns:
            try:
                filtered_data = filtered_data[filtered_data['Year'] == int(selected_year)]
            except Exception as e:
                flash(f"Error filtering by year: {e}", "error")
                print(f"Error filtering by year: {e}")

        if 'Reimbursement' in filtered_data.columns:
            filtered_data['Bonus_Percentage_Reimbursement'] = filtered_data['Reimbursement'] * 0.05
        else:
            filtered_data['Bonus_Percentage_Reimbursement'] = 0
            flash("Warning: 'Reimbursement' column not found for bonus calculation.", "warning")

        if 'Net' in filtered_data.columns:
            filtered_data['Bonus_Percentage_Net'] = filtered_data['Net'] * 0.15
        else:
            filtered_data['Bonus_Percentage_Net'] = 0
            flash("Warning: 'Net' column not found for bonus calculation.", "warning")

        if 'Associated Rep Name' in filtered_data.columns:
            monthly_bonus_data = filtered_data.groupby('Associated Rep Name').agg(
                Total_Reimbursement=('Reimbursement', 'sum'),
                Total_Net=('Net', 'sum'),
                Total_Bonus_Reimbursement=('Bonus_Percentage_Reimbursement', 'sum'),
                Total_Bonus_Net=('Bonus_Percentage_Net', 'sum')
            ).round(2).to_dict(orient='index')
        else:
            monthly_bonus_data = {}
            flash("Warning: 'Associated Rep Name' column not found for bonus report grouping.", "warning")

        return render_template(
            'monthly_bonus.html',
            data=filtered_data.to_dict(orient='records'),
            monthly_bonus_data=monthly_bonus_data,
            selected_entity=selected_entity,
            report_type=report_type,
            selected_month=selected_month,
            selected_year=selected_year,
            user_role=user_role
        )
    elif report_type == 'requisitions':
        pdf_filename = f"{selected_entity} - Requisitions.pdf"
        filepath_check = os.path.join(app.static_folder, pdf_filename)
        if os.path.exists(filepath_check):
            return send_from_directory(app.static_folder, pdf_filename)
        else:
            flash(f'Requisitions report file "{pdf_filename}" not found in static folder.', 'danger')
            return render_template(
                'dashboard.html',
                selected_entity=selected_entity,
                report_type=report_type,
                files={},
                data=[],
                user_role=user_role
            )
    elif report_type == 'marketing_material':
        files_to_display = {}
        if selected_entity:
            entity_files = []
            for report_def in MARKETING_REPORT_DEFINITIONS:
                filename = f"{selected_entity} - {report_def['display_name_part']}.pdf"
                filepath_check = os.path.join(app.static_folder, filename)
                if os.path.exists(filepath_check):
                    entity_files.append({
                        'name': f"{report_def['display_name_part']} for {selected_entity}",
                        'webViewLink': url_for('static', filename=filename)
                    })
            if entity_files:
                files_to_display[selected_entity] = entity_files
            else:
                 flash(f'No marketing materials found for {selected_entity}.', 'info')
        else:
            for entity in MASTER_ENTITIES:
                entity_files = []
                for report_def in MARKETING_REPORT_DEFINITIONS:
                    filename = f"{entity} - {report_def['display_name_part']}.pdf"
                    filepath_check = os.path.join(app.static_folder, filename)
                    if os.path.exists(filepath_check):
                        entity_files.append({
                            'name': f"{report_def['display_name_part']} for {entity}",
                            'webViewLink': url_for('static', filename=filename)
                        })
                if entity_files:
                    files_to_display[entity] = entity_files
            
            if not files_to_display:
                flash('No marketing materials found across all entities.', 'info')

        return render_template(
            'dashboard.html',
            selected_entity=selected_entity,
            report_type=report_type,
            files=files_to_display,
            data=[], # Ensure no data overview is passed for marketing materials
            user_role=user_role
        )
    elif report_type == 'patient_reports':
        return redirect(url_for('patient_results'))
    else:
        flash("Invalid report type selected.", "error")
        return redirect(url_for('select_report'))

    return render_template(
        'dashboard.html',
        selected_entity=selected_entity,
        report_type=report_type,
        files={},
        data=[],
        user_role=user_role
    )

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
            for i in range(1, 4):
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
                '2025-03-12', '2025-03-15', '2025-03-18', '2025-03-20', '2025-03-22',
                '2025-04-01', '2025-04-05', '2025-04-10', '2025-04-15',
                '2025-02-01', '2025-02-05',
                '2025-03-25', '2025-03-28', '2025-03-30',
                '2025-04-20', '2025-04-22',
                '2025-02-01',
                '2025-03-01',
                '2025-01-10', '2025-02-15', '2025-03-20', '2025-04-25',
                '2025-05-01'
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
                'Main Lab', 'Satellite Clinic', 'Main Lab', 'Satellite Clinic',
                'BUSINESS DEV OFFICE'
            ],
            'Entity': [
                'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC',
                'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab', 'First Bio Genetics LLC',
                'AIM Laboratories LLC', 'AMICO Dx LLC',
                'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab',
                'First Bio Genetics LLC', 'First Bio Lab of Illinois',
                'AIM Laboratories LLC',
                'First Bio Lab',
                'First Bio Lab', 'First Bio Lab', 'First Bio Lab', 'First Bio Lab',
                'First Bio Lab'
            ],
            'Bonus': [
                1000, 1500, 800, 2000, 1200,
                1100, 900, 1300, 1600,
                700, 1800,
                1400, 950, 1700,
                600, 1050,
                5000,
                7500,
                0, 0, 0, 0,
                0
            ],
            'Sales Representative': [
                'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew', 'JayM',
                'Andrew S',
                'Andrew S, Melinda C',
                'N/A', 'N/A', 'N/A', 'N/A',
                'Sample Business Dev'
            ],
            'Username': [
                'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
                'SatishD', 'ACG', 'MelindaC', 'MinaK',
                'VinceO', 'NickC',
                'AshlieT', 'Omar', 'DarangT',
                'Andrew', 'JayM',
                'AndrewS',
                'AndrewS,MelindaC',
                'House_Patient', 'House_Patient', 'PatientUser1', 'PatientUser1',
                'sample_business_dev'
            ],
            'PatientID': [
                'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A',
                'N/A',
                'PAT001', 'PAT001', 'PAT002', 'PAT002',
                'N/A'
            ],
            'TestResult': [
                'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A', 'N/A', 'N/A',
                'N/A', 'N/A',
                'N/A',
                'N/A',
                'Positive', 'Negative', 'Positive', 'Negative',
                'N/A'
            ],
             'Reimbursement': [
                1.98, 150.49, 805.13, 2466.87, 76542.07,
                500.00, 750.00, 120.00, 900.00,
                300.00, 450.00,
                600.00, 150.00, 2500.00,
                350.00, 80.00,
                38.85,
                1200.00,
                100.00, 200.00, 150.00, 250.00,
                750.00
            ],
            'COGS': [
                50.00, 151.64, 250.00, 1950.00, 30725.00,
                200.00, 300.00, 50.00, 400.00,
                100.00, 150.00,
                250.00, 70.00, 1800.00,
                120.00, 30.00,
                25.00,
                500.00,
                20.00, 40.00, 30.00, 50.00,
                200.00
            ],
            'Net': [
                -48.02, -1.15, 555.13, 516.87, 45817.07,
                300.00, 450.00, 70.00, 500.00,
                200.00, 300.00,
                350.00, 80.00, 700.00,
                230.00, 50.00,
                13.85,
                700.00,
                80.00, 160.00, 120.00, 200.00,
                550.00
            ],
            'Commission': [
                -14.40, -0.34, 166.53, 155.06, 13745.12,
                90.00, 135.00, 21.00, 150.00,
                60.00, 90.00,
                105.00, 24.00, 210.00,
                69.00, 15.00,
                4.16,
                210.00,
                24.00, 48.00, 36.00, 60.00,
                165.00
            ]
        }
    df = pd.DataFrame(dummy_data)
    df.to_csv('data.csv', index=False)
    print("Created dummy data.csv file.")

    app.run(debug=True)
