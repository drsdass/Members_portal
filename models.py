
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

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

# --- Users with Unfiltered Access (for monthly bonus reports) ---
UNFILTERED_ACCESS_USERS = ['SatishD', 'AshlieT', 'MinaK', 'BobS', 'NickT']

# --- Financial Report Definitions ---
FINANCIAL_REPORT_DEFINITIONS = {
    'revenue': {'name': 'Revenue Report', 'columns': ['Date', 'Location', 'Reimbursement', 'Entity', 'Associated Rep Name', 'Username']},
    'cogs': {'name': 'Cost of Goods Sold (COGS) Report', 'columns': ['Date', 'Location', 'COGS', 'Entity', 'Associated Rep Name', 'Username']},
    'net_profit': {'name': 'Net Profit Report', 'columns': ['Date', 'Location', 'Net', 'Entity', 'Associated Rep Name', 'Username']},
    'commission': {'name': 'Commission Report', 'columns': ['Date', 'Location', 'Commission', 'Entity', 'Associated Rep Name', 'Username']},
    'patient_id_report': {'name': 'Patient ID Report', 'columns': ['Date', 'Location', 'PatientID', 'Entity', 'Associated Rep Name', 'Username']},
}

# --- Marketing Report Definitions ---
MARKETING_REPORT_DEFINITIONS = {
    'marketing_material': {'name': 'Marketing Materials', 'columns': []} # Columns not applicable for file display
}

