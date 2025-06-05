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
    'AIM Laboratories LLC', # Updated based on file names
    'AMICO DX LLC', # Updated based on file names
    'AMICO Dx', # Keeping this for now as it was in the original list, but actual files use LLC
    'Enviro Labs LLC', # Updated based on file names
    'Stat Labs' # Updated based on file names
])

# --- Users with Unfiltered Access (for monthly bonus reports - remains unchanged) ---
# These specific admins will still get all data for bonus reports regardless of 'entities' filter.
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS']

# --- User Management (In-memory, with granular entity assignments for all roles) ---
# NOTE: For 'patient' role, 'username' is not used for login, but 'last_name', 'dob', 'ssn4'
# For 'physician_provider', 'email' is used as the username.
users = {
    # Full Access Admins (those explicitly confirmed for full access in previous turns)
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'BobS': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Representatives (with specific entity access)
    'SonnyA': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC'], 'role': 'rep'},
    'JayM': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab of Illinois', 'AMICO DX LLC'], 'role': 'rep'},
    'VinceO': {'password_hash': generate_password_hash('password1'), 'entities': ['Stat Labs', 'Enviro Labs LLC'], 'role': 'rep'},
    'NickC': {'password_hash': generate_password_hash('password1'), 'entities': ['AIM Laboratories LLC'], 'role': 'rep'},
    'Omar': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'rep'},
    'DarangT': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Genetics LLC'], 'role': 'rep'},

    # Business Development Manager (Access to a subset of entities)
    'ACG': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC'], 'role': 'business_dev_manager'},
    'AndrewS': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'AMICO DX LLC'], 'role': 'business_dev_manager'},
    'MelindaC': {'password_hash': generate_password_hash('password1'), 'entities': ['Stat Labs'], 'role': 'business_dev_manager'},

    # Physician/Provider (email based login)
    'dr.smith@example.com': {'password_hash': generate_password_hash('provider123'), 'entities': ['First Bio Lab'], 'role': 'physician_provider'},
    'dr.jones@example.2com': {'password_hash': generate_password_hash('provider123'), 'entities': ['AIM Laboratories LLC'], 'role': 'physician_provider'}, # Changed to .2com to avoid conflict

    # Patient (login handled separately by last_name, dob, ssn4)
    # The 'entities' here could represent the entities they have results from, but not used for login.
    'P001': {'last_name': 'Doe', 'dob': '1990-01-15', 'ssn4': '1234', 'role': 'patient', 'entities': ['First Bio Lab']},
    'P002': {'last_name': 'Smith', 'dob': '1985-05-20', 'ssn4': '5678', 'role': 'patient', 'entities': ['AIM Laboratories LLC']},
}

