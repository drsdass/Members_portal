import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

# --- Master List of All Entities (Centralized here) ---
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

# --- User Management (In-memory store, now centralized in models.py) ---
# IMPORTANT: In a production application, this data should come from a secure database.
users = {
    # Full Access Admins
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'AshlieT': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},
    'MinaK': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES, 'role': 'admin'},

    # Business Development Managers with specific entity access
    'BobS': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics LLC'], 'role': 'business_dev_manager'},
    'NickT': {'password_hash': generate_password_hash('password1'), 'entities': ['AIM Laboratories LLC', 'Enviro Labs LLC'], 'role': 'business_dev_manager'},

    # Physician/Providers with single entity access
    'DrSmith': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'physician_provider', 'full_name': 'Dr. Alice Smith'},
    'DrJones': {'password_hash': generate_password_hash('password1'), 'entities': ['AIM Laboratories LLC'], 'role': 'physician_provider', 'full_name': 'Dr. Bob Jones'},

    # Patients (with single entity access, typically for their own results)
    'patient1': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab'], 'role': 'patient', 'patient_id': 'PAT123'},
    'patient2': {'password_hash': generate_password_hash('password1'), 'entities': ['AIM Laboratories LLC'], 'role': 'patient', 'patient_id': 'PAT456'},
}

def get_user(username):
    """Retrieves user details from the in-memory store."""
    return users.get(username)

def register_user(username, password, role, entity=None, full_name=None, patient_id=None):
    """
    Registers a new user in the in-memory store.
    Note: For a real application, implement proper database storage and validation.
    """
    if username in users:
        return False, "Username already exists."

    password_hash = generate_password_hash(password)
    new_user_data = {
        'password_hash': password_hash,
        'role': role,
        'entities': [entity] if entity else [], # Assign single entity if provided
        'full_name': full_name,
        'patient_id': patient_id
    }
    
    if role == 'admin' or role == 'business_dev_manager':
        # For admin/biz dev roles, if no specific entity, give full master access or handle as default
        if not entity:
             new_user_data['entities'] = MASTER_ENTITIES # Give full access if not specified for broad roles
        
    users[username] = new_user_data
    return True, "User registered successfully."


def get_available_entities_for_user(username, role):
    """
    Determines which entities a user has access to based on their role.
    This function specifically handles entity access for admins and other roles.
    """
    user_data = get_user(username)
    if not user_data:
        return []

    user_assigned_entities = user_data.get('entities', [])

    if role in ['admin', 'business_dev_manager']:
        # Admins/Business Dev Managers can see 'All Entities' if they have broad access
        if set(user_assigned_entities) == set(MASTER_ENTITIES):
            # Include 'All Entities' as an option for full access users
            return sorted(['All Entities'] + MASTER_ENTITIES)
        else:
            # If they only have access to specific entities, just return those
            return sorted(user_assigned_entities)
    elif role == 'physician_provider':
        # Physicians usually have access to a single or a few specific entities
        return sorted(user_assigned_entities)
    elif role == 'patient':
        # Patients typically don't select entities in this manner; their access
        # is usually tied to their specific patient ID.
        return [] # Or handle as per your patient flow
    else:
        return []


def get_report_types_for_role(role):
    """
    Defines the available report types for each role.
    """
    if role == 'admin':
        return [
            {'value': 'revenue', 'name': 'Revenue Report'},
            {'value': 'cogs', 'name': 'Cost of Goods Sold (COGS) Report'},
            {'value': 'net_profit', 'name': 'Net Profit Report'},
            {'value': 'commission', 'name': 'Commission Report'},
            {'value': 'patient_id_report', 'name': 'Patient ID Report'},
            {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
            {'value': 'marketing_material', 'name': 'Marketing Materials'},
            {'value': 'training_material', 'name': 'Training Materials'},
            # Add other admin-specific reports
        ]
    elif role == 'business_dev_manager':
        return [
            {'value': 'revenue', 'name': 'Revenue Report'},
            {'value': 'cogs', 'name': 'Cost of Goods Sold (COGS) Report'},
            {'value': 'net_profit', 'name': 'Net Profit Report'},
            {'value': 'commission', 'name': 'Commission Report'},
            {'value': 'patient_id_report', 'name': 'Patient ID Report'},
            {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
            {'value': 'marketing_material', 'name': 'Marketing Materials'},
            # Add other business dev manager-specific reports
        ]
    elif role == 'physician_provider':
        return [
            {'value': 'patient_results', 'name': 'Patient Results'},
            {'value': 'marketing_material', 'name': 'Marketing Materials'},
            {'value': 'training_material', 'name': 'Training Materials'},
            # Add other physician-specific reports
        ]
    elif role == 'patient':
        return [
            {'value': 'patient_results', 'name': 'My Results'}
        ]
    return []


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
    'First Bio Lab': [
        {'name': 'First Bio Lab Brochure', 'webViewLink': '/marketing_material/First_Bio_Lab_Brochure.pdf'},
        {'name': 'First Bio Lab Services', 'webViewLink': '/marketing_material/First_Bio_Lab_Services.pptx'},
    ],
    'First Bio Genetics LLC': [
        {'name': 'Genetics Overview', 'webViewLink': '/marketing_material/Genetics_Overview.pdf'},
    ],
    'AIM Laboratories LLC': [
        {'name': 'AIM Labs Prospectus', 'webViewLink': '/marketing_material/AIM_Labs_Prospectus.pdf'},
    ],
    'Enviro Labs LLC': [
        {'name': 'Enviro Labs Whitepaper', 'webViewLink': '/marketing_material/Enviro_Labs_Whitepaper.pdf'}
    ]
    # Add more marketing materials per entity
}

# --- Training Report Definitions ---
TRAINING_REPORT_DEFINITIONS = {
    'general': [ # General training materials accessible to all relevant roles
        {'name': 'Portal Navigation Guide', 'webViewLink': '/training_material/Portal_Navigation_Guide.pdf'},
        {'name': 'Data Understanding', 'webViewLink': '/training_material/Data_Understanding.pptx'},
    ],
    'First Bio Lab': [
        {'name': 'First Bio Lab Specific Training', 'webViewLink': '/training_material/First_Bio_Lab_Training.mp4'},
    ]
    # Add more training materials per entity or category
}


# --- Dummy Data for Patient Results (replace with actual database queries) ---
# This dictionary simulates fetching patient reports based on patient_id and entity
# In a real application, this would involve a database query
def get_patient_reports_for_patient_id(patient_id, entity):
    dummy_patient_reports = {
        'PAT123': {
            'First Bio Lab': {
                '2025-03-15': [
                    {'name': 'Patient Report AB123 - March 2025', 'webViewLink': '/patient_results/Patient_Report_AB123_2025_03.pdf'},
                    {'name': 'Lab Results AB123 - March 2025', 'webViewLink': '/patient_results/Lab_Results_AB123_2025_03.pdf'}
                ],
                '2024-11-20': [
                    {'name': 'Patient Report AB123 - Nov 2024', 'webViewLink': '/patient_results/Patient_Report_AB123_2024_11.pdf'}
                ]
            }
        },
        'PAT456': {
            'AIM Laboratories LLC': {
                '2025-05-10': [
                    {'name': 'Patient Report IJ345 - May 2025', 'webViewLink': '/patient_results/Patient_Report_IJ345_2025_05.pdf'}
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
                filtered_df['Username'].apply(lambda x: current_username in str(x).split(', '))
            ]

    return filtered_df
