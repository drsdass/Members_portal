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
# These specific admins will still get all data for bonus reports regardless of 'entities' filter.
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS']

# --- User Management (In-memory, with granular entity assignments for all roles) ---
# NOTE: For 'patient' role, 'username' is not used for login, but 'last_name', 'dob', 'ssn4'
# For 'physician_provider', 'email' is used as the username.
users = {
    # Full Access Admins (those explicitly confirmed for full access in previous turns)
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
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
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': ['AIM Laboratories LLC', 'First Bio Genetics LLC'], 'role': 'rep'}, # Changed role from admin to rep as per previous turns

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


# --- Dummy Data for Reports (ensure this is consistent with your actual data.csv) ---
# This dictionary will hold dummy data for various reports.
# In a real application, this would come from a database or external files.
dummy_data = {
    'ReportID': [
        'R001', 'R002', 'R003', 'R004', 'R005',
        'R006', 'R007', 'R008', 'R009', 'R010',
        'R011', 'R012', 'R013', 'R014', 'R015',
        'R016', # For bonus report
        'R017', # For AndrewS specific report
        'R018' # For multi-user test
    ],
    'ReportName': [
        'Monthly Sales Report', 'Quarterly Financials', 'Annual Performance Review', 'Marketing Campaign Analysis', 'HR Onboarding Metrics',
        'Lab Test Results', 'Clinical Trial Data', 'Research Study Findings', 'Patient Demographics', 'Inventory Audit',
        'Supply Chain Efficiency', 'Customer Feedback Analysis', 'Website Traffic Report', 'Server Health Check', 'Network Security Audit',
        'Bonus Report Q1', # Example for bonus report
        'AndrewS Special Report', # Specific report for AndrewS
        'Joint Project Report' # Report for AndrewS, MelindaC
    ],
    'ReportDate': [
        '2024-05-01', '2024-04-15', '2024-03-31', '2024-05-10', '2024-04-20',
        '2024-05-02', '2024-04-25', '2024-03-10', '2024-05-05', '2024-04-01',
        '2024-05-12', '2024-04-05', '2024-03-15', '2024-05-08', '2024-04-12',
        '2024-03-01', # Date for bonus report
        '2024-05-15', # Date for AndrewS report
        '2024-05-20' # Date for multi-user report
    ],
    'Entity': [ # This column determines which entity the report belongs to
        'First Bio Lab', 'First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC',
        'AMICO Dx LLC', 'Enviro Labs LLC', 'Stat Labs', 'First Bio Lab', 'First Bio Genetics LLC',
        'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC', 'Enviro Labs LLC', 'Stat Labs',
        'First Bio Lab', # Entity for bonus report
        'First Bio Lab', # Entity for AndrewS report
        'First Bio Lab' # Entity for multi-user report
    ],
    'AccessLevel': [ # This column is for display in the table
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
    'PatientID': [
        'PAT001', 'PAT001', 'N/A', 'N/A', 'N/A', # Added PAT001 for House_Patient
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A',
        'N/A',
        'N/A',
    ],
    'PatientLastName': [
        'House', 'House', 'N/A', 'N/A', 'N/A', # Added House for House_Patient
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A',
        'N/A',
        'N/A',
    ],
    'PatientDOB': [
        '1980-05-15', '1980-05-15', 'N/A', 'N/A', 'N/A', # Added DOB for House_Patient
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A',
        'N/A',
        'N/A',
    ],
    'ReportFile': [ # Dummy file names for demonstration
        'report_R001.pdf', 'report_R002.pdf', 'report_R003.pdf', 'report_R004.pdf', 'report_R005.pdf',
        'report_R006.pdf', 'report_R007.pdf', 'report_R008.pdf', 'report_R009.pdf', 'report_R010.pdf',
        'report_R011.pdf', 'report_R012.pdf', 'report_R013.pdf', 'report_R014.pdf', 'report_R015.pdf',
        'report_R016.pdf',
        'report_R017.pdf',
        'report_R018.pdf',
    ]
}
dummy_df = pd.DataFrame(dummy_data)
dummy_df.to_csv('data.csv', index=False)
print("Created dummy data.csv for demonstration.")

# Create dummy patient_data.csv if it doesn't exist
if not os.path.exists('patient_data.csv'):
    patient_dummy_data = {
        'PatientID': ['PAT001', 'PAT001', 'PAT002', 'PAT001'],
        'PatientLastName': ['House', 'House', 'Doe', 'House'],
        'PatientDOB': ['1980-05-15', '1980-05-15', '1990-01-01', '1980-05-15'],
        'DateOfService': ['2024-05-01', '2024-04-10', '2024-05-05', '2024-03-20'],
        'ReportName': ['Comprehensive Metabolic Panel', 'Complete Blood Count', 'Thyroid Panel', 'Urinalysis'],
        'ReportFile': [
            'patient_report_PAT001_CMP_20240501.pdf',
            'patient_report_PAT001_CBC_20240410.pdf',
            'patient_report_PAT002_Thyroid_20240505.pdf',
            'patient_report_PAT001_Urinalysis_20240320.pdf'
        ],
        'Username': ['House_Patient', 'House_Patient', 'PatientUser1', 'House_Patient'] # This will be the patient's username for login
    }
    patient_dummy_df = pd.DataFrame(patient_dummy_data)
    patient_dummy_df.to_csv('patient_data.csv', index=False)
    print("Created dummy patient_data.csv for demonstration.")
else:
    print("patient_data.csv already exists.")


# --- Data Loading (Optimized: Load once at app startup) ---
# Initialize as empty to avoid error if file not found
df = pd.DataFrame()
patient_df = pd.DataFrame()

try:
    df = pd.read_csv('data.csv', parse_dates=['ReportDate']) # Changed 'Date' to 'ReportDate' to match dummy_data
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py. Dummy data will be created.")
    df = pd.DataFrame(dummy_data) # Fallback to dummy data if file not found
except Exception as e:
    print(f"An error occurred while loading data.csv: {e}")

try:
    patient_df = pd.read_csv('patient_data.csv', parse_dates=['DateOfService'])
    print("patient_data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: patient_data.csv not found. Please ensure the file is in the same directory as app.py. Dummy patient data will be created.")
    patient_df = pd.DataFrame(patient_dummy_data) # Fallback to dummy data if file not found
except Exception as e:
    print(f"An error occurred while loading patient_data.csv: {e}")


# --- Helper function to get available report types for a user role ---
def get_available_report_types(user_role):
    """Returns the list of report types available for a given user role."""
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
        if selected_role in ['physician_provider', 'patient', 'business_dev_manager', 'admin', 'rep']:
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
    Login logic varies based on the selected role (patient, physician, other).
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
                flash('Patient login successful!', 'success')
                return redirect(url_for('patient_results'))
            else:
                error_message = 'Invalid patient details.'
                flash(error_message, 'danger')
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
                flash('Physician login successful!', 'success')
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid email or password.'
                flash(error_message, 'danger')
        else:
            # All other roles (admin, rep, and business_dev_manager) use Username and Password
            username = request.form.get('username')
            password = request.form.get('password')
            
            user_info = users.get(username)

            if user_info and user_info.get('role') == selected_role and check_password_hash(user_info['password_hash'], password):
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('select_report'))
            else:
                error_message = 'Invalid username or password.'
                flash(error_message, 'danger')
    return render_template('login.html', error=error_message, selected_role=selected_role)

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    """Handles physician registration."""
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
        
        # Generate a unique username key for the new physician
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
    """Displays patient-specific reports based on their PatientID."""
    if 'username' not in session or users[session['username']]['role'] != 'patient':
        flash("Access denied. Please log in as a patient.", "error")
        return redirect(url_for('login'))

    patient_username = session['username']
    patient_id = session.get('patient_id')
    patient_last_name = users[patient_username]['patient_details']['last_name']

    # Ensure patient_df is loaded and has necessary columns
    if patient_df.empty or 'PatientID' not in patient_df.columns or 'DateOfService' not in patient_df.columns:
        flash("Patient data is not available or incorrectly structured. Please contact support.", "error")
        return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos={})

    patient_data = patient_df[patient_df['PatientID'] == patient_id].copy()

    if patient_data.empty:
        return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos={}, message="No results found for your patient ID.")

    # Ensure 'DateOfService' is datetime type for sorting
    if not pd.api.types.is_datetime64_any_dtype(patient_data['DateOfService']):
        patient_data['DateOfService'] = pd.to_datetime(patient_data['DateOfService'])

    patient_data = patient_data.sort_values(by='DateOfService', ascending=False)

    results_by_dos = {}
    for index, row in patient_data.iterrows():
        dos = row['DateOfService'].strftime('%Y-%m-%d')
        if dos not in results_by_dos:
            results_by_dos[dos] = []
        
        # Construct a report name and a dummy PDF filename
        report_name = f"{row['ReportName']} - {dos}"
        # Sanitize filename to avoid issues with special characters
        sanitized_report_name = re.sub(r'[^\w\-_\.]', '', row['ReportName'].replace(' ', '_'))
        dummy_pdf_filename = f"Patient_{patient_id}_DOS_{dos}_{sanitized_report_name}.pdf"
        
        results_by_dos[dos].append({
            'name': report_name,
            'webViewLink': url_for('static', filename=dummy_pdf_filename)
        })
        
        # Create a dummy PDF file if it doesn't exist for demonstration purposes
        filepath = os.path.join(app.static_folder, dummy_pdf_filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file for Patient {patient_id}, Date of Service {dos}, Report: {row['ReportName']}.")
            print(f"Created dummy patient result file: {filepath}")

    return render_template('patient_results.html', patient_name=patient_last_name, results_by_dos=results_by_dos)


@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    """
    Allows non-patient users (admins, physicians, reps, business dev managers)
    to select report type, entity, month, and year.
    """
    if 'username' not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role']
    user_authorized_entities = users[username]['entities']

    # Filter MASTER_ENTITIES to show only those the user is authorized for
    display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Use helper function to get available report types for the current user's role
    available_report_types = get_available_report_types(user_role)

    # Populate months and years for the dropdowns
    months = [
        {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
        {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
        {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
        {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
        {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
        {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'}
    ]
    current_year = datetime.datetime.now().year
    years = list(range(current_year - 2, current_year + 2)) # Years from 2 years ago to 1 year in future

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
        
        # Authorization check for the selected entity
        if selected_entity not in user_authorized_entities and username not in UNFILTERED_ACCESS_USERS:
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
        
        # Store selections in session for use in the dashboard
        session['report_type'] = report_type
        session['selected_entity'] = selected_entity
        session['selected_month'] = int(selected_month) if selected_month else None
        session['selected_year'] = int(selected_year) if selected_year else None
        
        return redirect(url_for('dashboard'))
    
    # Render the form for GET requests
    return render_template(
        'select_report.html',
        master_entities=display_entities,
        available_report_types=available_report_types,
        months=months,
        years=years
    )

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """
    Displays reports based on user selections and authorization.
    This is the main dashboard for non-patient roles.
    """
    if 'username' not in session:
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for('login'))

    username = session['username']
    user_role = users[username]['role']
    user_authorized_entities = users[username]['entities']

    # Populate months and years for the dropdowns (if needed in dashboard template)
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

    # Retrieve selections from session or form submission
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
        # Load selections from session for GET requests (e.g., after redirect from select_report)
        selected_entity = session.get('selected_entity')
        report_type = session.get('report_type')
        selected_month = session.get('selected_month')
        selected_year = session.get('selected_year')

    # Filter MASTER_ENTITIES to show only those the user is authorized for
    display_entities = [entity for entity in MASTER_ENTITIES if entity in user_authorized_entities]

    # Re-check authorization for the selected entity (important if user directly navigates or session expires)
    if selected_entity and selected_entity not in user_authorized_entities and username not in UNFILTERED_ACCESS_USERS:
        if not user_authorized_entities:
            flash("You do not have any entities assigned to view reports. Please contact support.", "error")
            return render_template('unauthorized.html', message="You do not have any entities assigned to view reports. Please contact support.")
        flash(f"You are not authorized to view reports for '{selected_entity}'. Please select an authorized entity.", "error")
        return render_template(
            'select_report.html',
            master_entities=display_entities,
            available_report_types=get_available_report_types(user_role),
            months=months,
            years=years
        )

    filtered_data = pd.DataFrame()
    files = [] # List to hold report files to display

    # Apply filtering based on user role and selections
    if username in UNFILTERED_ACCESS_USERS:
        # Unfiltered access users see all data in df
        if not df.empty:
            filtered_data = df.copy()
            print(f"User {username} has unfiltered access. Displaying all data.")
    elif not df.empty and 'Entity' in df.columns:
        # Filter by selected entity if one is chosen and user is authorized
        if selected_entity:
            filtered_data = df[df['Entity'] == selected_entity].copy()
        else:
            # If no entity is selected, but user has limited access, show only their authorized entities' data
            filtered_data = df[df['Entity'].isin(user_authorized_entities)].copy()
    else:
        print(f"Warning: 'Entity' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")


    # Apply date filtering if month and year are selected
    if selected_month and selected_year and 'ReportDate' in filtered_data.columns: # Changed 'Date' to 'ReportDate'
        if not pd.api.types.is_datetime64_any_dtype(filtered_data['ReportDate']): # Changed 'Date' to 'ReportDate'
            filtered_data['ReportDate'] = pd.to_datetime(filtered_data['ReportDate']) # Changed 'Date' to 'ReportDate'
        filtered_data = filtered_data[
            (filtered_data['ReportDate'].dt.month == selected_month) & \
            (filtered_data['ReportDate'].dt.year == selected_year)
        ]

    # Handle specific report types
    if report_type == 'financials':
        if selected_year:
            # Generate financial report filenames based on definitions and selected year/entity
            for definition in FINANCIAL_REPORT_DEFINITIONS:
                # Check if 'applicable_years' is defined and if the selected year is in it
                if 'applicable_years' in definition and selected_year not in definition['applicable_years']:
                    continue # Skip if not applicable for the selected year

                file_name_prefix = selected_entity.replace(' ', '_').replace('.', '') # Sanitize entity name for filename
                full_filename = f"{file_name_prefix}_{selected_year}{definition['file_suffix']}.pdf"
                display_name = f"{selected_entity} {selected_year} {definition['display_name_part']} ({definition['basis']})"
                files.append({'name': display_name, 'filename': full_filename})
                
                # Create dummy PDF file if it doesn't exist
                filepath = os.path.join(app.static_folder, full_filename)
                if not os.path.exists(filepath):
                    with open(filepath, 'w') as f:
                        f.write(f"This is a dummy PDF for {display_name}.")
                    print(f"Created dummy financial report file: {filepath}")
        else:
            flash("Please select a year for financial reports.", "info")
    elif report_type == 'monthly_bonus':
        if 'Username' in filtered_data.columns:
            normalized_username = username.strip().lower()
            # Filter for reports where the current username is explicitly listed in the 'Username' column
            # This handles both single and comma-separated usernames (e.g., 'AndrewS' or 'AndrewS,MelindaC')
            filtered_data['Username'] = filtered_data['Username'].astype(str)
            regex_pattern = r'\b' + re.escape(normalized_username) + r'\b'
            filtered_data = filtered_data[
                filtered_data['Username'].str.strip().str.lower().str.contains(regex_pattern, na=False)
            ]
            
            if not filtered_data.empty:
                files = [
                    {'name': f"Monthly Bonus Report - {row['Entity']} - {row['ReportDate'].strftime('%Y-%m')}", # Changed 'Date' to 'ReportDate'
                     'filename': f"monthly_bonus_report_{row['Entity'].replace(' ', '_').replace('.', '')}_{row['ReportDate'].strftime('%Y%m')}.pdf"} # Changed 'Date' to 'ReportDate'
                    for index, row in filtered_data.iterrows()
                ]
                # Create dummy PDF files for monthly bonus reports
                for file_info in files:
                    filepath = os.path.join(app.static_folder, file_info['filename'])
                    if not os.path.exists(filepath):
                        with open(filepath, 'w') as f:
                            f.write(f"This is a dummy PDF for {file_info['name']}.")
                        print(f"Created dummy monthly bonus report file: {filepath}")
            else:
                flash("No monthly bonus reports found for your selection criteria or username.", "info")
        else:
            flash("The 'Username' column is missing in data.csv, cannot filter monthly bonus reports.", "error")
    elif report_type == 'requisitions':
        # Dummy requisitions data
        files = [
            {'name': 'Requisition Form 1', 'filename': 'requisition_form_1.pdf'},
            {'name': 'Requisition Guidelines', 'filename': 'requisition_guidelines.pdf'}
        ]
        # Create dummy PDF files for requisitions
        for file_info in files:
            filepath = os.path.join(app.static_folder, file_info['filename'])
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"This is a dummy PDF for {file_info['name']}.")
                print(f"Created dummy requisition file: {filepath}")
    elif report_type == 'marketing_material':
        # Dummy marketing material data
        files = [
            {'name': 'Brochure - Services', 'filename': 'brochure_services.pdf'},
            {'name': 'Company Profile', 'filename': 'company_profile.pdf'}
        ]
        # Create dummy PDF files for marketing material
        for file_info in files:
            filepath = os.path.join(app.static_folder, file_info['filename'])
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(f"This is a dummy PDF for {file_info['name']}.")
                print(f"Created dummy marketing material file: {filepath}")
    elif report_type == 'patient_reports':
        # This report type redirects to the patient_results route for patient-specific views
        # Non-patient users (admins, physicians) would typically search for a patient here
        # For now, we'll just show a message or redirect if a patient ID is somehow in session
        if 'patient_id' in session:
            return redirect(url_for('patient_results'))
        else:
            flash("Please search for a patient to view patient-specific reports.", "info")
            files = [] # No files directly displayed here
    
    # Prepare data for display in the table (e.g., first few rows of filtered_data)
    data_for_display = {}
    if not filtered_data.empty:
        data_for_display = filtered_data.head().to_dict(orient='records') # Display first 5 records as example

    return render_template(
        'dashboard.html',
        current_username=username,
        selected_entity=selected_entity,
        report_type=report_type,
        months=months,
        years=years,
        selected_month=selected_month,
        selected_year=selected_year,
        files=files, # List of generated report files
        data=data_for_display, # Sample data from the filtered dataframe
        master_entities=display_entities, # Entities the current user can see
        available_report_types=get_available_report_types(user_role) # Report types for the current role
    )

@app.route('/logout')
def logout():
    """Logs out the current user and clears session data."""
    session.pop('username', None)
    session.pop('selected_role', None)
    session.pop('patient_id', None)
    session.pop('report_type', None)
    session.pop('selected_entity', None)
    session.pop('selected_month', None)
    session.pop('selected_year', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('select_role')) # Redirect to role selection after logout

if __name__ == '__main__':
    # Ensure the 'static' folder exists for dummy PDF files
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)