# --- Dummy Data Generation (for demonstration) ---
# Create a dummy data.csv if it doesn't exist for monthly bonus reports
if not os.path.exists('data.csv'):
    dummy_data = {
        'Entity': [
            'First Bio Lab', 'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois',
            'AIM Laboratories LLC', 'AMICO Dx LLC', 'Enviro Labs LLC', 'Stat Labs',
            'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab', 'AMICO Dx LLC',
            'AIM Laboratories LLC', 'First Bio Lab', 'First Bio Genetics LLC',
            'First Bio Lab', # For AndrewS specific bonus report test
            'AMICO DX LLC', # For AndrewS, MelindaC specific bonus report test
        ],
        'Month': [
            'January', 'February', 'January', 'February', 'January', 'February', 'January', 'February',
            'March', 'March', 'April', 'April', 'March', 'May', 'May',
            'January', # AndrewS test
            'February' # AndrewS, MelindaC test
        ],
        'Year': [
            2023, 2023, 2023, 2023, 2023, 2023, 2024, 2024,
            2024, 2024, 2024, 2024, 2025, 2025, 2025,
            2024, # AndrewS test
            2024 # AndrewS, MelindaC test
        ],
        'Total Revenue': [
            10000, 12000, 8000, 15000, 20000, 9000, 11000, 13000,
            10500, 8500, 16000, 21000, 9500, 11500, 13500,
            18000, # AndrewS test
            22000 # AndrewS, MelindaC test
        ],
        'Bonus': [
            1000, 1200, 800, 1500, 2000, 900, 1100, 1300,
            1050, 850, 1600, 2100, 950, 1150, 1350,
            1800, # AndrewS test
            2200, # AndrewS, MelindaC test
        ],
        'RepName': [ # For display in the table
            'House', 'House', 'Sonny A', 'Jay M', 'Bob S',
            'Satish D', 'ACG', 'Melinda C', 'Mina K',
            'Vince O', 'Nick C',
            'Ashlie T', 'Omar', 'Darang T',
            'Andrew', 'Jay M',
            'Andrew S', # Specific row for AndrewS bonus report test
            'Andrew S, Melinda C' # New row for multi-user test
        ],
        'Username': [ # NEW COLUMN - For filtering, must match login username
            'House_Patient', 'House_Patient', 'SonnyA', 'JayM', 'BobS',
            'SatishD', 'ACG', 'MelindaC', 'MinaK',
            'VinceO', 'NickC',
            'AshlieT', 'Omar', 'DarangT',
            'Andrew', 'JayM',
            'AndrewS', # Matches AndrewS login username
            'AndrewS,MelindaC' # Allows both AndrewS and MelindaC to see this line
        ],
        'PatientID': [ # For patient-specific filtering, N/A for non-patient reports
            'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A', 'N/A', 'N/A',
            'N/A', 'N/A',
            'N/A',
            'N/A'
        ]
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_df.to_csv('data.csv', index=False)
    print("Created dummy data.csv for demonstration.")

# Create dummy patient_data.csv if it doesn't exist
if not os.path.exists('patient_data.csv'):
    patient_dummy_data = {
        'PatientID': ['P001', 'P001', 'P002', 'P001', 'P001'],
        'PatientLastName': ['Doe', 'Doe', 'Smith', 'Doe', 'Doe'],
        'PatientDOB': ['1990-01-15', '1990-01-15', '1985-05-20', '1990-01-15', '1990-01-15'],
        'DateOfService': ['2024-05-01', '2024-04-10', '2024-05-05', '2024-03-20', '2024-05-15'],
        'ReportName': ['Comprehensive Metabolic Panel', 'Complete Blood Count', 'Thyroid Panel', 'Urinalysis', 'Lipid Panel'],
        'ReportFile': [
            'patient_report_P001_CMP_20240501.pdf',
            'patient_report_P001_CBC_20240410.pdf',
            'patient_report_P002_Thyroid_20240505.pdf',
            'patient_report_P001_Urinalysis_20240320.pdf',
            'patient_report_P001_Lipid_20240515.pdf'
        ],
        'Entity': ['First Bio Lab', 'First Bio Lab', 'AIM Laboratories LLC', 'First Bio Lab', 'First Bio Lab']
    }
    patient_df = pd.DataFrame(patient_dummy_data)
    patient_df.to_csv('patient_data.csv', index=False)
    print("Created dummy patient_data.csv for demonstration.")

# --- Helper Functions ---
def get_user_entities(username):
    """Retrieves entities accessible by a given username."""
    user_info = users.get(username)
    if user_info and 'entities' in user_info:
        return user_info['entities']
    return []

def get_current_year():
    return datetime.datetime.now().year

def get_available_years():
    # Example: current year and one year back/forward
    current_year = get_current_year()
    return sorted(list(set([current_year, current_year - 1, current_year + 1])))

def get_months():
    return [
        {'name': 'January', 'value': 'January'},
        {'name': 'February', 'value': 'February'},
        {'name': 'March', 'value': 'March'},
        {'name': 'April', 'value': 'April'},
        {'name': 'May', 'value': 'May'},
        {'name': 'June', 'value': 'June'},
        {'name': 'July', 'value': 'July'},
        {'name': 'August', 'value': 'August'},
        {'name': 'September', 'value': 'September'},
        {'name': 'October', 'value': 'October'},
        {'name': 'November', 'value': 'November'},
        {'name': 'December', 'value': 'December'},
    ]

# --- Flask Routes ---

@app.route('/')
def index():
    if 'username' in session or 'patient_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('select_role'))

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    session.pop('username', None) # Clear previous sessions
    session.pop('patient_id', None)
    session.pop('selected_role', None)

    if request.method == 'POST':
        selected_role = request.form.get('role')
        if selected_role:
            session['selected_role'] = selected_role
            if selected_role == 'patient':
                return redirect(url_for('login', role=selected_role))
            elif selected_role == 'physician_provider':
                return redirect(url_for('login', role=selected_role))
            else: # Admin, Rep, Business Dev Manager
                return redirect(url_for('login', role=selected_role))
        else:
            flash('Please select a role.', 'error')
    return render_template('role_selection.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    selected_role = session.get('selected_role')
    if not selected_role:
        return redirect(url_for('select_role'))

    error = None
    if request.method == 'POST':
        if selected_role == 'patient':
            last_name = request.form['last_name'].strip()
            dob = request.form['dob'].strip()
            ssn4 = request.form['ssn4'].strip()

            # Find patient by last_name, dob, and ssn4
            patient_found = False
            for patient_id, patient_info in users.items():
                if patient_info['role'] == 'patient' and \
                   patient_info['last_name'].lower() == last_name.lower() and \
                   patient_info['dob'] == dob and \
                   patient_info['ssn4'] == ssn4:
                    session['patient_id'] = patient_id
                    session['username'] = last_name # Storing last_name as username for display purposes
                    flash('Logged in successfully as Patient!', 'success')
                    return redirect(url_for('patient_results'))
            error = 'Invalid patient credentials.'

        elif selected_role == 'physician_provider':
            email = request.form['email'].strip()
            password = request.form['password'].strip()
            user_info = users.get(email)
            if user_info and user_info['role'] == 'physician_provider' and check_password_hash(user_info['password_hash'], password):
                session['username'] = email
                flash('Logged in successfully as Physician/Provider!', 'success')
                return redirect(url_for('select_report'))
            else:
                error = 'Invalid email or password.'

        else: # Admin, Rep, Business Dev Manager
            username = request.form['username'].strip()
            password = request.form['password'].strip()
            user_info = users.get(username)
            if user_info and user_info['role'] == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                flash(f'Logged in successfully as {selected_role.replace("_", " ").title()}!', 'success')
                return redirect(url_for('select_report'))
            else:
                error = 'Invalid username or password.'

    return render_template('login.html', selected_role=selected_role, error=error)

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register_physician.html')

        if email in users:
            flash('Email already registered.', 'error')
            return render_template('register_physician.html')

        # Add new physician
        users[email] = {
            'password_hash': generate_password_hash(password),
            'entities': [], # Newly registered physicians start with no entity access
            'role': 'physician_provider'
        }
        flash('Registration successful! Please log in.', 'success')
        session['selected_role'] = 'physician_provider' # Set role for redirect to login
        return redirect(url_for('login'))
    return render_template('register_physician.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session and 'patient_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('select_role'))
    
    current_username = session.get('username')
    current_role = session.get('selected_role')
    
    # Define available report types based on role
    available_report_types = []
    if current_role in ['admin', 'rep', 'business_dev_manager', 'physician_provider']:
        available_report_types = [
            {'name': 'Financial Reports', 'value': 'financial_reports'},
            {'name': 'Monthly Bonus Reports', 'value': 'monthly_bonus_reports'},
            {'name': 'Requisition Reports', 'value': 'requisition_reports'},
            {'name': 'Marketing Material', 'value': 'marketing_material'}
        ]
        if current_role == 'physician_provider':
             # Physicians can also view patient reports (e.g., for their own patients)
             available_report_types.append({'name': 'Patient Reports', 'value': 'patient_reports'})
    elif current_role == 'patient':
        # Patients can only see their own reports
        return redirect(url_for('patient_results'))
    else:
        flash('Unauthorized access to report selection.', 'error')
        return redirect(url_for('logout'))

    # Filter MASTER_ENTITIES based on user's assigned entities
    user_info = users.get(current_username)
    if current_role == 'admin' or current_username in UNFILTERED_ACCESS_USERS: # Admins and special users see all
        user_accessible_entities = MASTER_ENTITIES
    elif user_info and 'entities' in user_info:
        user_accessible_entities = sorted(list(set(user_info['entities'])))
    else:
        user_accessible_entities = []

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        entity_name = request.form.get('entity_name')
        month = request.form.get('month')
        year = request.form.get('year')

        # Basic validation
        if not report_type or not entity_name:
            flash('Please select both Report Type and Entity.', 'error')
            return render_template(
                'select_report.html',
                available_report_types=available_report_types,
                master_entities=user_accessible_entities,
                months=get_months(),
                years=get_available_years()
            )

        # Store selection in session
        session['report_type'] = report_type
        session['selected_entity'] = entity_name
        session['selected_month'] = month if month else None
        session['selected_year'] = year if year else None

        return redirect(url_for('dashboard'))

    # Initial GET request
    return render_template(
        'select_report.html',
        available_report_types=available_report_types,
        master_entities=user_accessible_entities,
        months=get_months(),
        years=get_available_years()
    )

@app.route('/dashboard')
def dashboard():
    if 'username' not in session and 'patient_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('select_role'))
    
    current_username = session.get('username')
    current_role = session.get('selected_role')
    selected_entity = session.get('selected_entity')
    report_type = session.get('report_type')
    selected_month = session.get('selected_month')
    selected_year = session.get('selected_year')

    # Redirect patients to their specific results page
    if current_role == 'patient':
        return redirect(url_for('patient_results'))

    # Check if necessary selections are made
    if not report_type or not selected_entity:
        flash('Please select a report type and entity.', 'warning')
        return redirect(url_for('select_report'))

    # Authorization check for entity access
    user_entities = get_user_entities(current_username)
    if current_role != 'admin' and current_username not in UNFILTERED_ACCESS_USERS:
        if selected_entity not in user_entities:
            flash(f'You are not authorized to view reports for {selected_entity}.', 'error')
            return render_template('unauthorized.html', message=f'Access Denied: You do not have permission to view reports for {selected_entity}.')

    files = [] # To store list of PDF files
    data = [] # To store dataframe data for display

    if report_type == 'financial_reports':
        # Example dummy PDF files for financial reports
        # These are just examples, you would replace this with actual file fetching logic
        # Filename format: Financials_EntityName_Month_Year.pdf
        # Note: AMICO DX LLC files are named 'AMICO Dx LLC' in file system.
        financial_files_data = [
            {'name': 'Financials - First Bio Lab - Jan 2024', 'filename': 'Financials_First Bio Lab_January_2024.pdf', 'entity': 'First Bio Lab', 'month': 'January', 'year': 2024},
            {'name': 'Financials - First Bio Lab - Feb 2024', 'filename': 'Financials_First Bio Lab_February_2024.pdf', 'entity': 'First Bio Lab', 'month': 'February', 'year': 2024},
            {'name': 'Financials - First Bio Genetics LLC - Jan 2024', 'filename': 'Financials_First Bio Genetics LLC_January_2024.pdf', 'entity': 'First Bio Genetics LLC', 'month': 'January', 'year': 2024},
            {'name': 'Financials - AMICO Dx LLC - Feb 2024', 'filename': 'Financials_AMICO Dx LLC_February_2024.pdf', 'entity': 'AMICO Dx LLC', 'month': 'February', 'year': 2024},
            {'name': 'Financials - AIM Laboratories LLC - Mar 2024', 'filename': 'Financials_AIM Laboratories LLC_March_2024.pdf', 'entity': 'AIM Laboratories LLC', 'month': 'March', 'year': 2024},
            {'name': 'Financials - First Bio Lab of Illinois - Apr 2024', 'filename': 'Financials_First Bio Lab of Illinois_April_2024.pdf', 'entity': 'First Bio Lab of Illinois', 'month': 'April', 'year': 2024},
            {'name': 'Financials - Stat Labs - May 2024', 'filename': 'Financials_Stat Labs_May_2024.pdf', 'entity': 'Stat Labs', 'month': 'May', 'year': 2024},
            {'name': 'Financials - Enviro Labs LLC - Jun 2024', 'filename': 'Financials_Enviro Labs LLC_June_2024.pdf', 'entity': 'Enviro Labs LLC', 'month': 'June', 'year': 2024},
            # Add more dummy files as needed
        ]
        for f in financial_files_data:
            if f['entity'] == selected_entity and \
               (not selected_month or f['month'] == selected_month) and \
               (not selected_year or f['year'] == int(selected_year)):
                files.append({'name': f['name'], 'filename': f['filename']})

    elif report_type == 'monthly_bonus_reports':
        try:
            df = pd.read_csv('data.csv')

            # Filter by entity
            filtered_df = df[df['Entity'] == selected_entity]

            # Further filter by month and year if selected
            if selected_month:
                filtered_df = filtered_df[filtered_df['Month'] == selected_month]
            if selected_year:
                filtered_df = filtered_df[filtered_df['Year'] == int(selected_year)]

            # Filter by username for non-admin/unfiltered users
            if current_username not in UNFILTERED_ACCESS_USERS:
                # Handle comma-separated usernames in the 'Username' column
                filtered_df = filtered_df[
                    filtered_df['Username'].apply(lambda x: current_username in [u.strip() for u in x.split(',')])
                ]

            if not filtered_df.empty:
                # If a specific month and year are selected, generate a dummy PDF link
                if selected_month and selected_year:
                    pdf_name = f"{selected_entity.replace(' ', '_')}_Bonus_Report_{selected_month}_{selected_year}.pdf"
                    files.append({'name': f"Monthly Bonus Report - {selected_entity} - {selected_month} {selected_year}", 'filename': pdf_name})
                    # You might also want to show a small preview of the data even when a PDF is generated
                    data = filtered_df.head().to_dict(orient='records')
                else:
                    # If no specific month/year, show the table data (e.g., all bonus data for the entity/user)
                    data = filtered_df.to_dict(orient='records')
            else:
                flash('No monthly bonus report data found for your selection.', 'info')

        except FileNotFoundError:
            flash('Monthly bonus reports data file not found.', 'error')
        except Exception as e:
            flash(f'An error occurred: {e}', 'error')

    elif report_type == 'requisition_reports':
        # Dummy PDF files for requisition reports (similar to financial reports)
        # Filename format: Requisitions_EntityName_Month_Year.pdf
        requisition_files_data = [
            {'name': 'Requisitions - First Bio Lab - Q1 2024', 'filename': 'Requisitions_First Bio Lab_Q1_2024.pdf', 'entity': 'First Bio Lab', 'month': 'Q1', 'year': 2024},
            {'name': 'Requisitions - First Bio Genetics LLC - Q2 2024', 'filename': 'Requisitions_First Bio Genetics LLC_Q2_2024.pdf', 'entity': 'First Bio Genetics LLC', 'month': 'Q2', 'year': 2024},
            # Add more dummy files as needed
        ]
        for f in requisition_files_data:
            # Assuming month/year can be 'Q1', 'Q2' etc. or specific months
            month_match = not selected_month or (f['month'] == selected_month)
            year_match = not selected_year or (f['year'] == int(selected_year))

            if f['entity'] == selected_entity and month_match and year_match:
                files.append({'name': f['name'], 'filename': f['filename']})

    elif report_type == 'marketing_material':
        # Dummy PDF files for marketing materials (e.g., brochures, flyers)
        marketing_files_data = [
            {'name': 'Marketing Brochure - First Bio Lab', 'filename': 'Marketing_Brochure_First Bio Lab.pdf', 'entity': 'First Bio Lab'},
            {'name': 'Service Flyer - First Bio Genetics LLC', 'filename': 'Service_Flyer_First Bio Genetics LLC.pdf', 'entity': 'First Bio Genetics LLC'},
            {'name': 'Company Profile - AIM Laboratories LLC', 'filename': 'Company_Profile_AIM Laboratories LLC.pdf', 'entity': 'AIM Laboratories LLC'},
            # Add more dummy files as needed
        ]
        for f in marketing_files_data:
            if f['entity'] == selected_entity:
                files.append({'name': f['name'], 'filename': f['filename']})

    # Render dashboard template with relevant data
    return render_template(
        'dashboard.html',
        current_username=current_username,
        selected_entity=selected_entity,
        report_type=report_type,
        selected_month=selected_month,
        selected_year=selected_year,
        files=files, # List of files to display
        data=data,   # DataFrame data to display (if no specific files or for preview)
        months=get_months(), # Pass for dropdown in sidebar if needed
        years=get_available_years() # Pass for dropdown in sidebar if needed
    )

@app.route('/patient_results')
def patient_results():
    patient_id = session.get('patient_id')
    patient_name = session.get('username') # This would be last_name for patients

    if not patient_id:
        flash('Patient not logged in.', 'error')
        return redirect(url_for('login'))

    try:
        df_patients = pd.read_csv('patient_data.csv')
        patient_results_df = df_patients[df_patients['PatientID'] == patient_id]

        if not patient_results_df.empty:
            # Group reports by DateOfService for display
            results_by_dos = {}
            for _, row in patient_results_df.iterrows():
                dos = row['DateOfService']
                if dos not in results_by_dos:
                    results_by_dos[dos] = []
                # Create a dummy link for the report file in static folder
                report_file_path = url_for('static', filename=row['ReportFile'])
                results_by_dos[dos].append({
                    'name': row['ReportName'],
                    'webViewLink': report_file_path # Use this for direct link to dummy PDF
                })
            return render_template('patient_results.html', patient_name=patient_name, results_by_dos=results_by_dos)
        else:
            return render_template('patient_results.html', patient_name=patient_name, message='No lab results found for your ID.')

    except FileNotFoundError:
        flash('Patient data file not found.', 'error')
        return render_template('patient_results.html', patient_name=patient_name, message='Error: Patient data file not found.')
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
        return render_template('patient_results.html', patient_name=patient_name, message=f'An error occurred: {e}')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('patient_id', None)
    session.pop('selected_role', None)
    session.pop('report_type', None)
    session.pop('selected_entity', None)
    session.pop('selected_month', None)
    session.pop('selected_year', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('select_role'))

if __name__ == '__main__':
    # Create a 'static' folder if it doesn't exist to simulate dummy PDFs
    if not os.path.exists('static'):
        os.makedirs('static')

    # Create dummy PDF files in the 'static' folder if they don't exist
    dummy_pdf_names = [
        'Financials_First Bio Lab_January_2024.pdf',
        'Financials_First Bio Lab_February_2024.pdf',
        'Financials_First Bio Genetics LLC_January_2024.pdf',
        'Financials_AMICO Dx LLC_February_2024.pdf',
        'Financials_AIM Laboratories LLC_March_2024.pdf',
        'Financials_First Bio Lab of Illinois_April_2024.pdf',
        'Financials_Stat Labs_May_2024.pdf',
        'Financials_Enviro Labs LLC_June_2024.pdf',
        'Requisitions_First Bio Lab_Q1_2024.pdf',
        'Requisitions_First Bio Genetics LLC_Q2_2024.pdf',
        'Marketing_Brochure_First Bio Lab.pdf',
        'Service_Flyer_First Bio Genetics LLC.pdf',
        'Company_Profile_AIM Laboratories LLC.pdf',
        'First_Bio_Lab_Bonus_Report_January_2024.pdf', # Example bonus PDF
        'AMICO_DX_LLC_Bonus_Report_February_2024.pdf', # Example bonus PDF for new multi-user test
        'patient_report_P001_CMP_20240501.pdf',
        'patient_report_P001_CBC_20240410.pdf',
        'patient_report_P002_Thyroid_20240505.pdf',
        'patient_report_P001_Urinalysis_20240320.pdf',
        'patient_report_P001_Lipid_20240515.pdf'
    ]

    for pdf_name in dummy_pdf_names:
        file_path = os.path.join('static', pdf_name)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(f"This is a dummy PDF content for {pdf_name}")
            print(f"Created dummy PDF: {file_path}")

    app.run(debug=True)
