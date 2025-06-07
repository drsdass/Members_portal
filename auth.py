
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from functools import wraps
from . import models # Import models from the same package

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """
    Decorator to check if the user is logged in and has a selected role.
    Redirects to login page if not authenticated, or to role selection if no role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if 'selected_role' not in session:
            flash('Please select a role to proceed.', 'error')
            return redirect(url_for('auth.select_role'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """
    Decorator to check if the logged-in user's role is in the allowed_roles list.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session or 'selected_role' not in session:
                flash('Please log in and select a role to access this page.', 'error')
                return redirect(url_for('auth.login'))

            user_role = session.get('selected_role')
            if user_role not in allowed_roles:
                flash('You do not have the necessary permissions to access this page.', 'error')
                return redirect(url_for('unauthorized')) # Redirect to a generic unauthorized page
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    selected_role = session.get('selected_role')
    if not selected_role:
        flash('Please select a role first.', 'error')
        return redirect(url_for('auth.select_role'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_info = models.get_user(username)

        if user_info and check_password_hash(user_info['password_hash'], password):
            # Check if the user's assigned role matches the selected role
            if user_info['role'] != selected_role:
                flash(f'Your credentials are valid, but your assigned role is "{user_info["role"]}". You selected "{selected_role}". Please select the correct role.', 'error')
                session.clear() # Clear session to force re-selection
                return redirect(url_for('auth.select_role'))

            session['username'] = username
            session['selected_role'] = selected_role
            session['user_role'] = user_info['role'] # Store the actual role from user data

            if selected_role == 'patient':
                # For patients, directly set their patient_id in session
                session['patient_id'] = user_info.get('patient_id')
                if not session['patient_id']:
                    flash("Patient ID not assigned to this user.", 'error')
                    session.clear()
                    return redirect(url_for('auth.select_role'))
                return redirect(url_for('reports.patient_results'))
            elif selected_role == 'physician_provider':
                # For physicians, redirect to select entity if they have multiple, or directly to report
                available_entities = models.get_available_entities_for_user(username, selected_role)
                if len(available_entities) > 1:
                    return redirect(url_for('reports.select_entity'))
                elif len(available_entities) == 1:
                    session['selected_entity'] = available_entities[0]
                    flash(f'Welcome, {username}! You are logged in as {selected_role.replace("_", " ").title()} for {session["selected_entity"]}.', 'success')
                    return redirect(url_for('reports.dashboard'))
                else:
                    flash('No entities assigned to this physician/provider account.', 'error')
                    session.clear()
                    return redirect(url_for('auth.select_role'))
            else:
                flash(f'Welcome, {username}! You are logged in as {selected_role.replace("_", " ").title()}.', 'success')
                # Admins and Business Dev Managers go to entity selection
                return redirect(url_for('reports.select_entity'))
        else:
            flash('Invalid username or password for the selected role.', 'error')

    return render_template('login.html', selected_role=selected_role)

@auth_bp.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.select_role'))

@auth_bp.route('/select_role', methods=['GET', 'POST'])
def select_role():
    if request.method == 'POST':
        role = request.form.get('role')
        if role in ['admin', 'business_dev_manager', 'physician_provider', 'patient']:
            session['selected_role'] = role
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid role selection.', 'error')
    return render_template('role_selection.html')

@auth_bp.route('/register_physician', methods=['GET', 'POST'])
@auth_bp.route('/register_provider', methods=['GET', 'POST']) # Alias route for clarity
@role_required(['admin']) # Only admins can register new physicians/providers
def register_physician():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name')
        entity = request.form.get('entity')

        if not username or not password or not confirm_password or not full_name or not entity:
            flash('All fields are required.', 'error')
            return render_template('register_physician.html', master_entities=models.MASTER_ENTITIES)

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register_physician.html', master_entities=models.MASTER_ENTITIES)

        if entity not in models.MASTER_ENTITIES:
            flash('Invalid entity selected.', 'error')
            return render_template('register_physician.html', master_entities=models.MASTER_ENTITIES)

        # Register as a physician/provider role
        success, message = models.register_user(username, password, 'physician_provider', entity, full_name=full_name)
        if success:
            flash('Physician/Provider registered successfully!', 'success')
            return redirect(url_for('reports.dashboard')) # Or redirect to a success page
        else:
            flash(message, 'error')

    return render_template('register_physician.html', master_entities=models.MASTER_ENTITIES)
