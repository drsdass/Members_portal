
import os
from flask import Flask, render_template, redirect, url_for, session, flash, send_from_directory
from flask_moment import Moment
import datetime
import re # Not directly used in this app.py, but kept if other parts might need it.

# Import blueprints
from auth import auth_bp
from models import get_all_reports, load_data, get_entities_for_user, get_available_report_types
from reports import reports_bp

# Initialize the Flask application
app = Flask(__name__)
moment = Moment(app) # Initialize Flask-Moment here

# --- Configuration ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_and_long_random_key_here_replace_me_in_production')

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(reports_bp)

# Global error handler for 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('unauthorized.html', message="Page not found. Please check the URL or your permissions."), 404

# Global error handler for 403 (Forbidden)
@app.errorhandler(403)
def forbidden_access(e):
    return render_template('unauthorized.html', message="You do not have permission to access this resource."), 403

# You can keep a simple root route here that redirects to the role selection
@app.route('/')
def root():
    if 'username' in session and 'selected_role' in session:
        return redirect(url_for('reports.dashboard'))
    return redirect(url_for('auth.select_role'))


if __name__ == '__main__':
    app.run(debug=True)
