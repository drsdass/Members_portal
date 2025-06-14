import os
import pandas as pd
from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_moment import Moment
import datetime
import re
from functools import wraps

# Import blueprints
from .auth import auth_bp
from .reports import reports_bp
from . import models # Import models to access centralized data like users and MASTER_ENTITIES

# Initialize the Flask application
app = Flask(__name__)
moment = Moment(app) # Initialize Flask-Moment here

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(reports_bp, url_prefix='/reports') # Ensure all reports routes are under /reports

# --- Data Loading (Optimized: Load once at app startup) ---
# data_df will be loaded from models.py when models is imported
# This ensures a single source of truth for your dataframes.

# Global lists for months and years (for dropdowns) - These can remain in app.py if truly global or moved to models.py
MONTHS = models.MONTHS # Get from models.py
YEARS = models.YEARS   # Get from models.py


# --- Login and Role Selection (Centralized in auth.py blueprint) ---
# The main login and role selection routes are now handled by the auth blueprint.
# The app.py will only contain the root redirect and logout.

# Decorator to check if user is logged in
# Note: This is a duplicate of the one in auth.py.
# If auth.login_required is used consistently, this one can be removed.
# For now, keeping it here for routes directly defined in app.py if any,
# but it's better to use the one from auth.py across the app.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.select_role')) # Redirect to auth blueprint's select_role
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check if the user has the required role
# Note: This is a duplicate of the one in auth.py.
# Prefer using auth.role_required.
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
    # This route is now primarily handled by auth.py blueprint.
    # Redirect to the blueprint's login route.
    return redirect(url_for('auth.login'))

@app.route('/logout')
@login_required # Use the decorator from here or auth.py
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.select_role')) # Redirect to auth blueprint's select_role

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html', message=flash.get_flashed_messages(with_categories=True))


# --- Main Application Routes (Now often handled by blueprints) ---

# Root route - typically redirects to a default entry point like dashboard
@app.route('/')
@login_required # Ensure user is logged in to access root
def index():
    return redirect(url_for('reports.dashboard')) # Redirect to reports blueprint's dashboard

# Select Role route (Moved to auth.py)
@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    return redirect(url_for('auth.select_role')) # Redirect to auth blueprint's select_role


# --- Dashboard and Report Views (Now handled by reports.py blueprint) ---
# The /dashboard, /select_entity, /select_report, /patient_results routes
# are now part of the 'reports_bp' blueprint.

# --- File Serving ---

# This route serves dummy reports. It's often better placed in a blueprint
# if specific to reports, or in app.py if generic. Keeping it here for now
# as it might interact with app.root_path.
@app.route('/download_report/<report_type>/<entity>/<display_name_part>')
@app.route('/download_report/<report_type>/<entity>/<display_name_part>/<basis>/<month>/<year>')
@app.route('/patient_results/<path:filename>') # For patient specific reports direct links
@app.route('/marketing_material/<path:filename>') # For marketing materials direct links
@app.route('/training_material/<path:filename>') # For training materials direct links
@login_required
def download_report(report_type=None, entity=None, display_name_part=None, basis=None, month=None, year=None, filename=None):
    """
    Serves dummy PDF/PPTX files based on report type or direct filename.
    In a real application, this would fetch from secure cloud storage.
    """
    reports_dir = os.path.join(app.root_path, 'static', 'reports')
    marketing_dir = os.path.join(app.root_path, 'static', 'marketing_materials')
    training_dir = os.path.join(app.root_path, 'static', 'training_materials')
    patient_reports_dir = os.path.join(app.root_path, 'static', 'patient_reports')

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(marketing_dir, exist_ok=True)
    os.makedirs(training_dir, exist_ok=True)
    os.makedirs(patient_reports_dir, exist_ok=True)

    # Determine the directory and filename based on the route parameters
    if report_type == 'financials' and display_name_part:
        # Generate dummy filename for financial reports
        filename_to_serve = f"{entity}-{display_name_part.replace(' ', '_')}"
        if basis:
            filename_to_serve += f"-{basis.replace(' ', '_')}"
        filename_to_serve += ".pdf"
        target_dir = reports_dir
    elif report_type == 'marketing_material' and display_name_part:
        # Generate dummy filename for marketing materials
        filename_to_serve = f"{display_name_part.replace(' ', '_')}.pdf" # Assuming PDF, adjust for pptx etc.
        target_dir = marketing_dir
    elif report_type == 'training_material' and display_name_part:
        # Generate dummy filename for training materials
        filename_to_serve = f"{display_name_part.replace(' ', '_')}.pdf" # Assuming PDF, adjust for pptx etc.
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
        # Fallback for direct filename in the root /download_report path
        if filename:
            filename_to_serve = filename
            target_dir = reports_dir # Default to reports_dir if no specific type is matched
        else:
            flash("Invalid download request.", 'error')
            return redirect(url_for('reports.dashboard'))


    dummy_file_path = os.path.join(target_dir, filename_to_serve)

    # Create dummy PDF content if file doesn't exist
    if not os.path.exists(dummy_file_path):
        with open(dummy_file_path, 'wb') as f:
            # Simple dummy PDF content
            f.write(b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Contents 4 0 R/Parent 2 0 R>>endobj 4 0 obj<</Length 55>>stream\nBT /F1 24 Tf 100 700 Td (This is a dummy PDF report.) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000055 00000 n\n0000000104 00000 n\n0000000192 00000 n\ntrailer<</Size 5/Root 1 0 R>>startxref\n296\n%%EOF')
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
    # Log the error for debugging
    app.logger.error(f"Server Error: {e}")
    return render_template('500.html'), 500

# --- Health Check (for Render.com or other deployment platforms) ---
@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

