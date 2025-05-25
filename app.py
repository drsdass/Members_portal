import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# It's crucial to set a strong secret key for session management.
# In a production environment, load this from an environment variable.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# --- Master List of All Entities (RESTRICTED to the 7 core company/lab entities) ---
# This list will populate the entity dropdown for all users.
MASTER_ENTITIES = sorted([
    'First Bio Lab',
    'First Bio Genetics',
    'First Bio Lab of Illinois',
    'AIM Laboratories',
    'AMICO Dx',
    'Enviro Labs',
    'Stat Labs'
])

# --- User Management (In-memory, with individual names as usernames) ---
# Passwords are simple for demonstration. In production, these would be hashed and stored securely.
# Entity access is mapped based on the previous "Rep" access to the 7 core entities.
users = {
    'SatishD': {'password_hash': generate_password_hash('password1'), 'entities': MASTER_ENTITIES}, # Associated with Celano Venture, HCM Crew LLC, Celano/GD, GD Laboratory/360 Health, GD Laboratory
    'ACG': {'password_hash': generate_password_hash('password2'), 'entities': MASTER_ENTITIES}, # Associated with Celano Venture, HCM Crew LLC, Celano/GD, GD Laboratory/360 Health, GD Laboratory
    'AshlieT': {'password_hash': generate_password_hash('password3'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois', 'AIM Laboratories', 'AMICO Dx', 'Enviro Labs', 'Stat Labs']}, # Associated with Celano Venture, HCM Crew LLC
    'MelindaC': {'password_hash': generate_password_hash('password4'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois', 'AIM Laboratories', 'AMICO Dx', 'Enviro Labs', 'Stat Labs']}, # Associated with Celano Venture
    'MinaK': {'password_hash': generate_password_hash('password5'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois', 'AIM Laboratories', 'AMICO Dx', 'Enviro Labs', 'Stat Labs']}, # Associated with Celano Venture, HCM Crew LLC
    'JayM': {'password_hash': generate_password_hash('password6'), 'entities': MASTER_ENTITIES}, # Associated with HCM Crew LLC, HCM Crew LLC/ 360 Health
    'Andrew': {'password_hash': generate_password_hash('password7'), 'entities': ['First Bio Lab', 'First Bio Genetics']}, # Associated with HCM Crew LLC, retaining specific access from previous Andrew user
    'AndrewS': {'password_hash': generate_password_hash('password8'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois']}, # Associated with HCM Crew LLC, Andrew S
    'House': {'password_hash': generate_password_hash('password9'), 'entities': []}, # Associated with HCM Crew LLC, retaining empty access from previous House user
    'VinceO': {'password_hash': generate_password_hash('password10'), 'entities': ['AMICO Dx']}, # Associated with SAV LLC
    'SonnyA': {'password_hash': generate_password_hash('password11'), 'entities': ['AIM Laboratories']}, # Associated with Sonny
    'Omar': {'password_hash': generate_password_hash('password12'), 'entities': MASTER_ENTITIES}, # Associated with GD Laboratory/360 Health, HCM Crew LLC/ 360 Health
    'NickC': {'password_hash': generate_password_hash('password13'), 'entities': ['AMICO Dx']}, # Associated with 2AZ Investments LLC
    'DarangT': {'password_hash': generate_password_hash('password14'), 'entities': MASTER_ENTITIES}, # Associated with DarangT (itself), retains access to all MASTER_ENTITIES
    'BobS': {'password_hash': generate_password_hash('password15'), 'entities': MASTER_ENTITIES}, # Associated with BobS (itself), retains access to all MASTER_ENTITIES
}

# --- Data Loading (Optimized: Load once at app startup) ---
try:
    df = pd.read_csv('data.csv')
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py.")
    df = pd.DataFrame()
except Exception as e:
    print(f"An error occurred while loading data.csv: {e}")
    df = pd.DataFrame()

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    - GET: Displays the login form.
    - POST: Processes login credentials.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user_info = users.get(username)
        if user_info and check_password_hash(user_info['password_hash'], password):
            session['username'] = username
            return redirect(url_for('select_report'))
        else:
            return render_template('login.html', error='Invalid username or password.'), 401
    return render_template('login.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    """
    Allows logged-in users to select both a report type and an entity.
    The entity dropdown shows all MASTER_ENTITIES, but authorization is checked on submission.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_authorized_entities = users[username]['entities']

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        selected_entity = request.form.get('entity_name')

        if not report_type or not selected_entity:
            return render_template(
                'select_report.html',
                master_entities=MASTER_ENTITIES,
                error="Please select both a report type and an entity."
            )

        if selected_entity not in user_authorized_entities:
            if not user_authorized_entities:
                return render_template(
                    'unauthorized.html',
                    message=f"You do not have any entities assigned to view reports. Please contact support."
                )
            return render_template(
                'select_report.html',
                master_entities=MASTER_ENTITIES,
                error=f"You are not authorized to view reports for '{selected_entity}'. Please select an entity you are authorized for."
            )

        session['report_type'] = report_type
        session['selected_entity'] = selected_entity
        return redirect(url_for('dashboard'))
    
    return render_template('select_report.html', master_entities=MASTER_ENTITIES)

@app.route('/dashboard')
def dashboard():
    """
    Displays the dashboard based on the selected report type and chosen entity.
    """
    if 'username' not in session or 'report_type' not in session or 'selected_entity' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    selected_entity = session['selected_entity']
    report_type = session.get('report_type')

    if not df.empty and 'Rep' in df.columns:
        rep_data = df[df['Rep'] == selected_entity]
    else:
        rep_data = pd.DataFrame()
        print(f"Warning: 'Rep' column not found in data.csv or data.csv is empty. Cannot filter for entity '{selected_entity}'.")

    if report_type == 'financials':
        files = [
            {'name': '2023 Full Report.pdf', 'webViewLink': url_for('static', filename='example1.pdf')},
            {'name': '2024 Full Report.pdf', 'webViewLink': url_for('static', filename='example2.pdf')},
            {'name': '2025 YTD Financials.pdf', 'webViewLink': url_for('static', filename='example1.pdf')},
            {'name': '2025 Last Month Financials.pdf', 'webViewLink': url_for('static', filename='example2.pdf')}
        ]
        return render_template(
            'dashboard.html',
            data=rep_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type,
            files=files
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=rep_data.to_dict(orient='records'),
            rep=rep,
            selected_entity=selected_entity,
            report_type=report_type
        )
    else:
        return redirect(url_for('select_report'))

@app.route('/logout')
def logout():
    """
    Logs out the user by clearing the session.
    """
    session.clear()
    return redirect(url_for('login'))

# --- Run the application ---
if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    for filename in ['example1.pdf', 'example2.pdf']:
        filepath = os.path.join('static', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file: {filename}")
            print(f"Created dummy file: {filepath}")

    # Update dummy data to only include entities from the new MASTER_ENTITIES list
    if not os.path.exists('data.csv'):
        dummy_data = {
            'Rep': [
                'First Bio Lab', 'AIM Laboratories', 'First Bio Genetics', 'Stat Labs',
                'First Bio Lab of Illinois', 'AMICO Dx', 'Enviro Labs',
                'First Bio Lab', 'AIM Laboratories', 'AMICO Dx', 'Enviro Labs', 'Stat Labs'
            ],
            'Value': [100, 200, 150, 300, 250, 120, 180, 110, 210, 130, 190, 260],
            'Date': [
                '2025-01-01', '2025-01-05', '2025-01-10', '2025-01-15', '2025-01-20',
                '2025-01-22', '2025-01-28', '2025-02-01', '2025-02-05', '2025-02-10',
                '2025-02-15', '2025-02-20'
            ]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv('data.csv', index=False)
        print("Created dummy data.csv for demonstration.")

    app.run(debug=True)
