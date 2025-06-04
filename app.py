import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re # Import the regular expression module

# Initialize the Flask application
app = Flask(__name__)

#--- Configuration
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# --- Master List of All Entities (RESTRICTED to the 7 core company/lab entities, updated with LLC) ---
MASTER_ENTITIES = sorted([
    'First Bio Lab',
    'First Bio Genetics LLC', # Updated based on file names
    'First Bio Lab of Illinois',
    'AIM Laboratories LLC', # Updated based on file names
    'AMICO DX LLC',
    # Updated based on file names
    'AMICO Dx', # Keeping this for now as it was in the original list, but actual files use LLC
    'Enviro Labs LLC',
    'Stat Labs'
])

# --- Users with Unfiltered Access (for existing 'members' role) ---
UNFILTERED_ACCESS_USERS = ['AshlieT', 'MinaK', 'BobS', 'SatishD']

# --- User Management (In-memory, with individual names as usernames and their roles) ---
# NOTE: For 'patient' role, 'username' is not used for login, but 'last_name', 'dob', 'ssn4'
# For 'physician_provider', 'email' is used as the username.
users = {
    'AshlieT': {'password': generate_password_hash('AshliePass'), 'role': 'admin'},
    'MinaK': {'password': generate_password_hash('MinaPass'), 'role': 'admin'},
    'BobS': {'password': generate_password_hash('BobPass'), 'role': 'business_development_manager'},
    'SatishD': {'password': generate_password_hash('SatishPass'), 'role': 'business_development_manager'},
    'physician@example.com': {'password': generate_password_hash('PhysicianPass'), 'role': 'physician_provider', 'name': 'Dr. Alex Smith'},
    'test@provider.com': {'password': generate_password_hash('ProviderPass'), 'role': 'physician_provider', 'name': 'Dr. Jane Doe'}
}

# --- Patient Data (In-memory for demonstration) ---
patients = {
    'Doe': {'1990-01-15': {'1234': {'PatientID': 'P001'}}},
    'Smith': {'1985-05-20': {'5678': {'PatientID': 'P002'}}}
}

# --- Report Data (In-memory, mapping PatientID to a list of reports) ---
reports_data = {
    'P001': [
        {'ReportName': 'Comprehensive Metabolic Panel', 'DateOfService': '2024-05-01', 'ReportFile': 'patient_report_P001_CMP_20240501.pdf'},
        {'ReportName': 'Complete Blood Count', 'DateOfService': '2024-04-10', 'ReportFile': 'patient_report_P001_CBC_20240410.pdf'}
    ],
    'P002': [
        {'ReportName': 'Thyroid Panel', 'DateOfService': '2024-05-05', 'ReportFile': 'patient_report_P002_Thyroid_20240505.pdf'},
    ]
}

# Ensure 'static' folder exists and create dummy PDF files if they don't
if not os.path.exists('static'):
    os.makedirs('static')

dummy_pdf_files = [
    'patient_report_P001_CMP_20240501.pdf',
    'patient_report_P001_CBC_20240410.pdf',
    'patient_report_P002_Thyroid_20240505.pdf'
]