# --- Combined Report Types by Role (For sidebar navigation) ---
REPORT_TYPES_BY_ROLE = {
    'admin': [
        {'value': 'revenue', 'name': 'Revenue Report'},
        {'value': 'cogs', 'name': 'COGS Report'},
        {'value': 'net_profit', 'name': 'Net Profit Report'},
        {'value': 'commission', 'name': 'Commission Report'},
        {'value': 'patient_id_report', 'name': 'Patient ID Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
        {'value': 'marketing_material', 'name': 'Marketing Materials'},
    ],
    'business_dev_manager': [
        {'value': 'revenue', 'name': 'Revenue Report'},
        {'value': 'cogs', 'name': 'COGS Report'},
        {'value': 'net_profit', 'name': 'Net Profit Report'},
        {'value': 'commission', 'name': 'Commission Report'},
        {'value': 'patient_id_report', 'name': 'Patient ID Report'},
        {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
        {'value': 'marketing_material', 'name': 'Marketing Materials'},
    ],
    'physician_provider': [
        {'value': 'patient_results', 'name': 'Patient Results'} # Specific report for providers
    ],
    'patient': [
        {'value': 'patient_results', 'name': 'My Results'} # Specific report for patients
    ],
}

# --- Date Ranges ---
CURRENT_YEAR = datetime.date.today().year
YEARS = list(range(CURRENT_YEAR, CURRENT_YEAR - 5, -1)) # Last 5 years including current
MONTHS = [
    {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
    {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
    {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
    {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
    {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
    {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'}
]

# --- In-memory User Management (Replace with Database in Production!) ---
# This dictionary represents your user "database" for demonstration purposes.
# In a real application, you'd use a proper database with hashed passwords.
users = {
    # Full Access Admins
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Business Development Managers with specific entity access
    'BobS': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Genetics LLC', 'AIM Laboratories LLC'], 'role': 'business_dev_manager'},
    'NickT': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'Enviro Labs LLC'], 'role': 'business_dev_manager'},
    'MelindaC': {'password_hash': generate_password_hash('password1'), 'entities': ['AMICO Dx LLC', 'Stat Labs'], 'role': 'business_dev_manager'},

    # Physician/Providers with specific entity access (example: Dr. Sarah Smith from First Bio Lab)
    'SarahS': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'full_name': 'Dr. Sarah Smith'},
    'JohnD': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Genetics LLC'], 'role': 'physician_provider', 'full_name': 'Dr. John Doe'},

    # Patients with specific entity and patient ID access
    'Patient1': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'patient', 'patient_id': 'AB123'},
    'Patient2': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Genetics LLC'], 'role': 'patient', 'patient_id': 'CD456'},
    'Patient3': {'password_hash': generate_password_hash('password1'), 'entities': ['AIM Laboratories LLC'], 'role': 'patient', 'patient_id': 'EF789'},
    'Patient4': {'password_hash': generate_password_hash('password1'), 'entities': ['Enviro Labs LLC'], 'role': 'patient', 'patient_id': 'GH012'},
    'Patient5': {'password_hash': generate_password_hash('password1'), 'entities': ['Stat Labs'], 'role': 'patient', 'patient_id': 'IJ345'}
}

# --- Data Loading ---
def load_data():
    """Loads the financial data from data.csv into a pandas DataFrame."""
    try:
        df = pd.read_csv('data.csv', parse_dates=['Date'])
        # Convert 'Username' to string to avoid potential float issues from NaN
        df['Username'] = df['Username'].astype(str)
        # Ensure 'PatientID' is string type
        df['PatientID'] = df['PatientID'].astype(str).replace('nan', 'NA')
        return df
    except FileNotFoundError:
        print("data.csv not found. Creating dummy data.")
        return create_dummy_data()
    except Exception as e:
        print(f"Error loading data.csv: {e}")
        return create_dummy_data() # Fallback to dummy data on other errors

def create_dummy_data():
    """Creates a dummy DataFrame for development if data.csv is not found."""
    print("Creating dummy data for demonstration purposes.")
    data = {
        'Date': [
            datetime.date(2025, 3, 1), datetime.date(2025, 3, 1), datetime.date(2025, 3, 1),
            datetime.date(2025, 3, 1), datetime.date(2025, 3, 1), datetime.date(2025, 3, 1),
            datetime.date(2025, 4, 1), datetime.date(2025, 4, 1), datetime.date(2025, 4, 1),
            datetime.date(2025, 4, 1), datetime.date(2025, 4, 1), datetime.date(2025, 4, 1),
            datetime.date(2025, 5, 1), datetime.date(2025, 5, 1), datetime.date(2025, 5, 1),
            datetime.date(2025, 5, 1), datetime.date(2025, 5, 1), datetime.date(2025, 1, 1),
            datetime.date(2025, 1, 1), datetime.date(2025, 1, 1), datetime.date(2025, 1, 1),
            datetime.date(2025, 1, 1), datetime.date(2025, 5, 1) # Added for Patient5
        ],
        'Location': [
            'BIRCH TREE RECOVERY', 'CENTRAL KENTUCKY SPINE SURGERY - TOX',
            'FAIRVIEW HEIGHTS MEDICAL GROUP - CLINICA', 'HOPESS RESIDENTIAL TREATMENT',
            'JACKSON MEDICAL CENTER', 'TRIBE RECOVERY HOMES',
            'SAGE HEALING', 'SONDERCARE BEHAVIORAL HEALTH',
            'WAVELENGTHS RECOVERY', 'PURPOSE DETOX FACILITY',
            'OCEAN RECOVERY', 'NEW HOPE',
            'GOLDEN ERA', 'BRIGHT FUTURE', 'HAPPY PATH CLINIC',
            'EAST COAST MEDICAL', 'WESTERN HEALTH',
            'SAGE HEALING', 'SONDERCARE BEHAVIORAL HEALTH',
            'WAVELENGTHS RECOVERY', 'HAPPY PATH CLINIC', 'PURPOSE DETOX FACILITY', 'SAGE HEALING'
        ],
        'Reimbursement': [
            186.49, 1.98, 150.49, 805.13, 2466.87, 76542.07,
            10278.22, 6605.83, 1535.59, 1366.42,
            62.09, 250.00,
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
            36.49, -48.02, -1.15, 555.13, 516.87, 45817.07,
            6853.22, 4280.83, 845.59, 1051.42,
            37.09, 100.00,
            100.00, 200.00,
            300.00, 80.00, 700.00,
            150.00, 50.00,
            13.85,
            700.00,
            80.00, 160.00, 120.00, 200.00,
            550.00
        ],
        'Commission': [
            10.95, -14.41, -0.35, 166.54, 155.06, 13745.12,
            2055.97, 1284.25, 253.68, 315.43,
            11.12, 30.00,
            30.00, 60.00,
            90.00, 24.00, 210.00,
            45.00, 15.00,
            4.16,
            210.00,
            24.00, 48.00, 36.00, 60.00,
            165.00
        ],
        'Entity': [
            'AIM Laboratories LLC', 'AIM Laboratories LLC', 'AIM Laboratories LLC',
            'AIM Laboratories LLC', 'AIM Laboratories LLC', 'AIM Laboratories LLC',
            'First Bio Genetics LLC', 'First Bio Genetics LLC', 'First Bio Genetics LLC',
            'First Bio Lab',
            'First Bio Genetics LLC', 'First Bio Lab',
            'Enviro Labs LLC', 'Enviro Labs LLC',
            'Stat Labs', 'Stat Labs', 'Stat Labs',
            'AIM Laboratories LLC', 'AMICO Dx LLC',
            'First Bio Lab of Illinois',
            'First Bio Lab',
            'First Bio Genetics LLC', 'First Bio Lab' # Added for Patient5 and additional test
        ],
        'Associated Rep Name': [
            'Andrew S', 'House', 'House', 'SAV LLC', 'HCM Crew LLC', 'First Bio Diagnostics',
            'Celano Venture', 'GD Laboratory', 'Celano Venture', 'Celano Venture',
            'HCM Crew LLC', 'Andrew S',
            'Jane D', 'Mike R',
            'Sarah L', 'Tom M', 'Jessica K',
            'House', 'Jane D',
            'Sarah L',
            'Mike R',
            'HCM Crew LLC', 'Jane D' # Added for Patient5 and additional test
        ],
        'Username': [
            'AndrewS', 'SatishD', 'SatishD', 'VinceO', 'JayM', 'SatishD',
            'SatishD,AshlieT,MinaK,MelindaC,ACG', 'SatishD,ACG', 'SatishD,AshlieT,MinaK,MelindaC,ACG', 'SatishD,AshlieT,MinaK,MelindaC,ACG',
            'JayM', 'AndrewS',
            'JaneD', 'MikeR',
            'SarahL', 'TomM', 'JessicaK',
            'SatishD', 'JaneD',
            'SarahL',
            'MikeR',
            'JayM', 'JaneD' # Added for Patient5 and additional test
        ],
        'PatientID': [
            'NA', 'NA', 'NA', 'NA', 'NA', 'NA',
            'NA', 'NA', 'NA', 'NA',
            'NA', 'AB123',
            'NA', 'NA',
            'NA', 'NA', 'NA',
            'NA', 'CD456', # Example for Patient2
            'EF789', # Example for Patient3
            'GH012', # Example for Patient4
            'NA', 'IJ345' # Example for Patient5
        ]
    }
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Username'] = df['Username'].astype(str)
    df['PatientID'] = df['PatientID'].astype(str).replace('nan', 'NA')
    return df

# Load data when models.py is imported
data_df = load_data()

# Centralized function to get user
def get_user(username):
    """Retrieves user details from the in-memory 'users' dictionary."""
    return users.get(username)

# Centralized function to register a user
def register_user(username, password, role, entity, full_name=None, patient_id=None):
    if username in users:
        return False, "Username already exists."

    hashed_password = generate_password_hash(password)
    users[username] = {
        'password_hash': hashed_password,
        'role': role,
        'entities': [entity] if entity else [], # Ensure it's a list
        'full_name': full_name,
        'patient_id': patient_id
    }
    return True, "User registered successfully."

# Centralized function to get available entities for a user based on role
def get_available_entities_for_user(username, role):
    user_info = get_user(username)
    if not user_info:
        return []

    if role == 'admin' or username in UNFILTERED_ACCESS_USERS: # Admins and certain users have full access
        return MASTER_ENTITIES
    else:
        return user_info.get('entities', []) # Return specific entities for other roles

# Function to get report types allowed for a given role
def get_report_types_for_role(role):
    return REPORT_TYPES_BY_ROLE.get(role, [])

# Function to get report definition by type
def get_report_definition(report_type):
    return FINANCIAL_REPORT_DEFINITIONS.get(report_type) or MARKETING_REPORT_DEFINITIONS.get(report_type)

# Function to get specific files for marketing materials (dummy implementation)
def get_marketing_materials(entity=None):
    # This is a placeholder. In a real app, this would query a file storage (e.g., GDrive, S3)
    dummy_files = {
        'First Bio Lab': [
            {'name': 'First Bio Lab Brochure.pdf', 'webViewLink': '/static/dummy_files/First_Bio_Lab_Brochure.pdf'},
            {'name': 'First Bio Lab Services.pptx', 'webViewLink': '/static/dummy_files/First_Bio_Lab_Services.pptx'}
        ],
        'First Bio Genetics LLC': [
            {'name': 'Genetics Overview.pdf', 'webViewLink': '/static/dummy_files/Genetics_Overview.pdf'},
            {'name': 'Genetic Testing Guide.docx', 'webViewLink': '/static/dummy_files/Genetic_Testing_Guide.docx'}
        ],
        'AIM Laboratories LLC': [
            {'name': 'AIM Labs Prospectus.pdf', 'webViewLink': '/static/dummy_files/AIM_Labs_Prospectus.pdf'}
        ]
        # Add more dummy data as needed
    }

    if entity and entity in dummy_files:
        return {entity: dummy_files[entity]}
    elif not entity: # Return all if no specific entity is selected
        return dummy_files
    return {}

# Function to simulate fetching patient results files (dummy implementation)
def get_patient_result_files(patient_id, entity):
    # In a real application, this would query a database or file system
    # to find actual reports linked to the patient_id and entity.
    # For now, it returns dummy files for demonstration.
    dummy_patient_reports = {
        'AB123': {
            'First Bio Lab': {
                '2025-03-15': [
                    {'name': 'Patient Report - March 2025.pdf', 'webViewLink': '/static/dummy_files/Patient_Report_AB123_2025_03.pdf'},
                    {'name': 'Lab Results - March 2025.pdf', 'webViewLink': '/static/dummy_files/Lab_Results_AB123_2025_03.pdf'}
                ],
                '2024-11-20': [
                    {'name': 'Patient Report - Nov 2024.pdf', 'webViewLink': '/static/dummy_files/Patient_Report_AB123_2024_11.pdf'}
                ]
            }
        },
        'CD456': {
            'AMICO Dx LLC': {
                '2025-01-20': [
                    {'name': 'Patient Report - Jan 2025.pdf', 'webViewLink': '/static/dummy_files/Patient_Report_CD456_2025_01.pdf'}
                ]
            }
        },
        'IJ345': {
            'Stat Labs': {
                '2025-05-05': [
                    {'name': 'Patient Report - May 2025.pdf', 'webViewLink': '/static/dummy_files/Patient_Report_IJ345_2025_05.pdf'}
                ]
            }
        }
        # Add more dummy data as needed
    }

    reports_for_patient_entity = dummy_patient_reports.get(patient_id, {}).get(entity, {})
    return reports_for_patient_entity

# Helper to filter financial data based on entity, month, year, and username
def filter_financial_data(df, selected_entity, selected_month, selected_year, current_username=None, entity_filter_enabled=True):
    filtered_df = df.copy()

    if selected_entity and selected_entity != 'All Entities' and entity_filter_enabled:
        filtered_df = filtered_df[filtered_df['Entity'] == selected_entity]

    if selected_month and selected_year:
        filtered_df = filtered_df[
            (filtered_df['Date'].dt.month == int(selected_month)) &
            (filtered_df['Date'].dt.year == int(selected_year))
        ]

    # For 'monthly_bonus' report, filter by the associated username
    if current_username and current_username not in UNFILTERED_ACCESS_USERS:
        # Check if 'Username' column is present before filtering
        if 'Username' in filtered_df.columns:
            # The 'Username' column might contain multiple usernames separated by commas.
            # We need to check if the current_username is present in any of the comma-separated strings.
            filtered_df = filtered_df[
                filtered_df['Username'].apply(lambda x: current_username in str(x).split(','))
            ]

    return filtered_df
