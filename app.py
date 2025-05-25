import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
# It's crucial to set a strong secret key for session management.
# In a production environment, load this from an environment variable.
# Example: app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_and_random_string_that_is_not_this')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# --- User Management (In-memory for demonstration, use a DB in production) ---
# Store hashed passwords instead of plain text for security.
# This is still in-memory for simplicity; a real app would use a database.
users = {
    'Andrew S': {'password_hash': generate_password_hash('password1'), 'entities': ['First Bio Lab', 'First Bio Genetics', 'First Bio Lab of Illinois']},
    'AIM Laboratories': {'password_hash': generate_password_hash('password2'), 'entities': ['AIM Laboratories']},
    'AMICO Dx': {'password_hash': generate_password_hash('password3'), 'entities': ['AMICO Dx']},
    'Enviro Labs': {'password_hash': generate_password_hash('password4'), 'entities': ['Enviro Labs']},
    'Stat Labs': {'password_hash': generate_password_hash('password5'), 'entities': ['Stat Labs']},
    'Celano Venture': {'password_hash': generate_password_hash('password6'), 'entities': ['Celano Venture']},
    'HCM Crew LLC': {'password_hash': generate_password_hash('password7'), 'entities': ['HCM Crew LLC']},
    'Andrew': {'password_hash': generate_password_hash('password8'), 'entities': []},
    'House': {'password_hash': generate_password_hash('password9'), 'entities': []},
    'Celano/GD': {'password_hash': generate_password_hash('password10'), 'entities': ['Celano/GD']},
    'SAV LLC': {'password_hash': generate_password_hash('password11'), 'entities': ['SAV LLC']},
    'Andrew S2': {'password_hash': generate_password_hash('password12'), 'entities': ['Andrew S']},
    'Sonny': {'password_hash': generate_password_hash('password13'), 'entities': []},
    'GD Laboratory/360 Health': {'password_hash': generate_password_hash('password14'), 'entities': ['GD Laboratory/360 Health']},
    '2AZ Investments LLC': {'password_hash': generate_password_hash('password15'), 'entities': ['2AZ Investments LLC']},
    'GD Laboratory': {'password_hash': generate_password_hash('password16'), 'entities': ['GD Laboratory']},
    # Corrected the typo in the password for 'HCM Crew LLC/ 360 Health'
    'HCM Crew LLC/ 360 Health': {'password_hash': generate_password_hash('password17'), 'entities': ['HCM Crew LLC/ 360 Health']},
    'DarangT': {'password_hash': generate_password_hash('password18'), 'entities': ['DarangT']},
    'BobS': {'password_hash': generate_password_hash('password19'), 'entities': ['BobS']}
}

# --- Data Loading (Optimized: Load once at app startup) ---
# This prevents reading the CSV file on every dashboard request, improving performance.
try:
    df = pd.read_csv('data.csv')
    print("data.csv loaded successfully.")
except FileNotFoundError:
    print("Error: data.csv not found. Please ensure the file is in the same directory as app.py.")
    df = pd.DataFrame() # Initialize an empty DataFrame to prevent errors later
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
            # Redirect to select_report using url_for for better maintainability
            return redirect(url_for('select_report'))
        else:
            # Provide a more user-friendly error message
            return render_template('login.html', error='Invalid username or password.'), 401
    return render_template('login.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    """
    Allows logged-in users to select a report type.
    Users without associated entities are redirected to an unauthorized page.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    available_entities = users[username]['entities']

    # If the user has no entities, show an unauthorized message
    if not available_entities:
        return render_template('unauthorized.html', message="You do not have any entities assigned to view reports.")

    if request.method == 'POST':
        report_type = request.form.get('report_type')
        if report_type in ['financials', 'monthly_bonus']: # Basic validation
            session['report_type'] = report_type
            return redirect(url_for('dashboard'))
        else:
            return render_template('select_report.html', available_entities=available_entities, error="Invalid report type selected.")
    
    return render_template('select_report.html', available_entities=available_entities)

@app.route('/dashboard')
def dashboard():
    """
    Displays the dashboard based on the selected report type and user's data.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    rep = session['username']
    report_type = session.get('report_type')

    # Filter data based on the logged-in user (rep)
    # Check if df is not empty before filtering
    if not df.empty and 'Rep' in df.columns:
        rep_data = df[df['Rep'] == rep]
    else:
        rep_data = pd.DataFrame() # Empty DataFrame if data not loaded or 'Rep' column missing
        print(f"Warning: 'Rep' column not found in data.csv or data.csv is empty. Cannot filter for user '{rep}'.")


    if report_type == 'financials':
        # Hardcoded files for demonstration. In a real app, these would be dynamic.
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
            report_type=report_type,
            files=files
        )
    elif report_type == 'monthly_bonus':
        return render_template(
            'monthly_bonus.html',
            data=rep_data.to_dict(orient='records'),
            rep=rep,
            report_type=report_type
        )
    else:
        # If no report type is selected or it's invalid, redirect to select_report
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
    # Ensure 'static' directory exists for PDF examples
    if not os.path.exists('static'):
        os.makedirs('static')
    # Create dummy PDF files for demonstration if they don't exist
    for filename in ['example1.pdf', 'example2.pdf']:
        filepath = os.path.join('static', filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(f"This is a dummy PDF file: {filename}")
            print(f"Created dummy file: {filepath}")

    # Create a dummy data.csv for demonstration if it doesn't exist
    if not os.path.exists('data.csv'):
        dummy_data = {
            'Rep': ['Andrew S', 'AIM Laboratories', 'Andrew S', 'Stat Labs', 'Andrew S', 'AIM Laboratories'],
            'Value': [100, 200, 150, 300, 250, 180],
            'Date': ['2025-01-01', '2025-01-05', '2025-01-10', '2025-01-15', '2025-01-20', '2025-01-25']
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv('data.csv', index=False)
        print("Created dummy data.csv for demonstration.")

    app.run(debug=True) # debug=True should ONLY be used during development

