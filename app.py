import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_moment import Moment
import datetime
import re
from functools import wraps
import sys

# IMPORTANT: Ensure the project root directory is on the Python path
# This is crucial for relative imports to work when app.py is the entry point
# and sibling modules (auth, reports, models) are part of the same package.
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import blueprints using relative imports
# These assume that app.py, auth.py, reports.py, and models.py are all in the same package (due to __init__.py)
from .auth import auth_bp
from .reports import reports_bp
from . import models # Import models as a module within the same package

# Initialize the Flask application
app = Flask(__name__)
moment = Moment(app) # Initialize Flask-Moment here

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(reports_bp, url_prefix='/reports')

# --- Global lists for months and years (Defined directly in app.py for robustness) ---
# These were causing an AttributeError when imported from models.py in some environments.
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


# --- Login and Role Selection (Centralized in auth.py blueprint) ---
# The main login and role selection routes are now handled by the auth blueprint.
# The app.py will only contain the root redirect and logout.

# Decorator to check if user is logged in
# Using the one from auth.py directly is preferred.
# Keeping this local one for clarity that it's still needed if app.py has routes directly decorated.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.select_role'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if the user has the required role
# Using the one from auth.py directly is preferred.
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


@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    return redirect(url_for('auth.login'))

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.select_role'))

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html', message=flash.get_flashed_messages(with_categories=True))


# --- Main Application Routes ---

@app.route('/')
@login_required
def index():
    return redirect(url_for('reports.dashboard'))

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    return redirect(url_for('auth.select_role'))


# --- File Serving ---
# Consolidated download_report. Note: This could also be part of a blueprint if desired.
@app.route('/download_report/<report_type>/<entity>/<display_name_part>')
@app.route('/download_report/<report_type>/<entity>/<display_name_part>/<basis>/<month>/<year>')
@app.route('/patient_results/<path:filename>')
@app.route('/marketing_material/<path:filename>')
@app.route('/training_material/<path:filename>')
@login_required
def download_report(report_type=None, entity=None, display_name_part=None, basis=None, month=None, year=None, filename=None):
    reports_dir = os.path.join(app.root_path, 'static', 'reports')
    marketing_dir = os.path.join(app.root_path, 'static', 'marketing_materials')
    training_dir = os.path.join(app.root_path, 'static', 'training_materials')
    patient_reports_dir = os.path.join(app.root_path, 'static', 'patient_reports')

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(marketing_dir, exist_ok=True)
    os.makedirs(training_dir, exist_ok=True)
    os.makedirs(patient_reports_dir, exist_ok=True)

    target_dir = None
    filename_to_serve = None

    if report_type == 'financials' and display_name_part:
        filename_to_serve = f"{entity}-{display_name_part.replace(' ', '_')}"
        if basis:
            filename_to_serve += f"-{basis.replace(' ', '_')}"
        filename_to_serve += ".pdf"
        target_dir = reports_dir
    elif report_type == 'marketing_material' and display_name_part:
        filename_to_serve = f"{display_name_part.replace(' ', '_')}.pdf"
        target_dir = marketing_dir
    elif report_type == 'training_material' and display_name_part:
        filename_to_serve = f"{display_name_part.replace(' ', '_')}.pdf"
        target_dir = training_dir
    elif filename and request.path.startswith('/patient_results/'):
        filename_to_serve = filename
        target_dir = patient_reports_dir
    elif filename and request.path.startswith('/marketing_material/'):
        filename_to_serve = filename
        target_dir = marketing_dir
    elif filename and request.path.startswith('/training_material/'):
        filename_to_serve = filename
        target_dir = training_dir
    else:
        if filename:
            filename_to_serve = filename
            target_dir = reports_dir
        else:
            flash("Invalid download request.", 'error')
            return redirect(url_for('reports.dashboard'))

    dummy_file_path = os.path.join(target_dir, filename_to_serve)

    if not os.path.exists(dummy_file_path):
        with open(dummy_file_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R/Parent 2 0 R>>endobj 4 0 obj<</Length 55>>stream\nBT /F1 24 Tf 100 700 Td (This is a dummy PDF report.) Tj ET\nendstream\nendobj\\nxref\\n0 5\\n0000000000 65535 f\\n0000000009 00000 n\\n0000000055 00000 n\\n0000000104 00000 n\\n0000000192 00000 n\\ntrailer<</Size 5/Root 1 0 R>>startxref\\n296\\n%%EOF')
        print(f"Created dummy PDF: {dummy_file_path}")
    
    try:
        return send_from_directory(target_dir, filename_to_serve, as_attachment=False)
    except FileNotFoundError:
        flash("The requested file was not found.", 'error')
        return redirect(url_for('reports.dashboard'))
    except Exception as e:
        flash(f"Error serving report: {e}", 'error')
        return redirect(url_for('reports.dashboard'))


# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Server Error: {e}")
    return render_template('500.html'), 500

# --- Health Check ---
@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