for filename in dummy_pdf_files:
    filepath = os.path.join('static', filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write(f"This is a dummy PDF content for {filename}.")
        print(f"Created dummy file: {filepath}")

# Create dummy data.csv if it doesn't exist
if not os.path.exists('data.csv'):
    dummy_data = {
        'Entity': MASTER_ENTITIES,
        'ReportName': [
            'Metabolic Panel', 'Genetic Screening', 'Blood Test', 'Drug Screen',
            'Pathology Report', 'Immunology Panel', 'Environmental Toxins'
        ],
        'ReportFile': [
            'report1.pdf', 'report2.pdf', 'report3.pdf', 'report4.pdf',
            'report5.pdf', 'report6.pdf', 'report7.pdf'
        ],
        'Username': [
            'AshlieT', 'MinaK', 'BobS', 'SatishD', 'AshlieT', 'MinaK', 'BobS'
        ],
        'Date': [
            '2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15',
            '2024-01-20', '2024-01-25', '2024-01-30'
        ],
        'Description': [
            'Comprehensive metabolic profile.', 'Genetic predispositions analysis.',
            'Complete blood count.', 'Drug screening for compliance.',
            'Tissue sample analysis.', 'Immune system markers.',
            'Analysis of environmental exposure.'
        ],
        'AccessLevel': [
            'restricted', 'unrestricted', 'restricted', 'unrestricted',
            'restricted', 'unrestricted', 'restricted'
        ],
        'AssignedPhysician': [
            'Dr. Alex Smith', 'Dr. Jane Doe', 'Dr. Alex Smith', 'Dr. Jane Doe',
            'Dr. Alex Smith', 'Dr. Jane Doe', 'Dr. Alex Smith'
        ],
        'ReviewedBy': [
            'AndrewS', 'MelindaC', 'AndrewS', 'MelindaC',
            'AndrewS', 'MelindaC', 'AndrewS'
        ],
        'UserTypeRequired': [
            'physician_provider', 'physician_provider', 'business_development_manager',
            'business_development_manager', 'admin', 'admin', 'admin'
        ],
        'TestCategory': ['Blood', 'Genetic', 'Blood', 'Toxicology', 'Pathology', 'Immunology', 'Environmental'],
        'ClinicalSignificance': [
            'Normal ranges for metabolic markers.', 'Identified gene variations.',
            'Elevated white blood cell count.', 'Detected controlled substances.',
            'Benign tissue findings.', 'Healthy immune response.',
            'Presence of trace contaminants.'
        ],
        'Notes': [
            'Patient fasted for 12 hours.', 'Family history of condition.',
            'Follow-up recommended.', 'Consult with prescribing physician.',
            'Further testing not required.', 'Annual check-up.',
            'Advised on mitigation strategies.'
        ],
        'AdditionalComments': [
            'No significant findings.', 'Genetic counseling advised.',
            'Repeat test in 2 weeks.', 'Treatment plan adjusted.',
            'Report shared with specialist.', 'Vaccination records current.',
            'Home environment assessment suggested.'
        ],
        'RelatedReports': [
            'report8.pdf,report9.pdf', 'report10.pdf', '', '', '', '', ''
        ],
        'FileName': [
            'report1.pdf', 'report2.pdf', 'report3.pdf', 'report4.pdf',
            'report5.pdf', 'report6.pdf', 'report7.pdf'
        ],
        'OriginalRequestID': ['REQ001', 'REQ002', 'REQ003', 'REQ004', 'REQ005', 'REQ006', 'REQ007'],
        'SampleType': ['Blood', 'Saliva', 'Blood', 'Urine', 'Tissue', 'Blood', 'Water'],
        'CollectionDate': [
            '2023-12-30', '2024-01-03', '2024-01-08', '2024-01-13',
            '2024-01-18', '2024-01-23', '2024-01-28'
        ],
        'ReceivedDate': [
            '2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15',
            '2024-01-20', '2024-01-25', '2024-01-30'
        ],
        'ReportDate': [
            '2024-01-01', '2024-01-05', '2024-01-10', '2024-01-15',
            '2024-01-20', '2024-01-25', '2024-01-30'
        ],
        'ApprovingScientist': [
            'Dr. Emily White', 'Dr. David Green', 'Dr. Emily White', 'Dr. David Green',
            'Dr. Emily White', 'Dr. David Green', 'Dr. Emily White'
        ],
        'QCStatus': ['Passed', 'Passed', 'Passed', 'Passed', 'Passed', 'Passed', 'Passed'],
        'BillingCode': ['BC001', 'BC002', 'BC003', 'BC004', 'BC005', 'BC006', 'BC007'],
        'CommentsForPhysician': [
            'Refer to patient history.', 'Discuss findings with patient.',
            'Monitor closely.', 'Review medication list.',
            'Pathology slides available.', 'Immunization status confirmed.',
            'Environmental remediation advised.'
        ],
        'InternalNotes': [
            'Processed smoothly.', 'Complex analysis performed.',
            'Standard procedure.', 'Urgent processing requested.',
            'QC flags clear.', 'Routine screening.',
            'Special handling applied.'
        ],
        'ClientReference': ['CR001', 'CR002', 'CR003', 'CR004', 'CR005', 'CR006', 'CR007'],
        'DiscrepancyFlag': ['No', 'No', 'No', 'No', 'No', 'No', 'No'],
        'ActionRequired': ['None', 'Follow-up', 'None', 'Alert physician', 'None', 'None', 'Environmental consult'],
        'Department': ['Clinical', 'Genetics', 'Clinical', 'Toxicology', 'Pathology', 'Immunology', 'Environmental'],
        'MethodUsed': [
            'Spectroscopy', 'Sequencing', 'Flow Cytometry', 'Chromatography',
            'Microscopy', 'ELISA', 'Mass Spectrometry'
        ],
        'Instrumentation': ['Instrument A', 'Instrument B', 'Instrument C', 'Instrument D', 'Instrument E', 'Instrument F', 'Instrument G'],
        'RegulatoryCompliance': ['Compliant', 'Compliant', 'Compliant', 'Compliant', 'Compliant', 'Compliant', 'Compliant'],
        'DistributionList': [
            'AndrewS', 'MelindaC', 'AndrewS,MelindaC', 'AndrewS,MelindaC',
            'AndrewS,MelindaC', 'AndrewS,MelindaC', 'AndrewS,MelindaC'
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
        'ClinicalNotes': [
            'Patient showed good fasting results.', 'Mild anemia detected.',
            'Thyroid levels normal.', 'UTI symptoms. Follow-up needed.'
        ]
    }
    patient_dummy_df = pd.DataFrame(patient_dummy_data)
    patient_dummy_df.to_csv('patient_data.csv', index=False)
    print("Created dummy patient_data.csv for demonstration.")

try:
    df = pd.read_csv('data.csv')
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure it's in the same directory.")
    df = pd.DataFrame() # Create empty DataFrame to prevent errors

try:
    patient_df = pd.read_csv('patient_data.csv')
    print("patient_data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: patient_data.csv not found. Dummy patient data will be created.")
    # This block should ideally not be reached if dummy data is created above
    patient_df = pd.DataFrame(columns=[
        'PatientID', 'PatientLastName', 'PatientDOB', 'DateOfService',
        'ReportName', 'ReportFile', 'ClinicalNotes'
    ])

# --- Routes ---

@app.route('/')
def index():
    # If a role is already selected, redirect to the appropriate dashboard/login
    if 'selected_role' in session:
        if session['selected_role'] == 'patient':
            return redirect(url_for('login')) # Patients always go to login
        elif session['selected_role'] in ['admin', 'business_development_manager', 'physician_provider']:
            if 'username' in session or 'email' in session: # Check if actually logged in
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('login')) # If role selected but not logged in, go to login
    return render_template('role_selection.html')


# NEW ROUTE ADDED HERE TO FIX THE ERROR
@app.route('/privacy')
def privacy():
    """Renders the privacy policy page."""
    return render_template('privacy.html') # Ensure you have a privacy.html in your templates folder


@app.route('/select_role', methods=['POST'])
def select_role():
    selected_role = request.form.get('role')
    allowed_roles = ['patient', 'physician_provider', 'admin', 'business_development_manager']

    if selected_role in allowed_roles:
        session['selected_role'] = selected_role
        if selected_role == 'patient':
            flash(f"Role '{selected_role.replace('_', ' ').title()}' selected. Please log in.", 'success')
            return redirect(url_for('login'))
        else: # physician_provider, admin, business_development_manager
            flash(f"Role '{selected_role.replace('_', '').title()}' selected. Please log in.", 'success')
            return redirect(url_for('login'))
    else:
        flash("Invalid role selected.", 'error')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'selected_role' not in session:
        flash("Please select a role first.", 'error')
        return redirect(url_for('select_role'))

    selected_role = session['selected_role']
    error = None

    if request.method == 'POST':
        if selected_role == 'patient':
            last_name = request.form.get('last_name')
            dob = request.form.get('dob')
            ssn4 = request.form.get('ssn4')

            patient_found = False
            if last_name in patients and dob in patients[last_name] and ssn4 in patients[last_name][dob]:
                session['patient_id'] = patients[last_name][dob][ssn4]['PatientID']
                session['patient_last_name'] = last_name
                flash('Logged in successfully as patient!', 'success')
                return redirect(url_for('patient_dashboard'))
            else:
                error = 'Invalid patient credentials.'

        elif selected_role == 'physician_provider':
            email = request.form.get('email')
            password = request.form.get('password')
            if email in users and check_password_hash(users[email]['password'], password) and users[email]['role'] == 'physician_provider':
                session['email'] = email
                session['username'] = users[email]['name'] # Store the name for display
                flash('Logged in successfully as physician/provider!', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid email or password.'

        else: # Admin, Business Development Manager
            username = request.form.get('username')
            password = request.form.get('password')
            if username in users and check_password_hash(users[username]['password'], password) and users[username]['role'] == selected_role:
                session['username'] = username
                flash(f'Logged in successfully as {selected_role.replace("_", " ").title()}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid username or password.'
    
    return render_template('login.html', selected_role=selected_role, error=error)

@app.route('/dashboard')
def dashboard():
    if 'selected_role' not in session:
        flash("Please select a role first.", 'error')
        return redirect(url_for('select_role'))
    
    selected_role = session['selected_role']

    if selected_role == 'patient':
        return redirect(url_for('patient_dashboard'))

    if 'username' not in session and 'email' not in session:
        flash("Please log in to access the dashboard.", 'error')
        return redirect(url_for('login'))

    username = session.get('username') or session.get('email')
    
    # Filter data based on role and access
    if selected_role == 'admin':
        filtered_df = df.copy() # Admins see everything
    elif selected_role == 'business_development_manager':
        # BDM can see reports assigned to specific usernames (including themselves)
        # Assuming 'AndrewS' and 'MelindaC' are the BDM usernames.
        # This needs to be adjusted based on actual BDM user management
        if username in UNFILTERED_ACCESS_USERS: # Use the existing UNFILTERED_ACCESS_USERS for BDM
            filtered_df = df.copy()
        elif username == 'AndrewS': # Example: BDM specific access
            filtered_df = df[df['DistributionList'].apply(lambda x: username in str(x).split(','))]
        elif username == 'MelindaC':
            filtered_df = df[df['DistributionList'].apply(lambda x: username in str(x).split(','))]
        else:
            filtered_df = df[df['UserTypeRequired'] == 'business_development_manager'] # Default BDM access
    elif selected_role == 'physician_provider':
        # Physicians see reports assigned to them or their entities
        physician_name = users[username]['name'] if username in users else None
        if physician_name:
            filtered_df = df[df['AssignedPhysician'] == physician_name].copy()
        else:
            filtered_df = pd.DataFrame() # No data if physician name not found
    else:
        filtered_df = pd.DataFrame() # Should not happen if roles are correctly managed

    # Get unique entities from the filtered data
    entities = sorted(filtered_df['Entity'].unique().tolist()) if not filtered_df.empty else []

    # Prepare user-specific messages based on the role
    user_message = f"Welcome, {username}! You are logged in as {selected_role.replace('_', ' ').title()}."

    return render_template('dashboard.html',
                           username=username,
                           selected_role=selected_role,
                           user_message=user_message,
                           entities=entities,
                           reports=filtered_df.to_dict('records')) # Pass filtered data

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'selected_role' not in session or session['selected_role'] != 'patient':
        flash("Access denied. Please log in as a patient.", 'error')
        return redirect(url_for('login'))

    if 'patient_id' not in session:
        flash("Patient ID not found in session. Please log in again.", 'error')
        return redirect(url_for('login'))

    patient_id = session['patient_id']
    patient_last_name = session['patient_last_name']
    
    # Filter patient-specific reports
    patient_reports = patient_df[patient_df['PatientID'] == patient_id].to_dict('records')

    # Prepare for display
    return render_template('patient_dashboard.html',
                           patient_id=patient_id,
                           patient_last_name=patient_last_name,
                           reports=patient_reports)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('email', None)
    session.pop('selected_role', None)
    session.pop('patient_id', None)
    session.pop('patient_last_name', None)
    flash("You have been logged out.", 'success')
    return redirect(url_for('index'))

@app.route('/register_physician', methods=['GET', 'POST'])
def register_physician():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        if not email or not password or not name:
            flash('All fields are required!', 'error')
        elif email in users:
            flash('Email already registered!', 'error')
        else:
            hashed_password = generate_password_hash(password)
            users[email] = {'password': hashed_password, 'role': 'physician_provider', 'name': name}
            flash('Physician/Provider registered successfully! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register_physician.html')

@app.route('/view_report/<path:filename>')
def view_report(filename):
    # This is a simplified example. In a real application, you would
    # implement proper access control to ensure the user is authorized
    # to view the specific report.
    # For now, we'll assume the files are in the 'static' directory.
    file_path = os.path.join('static', filename)
    
    if os.path.exists(file_path):
        # In a real app, you'd use send_from_directory or similar for file serving.
        # For this mock, we can just return a placeholder or actual file content.
        # This part requires more robust file serving or integration with a PDF viewer.
        # As it's outside the scope of current request, we'll return a simple message.
        return f"<html><body><h1>Viewing Report: {filename}</h1><p>Content for {filename} would be displayed here.</p><a href='#' onclick='history.back()'>Go Back</a></body></html>"
    else:
        return "Report not found.", 404


if __name__ == '__main__':
    app.run(debug=True)
