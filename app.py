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
            'CENTRAL KENTUCKY SPINE SURGERY - TOX', 'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA', 'HOPESS RESIDENTIAL TREATMENT', 'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
            'TEST LOCATION A', 'TEST LOCATION B', 'TEST LOCATION C', 'TEST LOCATION D',
            'OLD LOCATION X', 'OLD LOCATION Y',
            'NEW CLINIC Z', 'URGENT CARE A', 'HOSPITAL B',
            'HEALTH CENTER C', 'WELLNESS SPA D',
            'BETA TEST LOCATION', # Specific row for AndrewS bonus report test
            'SHARED PERFORMANCE CLINIC', # New row for multi-user test
            'Main Lab', 'Satellite Clinic', 'Main Lab', 'Satellite Clinic', # Patient data
            'BUSINESS DEV OFFICE' # New row for sample_business_dev
        ],
        'Reimbursement': [
            1.98, 150.49, 805.13, 2466.87, 76542.07,
            500.00, 750.00, 1200.00, 600.00,
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
            300.00, 450.00, 1150.00, 200.00,
            200.00, 300.00,
            350.00, 80.00, 700.00,
            230.00, 50.00,
            13.85,
            700.00,
            80.00, 160.00, 120.00, 200.00,
            550.00
        ],
        'Commission': [
            -14.41, -0.35, 166.54, 155.06, 13745.12,
            90.00, 135.00, 345.00, 60.00,
            60.00, 90.00,
            105.00, 24.00, 210.00,
            69.00, 15.00,
            4.16,
            210.00,
            24.00, 48.00, 36.00, 60.00,
            165.00
        ],
        'Entity': [
            'AIM Laboratories LLC', 'AIM Laboratories LLC', 'AIM Laboratories LLC', 'AIM Laboratories LLC', 'AIM Laboratories LLC',
            'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AMICO Dx LLC',
            'Enviro Labs LLC', 'Stat Labs',
            'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois',
            'AIM Laboratories LLC', 'AMICO Dx LLC',
            'AIM Laboratories LLC', # Entity for AndrewS bonus report test
            'First Bio Lab', # Entity for multi-user test
            'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab', 'First Bio Genetics LLC', # Patient data
            'First Bio Lab' # Entity for sample_business_dev
        ],
        'Associated Rep Name': [
            'House', 'House', 'SAV LLC', 'HCM Crew LLC', 'HCM Crew LLC',
            'Celano Venture', 'Celano Venture', 'Celano Venture', 'Celano Venture',
            'GD Laboratory', 'GD Laboratory',
            'Celano Venture', 'GD Laboratory', 'Celano Venture',
            'HCM Crew LLC', 'HCM Crew LLC',
            'Andrew S', # Associated Rep Name for AndrewS bonus report test
            'Celano Venture', # Associated Rep Name for multi-user test
            'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Jones', # Patient data
            'Sample Business Dev' # Associated Rep Name for sample_business_dev
        ],
        'Username': [
            'SatishD', 'SatishD', 'VinceO', 'JayM', 'JayM',
            'SatishD', 'SatishD', 'SatishD', 'SatishD',
            'SatishD', 'SatishD',
            'SatishD', 'SatishD', 'SatishD',
            'JayM', 'JayM',
            'AndrewS', # Username for AndrewS bonus report test
            'SatishD', # Username for multi-user test
            'PatientUser1', 'PatientUser1', 'House_Patient', 'House_Patient', # Patient data
            'sample_business_dev' # Username for sample_business_dev
        ],
        'PatientID': [
            'NA', 'NA', 'NA', 'NA', 'NA',
            'NA', 'NA', 'NA', 'NA',
            'NA', 'NA',
            'NA', 'NA', 'NA',
            'NA', 'NA',
            'NA',
            'NA',
            'PAT001', 'PAT001', 'PAT002', 'PAT002', # Patient data
            'NA'
        ]
    }
    df = pd.DataFrame(dummy_data)
    df['Date'] = pd.to_datetime(df['Date']) # Ensure 'Date' column is datetime
    print("Dummy data created and loaded.")
    # Save dummy data to data.csv for future runs if needed
    df.to_csv('data.csv', index=False)


# --- Login and Role Selection ---

# Decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('select_role'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if the user has the required role
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in allowed_roles:
                flash('You do not have the necessary permissions to view this page.', 'error')
                return redirect(url_for('unauthorized'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    session.clear() # Clear session on role selection to ensure fresh start
    if request.method == 'POST':
        role = request.form.get('role')
        if role in ['physician_provider', 'patient', 'business_dev_manager', 'admin']:
            session['selected_role'] = role
            # Redirect to login page specific to the selected role
            return redirect(url_for('login', role=role))
        else:
            flash('Invalid role selected.', 'error')
    return render_template('role_selection.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me')

        user_data = users.get(username)

        if user_data and check_password_hash(user_data['password_hash'], password):
            if user_data['role'] == role:
                session['username'] = username
                session['role'] = role
                session['logged_in'] = True

                if remember_me:
                    session.permanent = True
                    app.permanent_session_lifetime = datetime.timedelta(days=30) # Remember for 30 days

                flash(f'Welcome, {username}! You have successfully logged in as {role.replace("_", " ").title()}.', 'success')

                # Admins and Business Dev Managers with full entity access can go directly to dashboard
                if role in ['admin', 'business_dev_manager'] and user_data['entities'] == MASTER_ENTITIES:
                    # For admins and business dev managers, automatically select all entities if they have full access
                    session['selected_entity'] = 'All Entities'
                    return redirect(url_for('dashboard'))
                # Physicians/Providers need to select an entity if they have multiple
                elif role == 'physician_provider' and len(user_data['entities']) > 1:
                    return redirect(url_for('select_entity'))
                # All other cases go to dashboard or specific selection if only one entity
                else:
                    if user_data['entities']:
                        # If a user has only one entity, pre-select it
                        session['selected_entity'] = user_data['entities'][0]
                    else:
                        # For patients or roles without associated entities, set a placeholder or handle as needed
                        session['selected_entity'] = 'N/A'
                    return redirect(url_for('dashboard'))
            else:
                flash(f'Your account is not registered under the {role.replace("_", " ").title()} role. Please select the correct role.', 'error')
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html', selected_role=role)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('select_role'))

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html', message=flash.get_flashed_messages(with_categories=true))

# --- Entity Selection ---
@app.route('/select_entity', methods=['GET', 'POST'])
@login_required
@role_required(['physician_provider', 'admin', 'business_dev_manager']) # Only these roles manage entities
def select_entity():
    username = session['username']
    user_entities = users[username]['entities']
    error = None

    if request.method == 'POST':
        selected_entity = request.form.get('entity_name')
        if selected_entity and selected_entity in user_entities:
            session['selected_entity'] = selected_entity
            return redirect(url_for('dashboard'))
        else:
            error = 'Please select a valid entity.'

    return render_template('select_entity.html', available_entities=user_entities, error=error)

# --- Dashboard and Report Views ---
@app.route('/')
@login_required
def dashboard():
    username = session['username']
    user_role = session.get('role')
    if not user_role:
        flash('No role found. Please select one.')
        return redirect(url_for('auth.select_role'))
    selected_entity = session.get('selected_entity', 'All Entities') # Default to 'All Entities'

    # Filter available report types based on the user's role
    available_report_types = REPORT_TYPES_BY_ROLE.get(user_role, [])

    # Prepare data for dashboard view
    display_data = []
    report_type = session.get('report_type')
    month = session.get('month')
    year = session.get('year')

    if report_type == 'financials':
        if selected_entity == 'All Entities':
            message = "Please select a specific entity to view financial reports."
            return render_template('dashboard.html',
                                   current_username=username,
                                   user_role=user_role,
                                   available_report_types=available_report_types,
                                   message=message)

        # Determine the correct financial report filename based on selected entity, month, year
        # This is a placeholder for actual file fetching logic
        financial_reports_info = []
        for report_def in FINANCIAL_REPORT_DEFINITIONS:
            # Check if 'applicable_years' exists and if the selected year is in it
            if 'applicable_years' in report_def and year not in report_def['applicable_years']:
                continue # Skip if the report is not applicable for the selected year

            filename = f"{selected_entity}{report_def['file_suffix']}.pdf"
            display_name = f"{selected_entity} {report_def['display_name_part']} ({report_def['basis']}) - {month}/{year}"

            # Placeholder for actual file existence check
            # In a real application, you would check if the file exists in your storage (e.g., S3, Google Drive)
            file_exists = True # Assume file exists for demonstration

            if file_exists:
                financial_reports_info.append({
                    'name': display_name,
                    'filename': filename,
                    # This would be a link to download or view the PDF,
                    # e.g., url_for('download_report', filename=filename, entity=selected_entity)
                    'webViewLink': url_for('download_report', report_type='financials', entity=selected_entity,
                                           display_name_part=report_def['display_name_part'], basis=report_def['basis'],
                                           month=month, year=year)
                })

        if not financial_reports_info:
            message = "No financial reports available for the selected entity and period."
            return render_template('dashboard.html',
                                   current_username=username,
                                   user_role=user_role,
                                   available_report_types=available_report_types,
                                   selected_entity=selected_entity,
                                   message=message)

        return render_template('dashboard.html',
                               current_username=username,
                               user_role=user_role,
                               available_report_types=available_report_types,
                               selected_entity=selected_entity,
                               financial_reports=financial_reports_info)

    elif report_type == 'monthly_bonus':
        # Ensure the user has unfiltered access for monthly bonus reports
        if username not in UNFILTERED_ACCESS_USERS:
            flash('You are not authorized to view the Monthly Bonus Report.', 'error')
            return redirect(url_for('unauthorized')) # Redirect to unauthorized page

        # Filter data for the logged-in user and selected month/year
        filtered_df = df[
            (df['Username'] == username) &
            (df['Date'].dt.month == int(month)) &
            (df['Date'].dt.year == int(year))
        ]

        # Calculate totals for the bonus report
        total_reimbursement = filtered_df['Reimbursement'].sum()
        total_cogs = filtered_df['COGS'].sum()
        total_net = filtered_df['Net'].sum()
        total_commission = filtered_df['Commission'].sum()

        # Convert to a list of dictionaries for rendering in HTML
        # Also, include the totals
        if not filtered_df.empty:
            display_data = filtered_df.to_dict(orient='records')
            # Add totals as a separate entry or as a summary object
            totals_summary = {
                'Location': 'TOTALS',
                'Reimbursement': total_reimbursement,
                'COGS': total_cogs,
                'Net': total_net,
                'Commission': total_commission,
                'Entity': '', 'Associated Rep Name': '', 'Username': '', 'PatientID': '' # Empty for totals row
            }
            display_data.append(totals_summary) # Add totals to the end of the data

        return render_template('monthly_bonus.html',
                               current_username=username,
                               user_role=user_role,
                               available_report_types=available_report_types,
                               selected_entity=selected_entity,
                               month=month,
                               year=year,
                               report_data=display_data,
                               has_data=not filtered_df.empty)

    elif report_type == 'requisitions':
        # Filter for the selected entity and month/year
        if selected_entity == 'All Entities':
            message = "Please select a specific entity to view requisitions."
            return render_template('dashboard.html',
                                   current_username=username,
                                   user_role=user_role,
                                   available_report_types=available_report_types,
                                   message=message)

        filtered_df = df[
            (df['Entity'] == selected_entity) &
            (df['Date'].dt.month == int(month)) &
            (df['Date'].dt.year == int(year))
        ]

        # For requisitions, we might just want to display the raw data or a summarized version
        display_data = filtered_df.to_dict(orient='records') if not filtered_df.empty else []

        return render_template('generic_report.html',
                               report_title=f"Requisitions for {selected_entity} - {month}/{year}",
                               message=f"Displaying {len(display_data)} requisitions.",
                               report_data=display_data,
                               show_table=not filtered_df.empty) # Pass a flag to indicate if table should be shown

    elif report_type == 'marketing_material':
        # Placeholder for fetching marketing materials from a drive/storage
        # In a real application, this would interact with a file storage API (e.g., Google Drive API)
        marketing_materials_info = []

        entities_to_show = [selected_entity] if selected_entity != 'All Entities' else MASTER_ENTITIES

        files_by_entity = {} # Group files by entity

        for entity in entities_to_show:
            entity_files = []
            for material_def in MARKETING_REPORT_DEFINITIONS:
                filename = f"{entity}{material_def['file_suffix']}.pdf"
                display_name = f"{entity} {material_def['display_name_part']}"

                # Simulate file existence check
                file_exists = True # Assume files exist for all entities and types for demo

                if file_exists:
                    entity_files.append({
                        'name': display_name,
                        'filename': filename,
                        # This would be a link to view/download the material
                        'webViewLink': url_for('download_report', report_type='marketing_material', entity=entity,
                                               display_name_part=material_def['display_name_part'])
                    })
            if entity_files:
                files_by_entity[entity] = entity_files

        return render_template('dashboard.html',
                               current_username=username,
                               user_role=user_role,
                               available_report_types=available_report_types,
                               selected_entity=selected_entity,
                               files=files_by_entity) # Pass grouped files

    elif report_type == 'patient_reports':
        patient_id = request.args.get('patient_id') # Patient ID is passed as a query parameter
        if user_role == 'patient':
            # For patient role, automatically use their own patient details
            user_details = users.get(username, {}).get('patient_details', {})
            patient_id = user_details.get('patient_id')
            patient_last_name = user_details.get('last_name')
            patient_dob = user_details.get('dob')
            patient_ssn4 = user_details.get('ssn4')

            # If patient details are not fully configured, redirect or show error
            if not all([patient_id, patient_last_name, patient_dob, patient_ssn4]):
                flash("Your patient profile is incomplete. Please contact support.", 'error')
                return redirect(url_for('dashboard'))

            # Filter for the patient's own records
            filtered_df = df[
                (df['PatientID'] == patient_id) &
                (df['Associated Rep Name'].str.contains(patient_last_name, case=False, na=False)) # Assuming last name is in 'Associated Rep Name' for simplicity
                # In a real system, you'd use a more robust patient matching
            ]

            if not filtered_df.empty:
                return redirect(url_for('display_patient_reports', patient_id=patient_id))
            else:
                return render_template('patient_results.html',
                                       patient_name=patient_last_name,
                                       message="No patient reports found for your profile.",
                                       show_table=False)

        elif user_role in ['physician_provider', 'admin']:
            if not patient_id:
                flash('Please enter a Patient ID to search for patient reports.', 'info')
                return render_template('dashboard.html',
                                       current_username=username,
                                       user_role=user_role,
                                       available_report_types=available_report_types,
                                       selected_entity=selected_entity)

            # Filter based on patient_id and selected_entity (if not 'All Entities')
            filtered_df = df[df['PatientID'] == patient_id]

            if selected_entity != 'All Entities':
                # Admins or Physicians can only see patient reports for entities they manage
                user_allowed_entities = users[username]['entities']
                if selected_entity not in user_allowed_entities:
                    flash('You are not authorized to view patient reports for this entity.', 'error')
                    return redirect(url_for('unauthorized'))

                filtered_df = filtered_df[filtered_df['Entity'] == selected_entity]

            if not filtered_df.empty:
                # Redirect to a dedicated page for displaying patient reports
                return redirect(url_for('display_patient_reports', patient_id=patient_id, entity=selected_entity))
            else:
                message = f"No patient reports found for Patient ID: {patient_id} in {selected_entity}."
                if selected_entity == 'All Entities':
                    message = f"No patient reports found for Patient ID: {patient_id} across all entities."

                return render_template('patient_results.html',
                                       patient_name=patient_id, # Display patient ID if name not available
                                       message=message,
                                       show_table=False)
        else:
            flash("Patient reports are not available for your role.", 'error')
            return redirect(url_for('dashboard'))

    return render_template('dashboard.html',
                           current_username=username,
                           user_role=user_role,
                           available_report_types=available_report_types,
                           selected_entity=selected_entity,
                           months=MONTHS,
                           years=YEARS,
                           current_month=datetime.datetime.now().month,
                           current_year=datetime.datetime.now().year)

@app.route('/select_report', methods=['GET', 'POST'])
@login_required
def select_report():
    import pandas as pd
access_df = pd.read_csv('access.csv')
username = session['username']
        user_role = session.get('role')
    if not user_role:
        flash('No role found. Please select one.')
        return redirect(url_for('auth.select_role'))
    selected_entity = session.get('selected_entity')
    # Filter allowed entities for this user from access.csv
    user_row = access_df[access_df['Admin'] == username]
    entities = []
    if not user_row.empty:
        row_data = user_row.iloc[0].to_dict()
        entities = [key for key, val in row_data.items() if val.strip().lower() == 'yes' and key != 'Admin']


    # Filter available report types based on the user's role
    available_report_types = REPORT_TYPES_BY_ROLE.get(user_role, [])

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        month = request.form.get('month')
        year = request.form.get('year')
        patient_id = request.form.get('patient_id') # For patient reports search

        # Store selections in session
        session['report_type'] = report_type
        session['month'] = month
        session['year'] = year

        # Handle specific redirects based on report type
        if report_type == 'patient_reports':
            # For patient reports, we always pass the patient_id (even if empty for admins/physicians initially)
            return redirect(url_for('dashboard', patient_id=patient_id))
        elif report_type in ['financials', 'monthly_bonus', 'requisitions', 'marketing_material']:
            return redirect(url_for('dashboard'))
        else:
            flash('Please select a valid report type.', 'error')
            return redirect(url_for('select_report'))

    # Determine default month and year for display
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year

    return render_template('select_report.html',
                           available_report_types=available_report_types,
                           months=MONTHS,
                           years=YEARS,
                           current_month=current_month,
                           current_year=current_year,
                           user_role=user_role, # Pass role to template for conditional rendering
                           selected_entity=selected_entity,
                           username=username) # Pass username to template for personalized messages

@app.route('/patient_reports/<patient_id>')
@login_required
def display_patient_reports(patient_id):
    username = session['username']
    user_role = session.get('role')
    if not user_role:
        flash('No role found. Please select one.')
        return redirect(url_for('auth.select_role'))
    selected_entity = session.get('selected_entity')
    # Filter allowed entities for this user from access.csv
    user_row = access_df[access_df['Admin'] == username]
    entities = []
    if not user_row.empty:
        row_data = user_row.iloc[0].to_dict()
        entities = [key for key, val in row_data.items() if val.strip().lower() == 'yes' and key != 'Admin']
 # Get selected entity from session

    patient_name = patient_id # Default to patient ID if name not found

    # Logic for patient role vs. admin/physician role
    if user_role == 'patient':
        user_details = users.get(username, {}).get('patient_details', {})
        if user_details and user_details.get('patient_id') == patient_id:
            # This is the patient viewing their own reports
            filtered_df = df[df['PatientID'] == patient_id]
            patient_name = user_details.get('last_name', patient_id) # Use last name for display
        else:
            flash("You are not authorized to view this patient's reports.", 'error')
            return redirect(url_for('unauthorized'))
    else: # admin or physician_provider role
        filtered_df = df[df['PatientID'] == patient_id]

        if selected_entity != 'All Entities':
            # Admins/Physicians can only see patient reports for entities they manage
            user_allowed_entities = users[username]['entities']
            if selected_entity not in user_allowed_entities:
                flash('You are not authorized to view patient reports for this entity.', 'error')
                return redirect(url_for('unauthorized'))
            filtered_df = filtered_df[filtered_df['Entity'] == selected_entity]

        # Try to get patient's last name from the filtered data if available
        if not filtered_df.empty:
            patient_name = filtered_df['Associated Rep Name'].iloc[0] # Assuming rep name might contain patient's last name
            # Or retrieve from a dedicated patient_details structure if available
            # For simplicity, if 'Associated Rep Name' is 'Dr. Smith' or 'Dr. Jones', we don't want to use that.
            # We would need a proper patient database for robust patient name lookup.
            # For now, let's just use the patient_id if it's not a physician's name.
            if patient_name.startswith('Dr.'):
                patient_name = patient_id

    if not filtered_df.empty:
        # Group by Date of Service (DOS)
        results_by_dos = {}
        for dos, group in filtered_df.groupby(filtered_df['Date'].dt.date):
            reports_for_dos = []
            # In a real application, each row might correspond to a specific report file
            # For this demo, we'll create dummy report names/links
            for index, row in group.iterrows():
                report_name = f"Report for {row['Location']} (Reimbursement: ${row['Reimbursement']:.2f})"
                # Dummy link to a generic report or a downloadable file
                report_link = url_for('download_report', report_type='patient_specific', patient_id=patient_id, date=dos.strftime('%Y-%m-%d'))
                reports_for_dos.append({'name': report_name, 'webViewLink': report_link})
            results_by_dos[dos.strftime('%Y-%m-%d')] = reports_for_dos

        return render_template('patient_results.html',
                               patient_name=patient_name,
                               results_by_dos=results_by_dos,
                               message=f"Found {len(filtered_df)} records for {patient_name}." if user_role != 'patient' else None,
                               show_table=True)
    else:
        message = f"No patient reports found for Patient ID: {patient_id}."
        if selected_entity != 'All Entities':
            message += f" within entity: {selected_entity}."
        return render_template('patient_results.html',
                               patient_name=patient_name,
                               message=message,
                               show_table=False)

# --- File Serving ---

@app.route('/download_report/<report_type>/<entity>/<display_name_part>')
@app.route('/download_report/<report_type>/<entity>/<display_name_part>/<basis>/<month>/<year>')
@login_required
def download_report(report_type, entity, display_name_part, basis=None, month=None, year=None):
    # This route is a placeholder for serving actual PDF files from a secure storage.
    # In a production environment, you would:
    # 1. Verify user authorization (already handled by @login_required and role logic in dashboard)
    # 2. Construct the actual path to the file in your secure storage (e.g., S3, Google Drive, Azure Blob Storage)
    # 3. Use the storage client library to serve the file.

    # For demonstration, we'll serve a dummy PDF.
    # Ensure a 'reports' directory exists in your static folder for this to work.

    # Construct a dummy filename for demonstration purposes
    filename_to_serve = "dummy_report.pdf"

    if report_type == 'financials':
        matching_def = next((item for item in FINANCIAL_REPORT_DEFINITIONS if item['display_name_part'] == display_name_part and item.get('basis', '') == (basis or '')), None)
        if matching_def:
            # Financial reports might have year-specific names for actual files
            actual_filename_prefix = f"{entity}{matching_def['file_suffix']}"
            # This is a simplification; real financial reports would likely be named with month/year
            # For demo, just use a generic dummy name or a specific one if available
            filename_to_serve = f"{actual_filename_prefix}.pdf" if "YTD" not in display_name_part else "dummy_ytd_report.pdf" # Example for YTD

    elif report_type == 'marketing_material':
        matching_def = next((item for item in MARKETING_REPORT_DEFINITIONS if item['display_name_part'] == display_name_part), None)
        if matching_def:
            actual_filename_prefix = f"{entity}{matching_def['file_suffix']}"
            filename_to_serve = f"{actual_filename_prefix}.pdf" # Example for marketing materials

    elif report_type == 'patient_specific':
        # For patient-specific reports, the filename would be derived from patient_id, date, and report type
        # E.g., f"patient_{patient_id}_{date}_lab_results.pdf"
        # For this demo, just serve a generic dummy.
        filename_to_serve = "dummy_patient_report.pdf"

    # Serve the dummy file from a 'static/reports' directory
    # You would replace this with actual file serving logic from your backend storage
    try:
        # Create a dummy reports directory and dummy PDF if they don't exist
        reports_dir = os.path.join(app.root_path, 'static', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        dummy_pdf_path = os.path.join(reports_dir, filename_to_serve)
        if not os.path.exists(dummy_pdf_path):
            with open(dummy_pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R/Parent 2 0 R>>endobj 4 0 obj<</Length 55>>stream\nBT /F1 24 Tf 100 700 Td (This is a dummy PDF report.) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000055 00000 n\n0000000104 00000 n\n0000000192 00000 n\ntrailer<</Size 5/Root 1 0 R>>startxref\n296\n%%EOF')
            print(f"Created dummy PDF: {dummy_pdf_path}")

        return send_from_directory(reports_dir, filename_to_serve, as_attachment=False) # as_attachment=False to display in browser
    except Exception as e:
        flash(f"Error serving report: {e}", 'error')
        return redirect(url_for('dashboard'))

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # Log the error for debugging
    app.logger.error(f"Server Error: {e}")
    return render_template('500.html'), 500

# --- Health Check (for Render.com or other deployment platforms) ---
@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
