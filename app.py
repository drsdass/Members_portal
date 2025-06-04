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
    'First Bio Genetics LLC', # Updated based on file names
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC', # Updated based on file names
    'AMICO Dx LLC', # Updated based on file names
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
    'Omar': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'JayM': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'ACG': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'NickT': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Admins with specific entity access based on your provided list
    'DarangT': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois'], 'role': 'admin'},
    'MelindaC': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC', 'Enviro Labs LLC'], 'role': 'admin'},
    'AghaA': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'Wenjun': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'AndreaM': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'BenM': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'SonnyA': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'NickC': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},
    'BobSilverang': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC', 'First Bio Lab of Illinois', 'AIM Laboratories LLC', 'AMICO Dx LLC'], 'role': 'admin'},
    'VinceO': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'admin'},

    # Example non-admin users (keeping original structure for these)
    'physician1@example.com': {'password_hash': generate_password_hash('doctorpass'), 'entities': ['First Bio Lab'], 'role': 'physician_provider'},
    'patient_doe': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient'}, # Patient role doesn't use entities for access directly, but good to keep consistent structure
    'patient_smith': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient'},
    'patient_johnson': {'password_hash': generate_password_hash('patientpass'), 'entities': [], 'role': 'patient'},
}


# --- Dummy Data for Reports (ensure this is consistent with your actual data.csv) ---
# This dictionary will hold dummy data for various reports.
# In a real application, this would come from a database or external files.
dummy_data = {
    'ReportID': [
        'R001', 'R002', 'R003', 'R004', 'R005',
        'R006', 'R007', 'R008', 'R009', 'R010',
        'R011', 'R012', 'R013', 'R014', 'R015',
        'R016', 'R017', # For AndrewS bonus report test
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
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A',
        'N/A',
        'N/A',
    ],
    'PatientLastName': [
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
        'N/A',
        'N/A',
        'N/A',
    ],
    'PatientDOB': [
        'N/A', 'N/A', 'N/A', 'N/A', 'N/A',
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
        'PatientID': ['P001', 'P001', 'P002', 'P001'],
        'PatientLastName': ['Doe', 'Doe', 'Smith', 'Doe'],
        'PatientDOB': ['1990-01-15', '1990-01-15', '1985-05-20', '1990-01-15'],
        'DateOfService': ['2024-05-01', '2024-04-10', '2024-05-05', '2024-03-20'],
        'ReportName': ['Comprehensive Metabolic Panel', 'Complete Blood Count', 'Thyroid Panel', 'Urinalysis'],
        'ReportFile': [
            'patient_report_P001_CMP_20240501.pdf',
            'patient_report_P001_CBC_20240410.pdf',
            'patient_report_P002_Thyroid_20240505.pdf',
            'patient_report_P001_Urinalysis_20240320.pdf'
        ],
        'Username': ['House_Patient', 'House_Patient', 'House_Patient', 'House_Patient'] # This will be the patient's username for login
    }
    patient_dummy_df = pd.DataFrame(patient_dummy_data)
    patient_dummy_df.to_csv('patient_data.csv', index=False)
    print("Created dummy patient_data.csv for demonstration.")
else:
    print("patient_data.csv already exists.")


# Load data
try:
    df = pd.read_csv('data.csv')
    patient_df = pd.read_csv('patient_data.csv')
except FileNotFoundError:
    print("Error: data.csv or patient_data.csv not found. Please ensure they are created.")
    df = pd.DataFrame(dummy_data) # Fallback to dummy data if file not found
    patient_df = pd.DataFrame(patient_dummy_data)


# --- Helper Functions ---
def get_user_role():
    """Returns the role of the currently logged-in user."""
    username = session.get('username')
    if username and username in users:
        return users[username]['role']
    return None

def get_user_entities():
    """Returns the list of entities the currently logged-in user has access to."""
    username = session.get('username')
    if username and username in users:
        return users[username]['entities']
    return []

def get_patient_info(last_name, dob, ssn4):
    """Retrieves patient information based on last name, DOB, and last 4 of SSN."""
    # In a real app, this would query a secure database.
    # For this dummy, we'll simulate a lookup.
    # NOTE: SSN is not stored in dummy_data for security, so we'll just check last name and DOB.
    # In a real scenario, you'd hash and compare SSN4.
    matching_patients = patient_df[
        (patient_df['PatientLastName'].str.lower() == last_name.lower()) &
        (patient_df['PatientDOB'] == dob)
    ]
    if not matching_patients.empty:
        # For simplicity, return the first match. In a real app, handle multiple matches or stricter criteria.
        return matching_patients.iloc[0]
    return None

def get_patient_reports(patient_id):
    """Retrieves reports for a given PatientID."""
    return patient_df[patient_df['PatientID'] == patient_id]


# --- Routes ---

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')

        if user_type == 'admin_physician':
            username = request.form.get('username')
            password = request.form.get('password')

            if username in users and check_password_hash(users[username]['password_hash'], password):
                session['username'] = username
                session['role'] = users[username]['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'danger')
        elif user_type == 'patient':
            last_name = request.form.get('patient_last_name')
            dob = request.form.get('patient_dob')
            ssn4 = request.form.get('patient_ssn4') # Last 4 digits of SSN

            patient_info = get_patient_info(last_name, dob, ssn4)

            if patient_info is not None:
                session['username'] = patient_info['Username'] # Use the dummy username for session
                session['role'] = 'patient'
                session['patient_id'] = patient_info['PatientID']
                flash('Patient login successful!', 'success')
                return redirect(url_for('patient_dashboard'))
            else:
                flash('Patient information not found. Please check your details.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))

    current_username = session['username']
    user_role = session['role']
    user_entities = get_user_entities()

    # Filter reports based on user's role and assigned entities
    if user_role == 'admin':
        if current_username in UNFILTERED_ACCESS_USERS:
            # Admins with unfiltered access see all reports
            filtered_df = df.copy()
            # For these users, also include reports where their username is explicitly listed
            # This handles cases like 'AndrewS Special Report'
            explicit_user_reports = df[df['Username'].apply(lambda x: current_username in x.split(','))]
            filtered_df = pd.concat([filtered_df, explicit_user_reports]).drop_duplicates().reset_index(drop=True)

        else:
            # Admins with specific entity access
            if not user_entities: # If an admin somehow has no entities assigned, show nothing
                filtered_df = pd.DataFrame(columns=df.columns)
            else:
                # Filter by entity
                filtered_df = df[df['Entity'].isin(user_entities)].copy()
                # Additionally, include reports explicitly assigned to this username or multi-user assignments
                explicit_user_reports = df[df['Username'].apply(lambda x: current_username in x.replace(' ', '').split(','))]
                filtered_df = pd.concat([filtered_df, explicit_user_reports]).drop_duplicates().reset_index(drop=True)

    elif user_role == 'physician_provider':
        # Physicians see reports from entities they are assigned to
        if not user_entities:
            filtered_df = pd.DataFrame(columns=df.columns)
        else:
            filtered_df = df[df['Entity'].isin(user_entities)].copy()
            # Physicians might also have reports explicitly assigned to their username
            explicit_user_reports = df[df['Username'].apply(lambda x: current_username in x.replace(' ', '').split(','))]
            filtered_df = pd.concat([filtered_df, explicit_user_reports]).drop_duplicates().reset_index(drop=True)
    else:
        # Other roles (like 'patient') should not access this dashboard directly
        flash('Access denied for your role.', 'danger')
        return redirect(url_for('login'))

    return render_template('dashboard.html', reports=filtered_df.to_dict('records'), username=current_username, role=user_role)

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'role' not in session or session['role'] != 'patient':
        flash('Please log in as a patient to access this dashboard.', 'warning')
        return redirect(url_for('login'))

    patient_id = session.get('patient_id')
    if not patient_id:
        flash('Patient ID not found in session.', 'danger')
        return redirect(url_for('login'))

    patient_reports = get_patient_reports(patient_id)

    return render_template('patient_dashboard.html', reports=patient_reports.to_dict('records'), patient_id=patient_id)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('patient_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/view_report/<report_file>')
def view_report(report_file):
    # In a real application, you would serve the actual PDF file
    # For this dummy app, we'll just show a placeholder message or a dummy PDF.
    # You would typically use send_from_directory here.
    return f"Viewing dummy report: {report_file}. In a real app, this would be the actual PDF."

if __name__ == '__main__':
    app.run(debug=True)
