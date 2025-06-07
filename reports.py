
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_from_directory
from functools import wraps
import pandas as pd
import datetime
import re
from . import models # Import models from the same package
from .auth import login_required, role_required # Import decorators from auth blueprint

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    return redirect(url_for('reports.dashboard'))

@reports_bp.route('/dashboard')
@login_required
def dashboard():
    current_username = session.get('username')
    user_role = session.get('user_role') # This is the actual role assigned to the user
    selected_role = session.get('selected_role') # This is the role the user selected for the session

    # Check for direct access to dashboard without entity or report type
    if selected_role not in ['admin', 'business_dev_manager', 'physician_provider', 'patient']:
        flash('Please select a role to view the dashboard.', 'error')
        return redirect(url_for('auth.select_role'))

    # If user selected a patient role, always redirect to patient results
    if selected_role == 'patient':
        return redirect(url_for('reports.patient_results'))

    # If user selected physician and has only one entity, redirect to patient results for that entity
    if selected_role == 'physician_provider':
        available_entities = models.get_available_entities_for_user(current_username, user_role)
        if len(available_entities) == 1:
            session['selected_entity'] = available_entities[0] # Automatically select the only entity
            return redirect(url_for('reports.patient_results'))

    # For other roles, or if physician has multiple entities:
    # Get available report types based on the user's actual role
    available_report_types = models.get_report_types_for_role(user_role)

    # Get the selected entity, month, and year from session or request
    selected_entity = session.get('selected_entity')
    selected_month = request.args.get('month', session.get('selected_month'))
    selected_year = request.args.get('year', session.get('selected_year'))
    report_type = request.args.get('report_type', session.get('report_type'))

    # Update session with current selections
    session['selected_month'] = selected_month
    session['selected_year'] = selected_year
    session['report_type'] = report_type

    # Initialize data for templates
    report_data = None
    report_columns = []
    report_title = "Dashboard"
    files = {}
    message = "Please select a report type from the sidebar."

    if report_type:
        definition = models.get_report_definition(report_type)
        if not definition:
            flash(f'Invalid report type: {report_type}', 'error')
            return redirect(url_for('reports.dashboard')) # Redirect to dashboard without specific report

        report_title = definition['name']
        report_columns = definition['columns']

        if report_type == 'marketing_material':
            files = models.get_marketing_materials(selected_entity)
            message = None # No generic message needed for marketing materials
        elif report_type == 'monthly_bonus':
            # Monthly bonus report logic
            if not selected_month or not selected_year:
                flash('Please select a month and year for the Monthly Bonus Report.', 'info')
                return redirect(url_for('reports.select_report', report_type='monthly_bonus'))
            else:
                # Special handling for monthly bonus, it's always for the logged-in user's entities
                # Admins and specific users get all data; others filtered by their associated rep name/username
                df_filtered = models.filter_financial_data(
                    models.data_df,
                    selected_entity=None, # Monthly bonus is not entity-filtered in the same way
                    selected_month=selected_month,
                    selected_year=selected_year,
                    current_username=current_username,
                    entity_filter_enabled=False # Filter by username in this case
                )

                # Filter by entity if the user is NOT an unfiltered access user
                if current_username not in models.UNFILTERED_ACCESS_USERS:
                    user_entities = models.get_user(current_username).get('entities', [])
                    df_filtered = df_filtered[df_filtered['Entity'].isin(user_entities)]

                # Group by 'Associated Rep Name' (and 'Entity' if it's not All Entities)
                group_cols = ['Associated Rep Name']
                if selected_entity and selected_entity != 'All Entities':
                    group_cols.append('Entity')

                # Filter to current user's associated rep name if they are not unfiltered access
                if current_username not in models.UNFILTERED_ACCESS_USERS:
                    df_filtered = df_filtered[df_filtered['Username'].apply(lambda x: current_username in x.split(','))]

                if not df_filtered.empty:
                    # Aggregate the relevant columns for monthly bonus
                    bonus_data = df_filtered.groupby(['Associated Rep Name', 'Entity']).agg(
                        Reimbursement=pd.NamedAgg(column='Reimbursement', aggfunc='sum'),
                        COGS=pd.NamedAgg(column='COGS', aggfunc='sum'),
                        Net=pd.NamedAgg(column='Net', aggfunc='sum'),
                        Commission=pd.NamedAgg(column='Commission', aggfunc='sum')
                    ).reset_index()

                    # Round numeric columns to 2 decimal places
                    numeric_cols = ['Reimbursement', 'COGS', 'Net', 'Commission']
                    for col in numeric_cols:
                        if col in bonus_data.columns:
                            bonus_data[col] = bonus_data[col].round(2)

                    report_data = bonus_data.to_dict(orient='records')
                    report_columns = ['Associated Rep Name', 'Entity', 'Reimbursement', 'COGS', 'Net', 'Commission']
                else:
                    message = "No data available for the selected month/year and your associated entities."
                    report_data = [] # Ensure report_data is an empty list if no data
                    report_columns = [] # Ensure report_columns is empty

            return render_template(
                'monthly_bonus.html',
                current_username=current_username,
                report_data=report_data,
                report_columns=report_columns,
                report_title=report_title,
                selected_month=selected_month,
                selected_year=selected_year,
                months=models.MONTHS,
                years=models.YEARS,
                message=message
            )
        else: # Generic financial reports
            if not selected_entity:
                flash('Please select an entity to view this report.', 'info')
                # Redirect to the select_entity page if no entity is chosen, unless it's an admin/bd manager
                if selected_role in ['admin', 'business_dev_manager']:
                    return redirect(url_for('reports.select_entity'))
                else:
                    # For other roles like physician/patient, this case should ideally not happen
                    # as they are redirected earlier or forced to select entity.
                    return redirect(url_for('reports.dashboard'))

            df_filtered = models.filter_financial_data(
                models.data_df,
                selected_entity=selected_entity,
                selected_month=selected_month,
                selected_year=selected_year
            )

            # Further filter by the current user's associated username if not an unfiltered access user
            if current_username not in models.UNFILTERED_ACCESS_USERS and user_role not in ['admin']:
                if 'Username' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['Username'].apply(lambda x: current_username in x.split(','))]
                else:
                    flash('Error: "Username" column not found in data for filtering.', 'error')
                    report_data = []

            if not df_filtered.empty:
                # Select only the relevant columns and convert to list of dicts
                if 'PatientID' in report_columns and 'PatientID' not in df_filtered.columns:
                    # This handles the case where PatientID might not be in all dummy data
                    # In real data, you'd expect it to be present if column is requested
                    flash('PatientID column not found in data for this report.', 'error')
                    report_data = []
                else:
                    report_data = df_filtered[report_columns].to_dict(orient='records')
            else:
                message = "No data available for the selected criteria."
                report_data = []

    # Render generic_report for most financial reports and marketing materials
    if report_type == 'marketing_material':
        return render_template(
            'dashboard.html',
            current_username=current_username,
            user_role=user_role,
            selected_entity=selected_entity,
            available_entities=models.get_available_entities_for_user(current_username, user_role),
            available_report_types=available_report_types,
            report_type=report_type,
            report_title=report_title,
            files=files,
            message=message
        )
    else:
        return render_template(
            'generic_report.html',
            current_username=current_username,
            user_role=user_role,
            selected_entity=selected_entity,
            available_entities=models.get_available_entities_for_user(current_username, user_role),
            available_report_types=available_report_types,
            report_type=report_type,
            report_title=report_title,
            report_data=report_data,
            report_columns=report_columns,
            selected_month=selected_month,
            selected_year=selected_year,
            months=models.MONTHS,
            years=models.YEARS,
            message=message
        )


@reports_bp.route('/select_entity', methods=['GET', 'POST'])
@role_required(['admin', 'business_dev_manager', 'physician_provider'])
def select_entity():
    current_username = session.get('username')
    user_role = session.get('user_role') # Use actual assigned role for entity permissions

    # Redirect patient role directly to patient results
    if user_role == 'patient':
        return redirect(url_for('reports.patient_results'))

    available_entities = models.get_available_entities_for_user(current_username, user_role)

    # If only one entity is available for a physician/provider, automatically select it and go to dashboard
    if user_role == 'physician_provider' and len(available_entities) == 1:
        session['selected_entity'] = available_entities[0]
        return redirect(url_for('reports.dashboard'))

    if request.method == 'POST':
        entity_name = request.form.get('entity_name')
        if entity_name:
            if entity_name == 'All Entities' and user_role in ['admin', 'business_dev_manager']:
                session['selected_entity'] = entity_name
                flash('All Entities selected.', 'info')
                return redirect(url_for('reports.dashboard'))
            elif entity_name in available_entities:
                session['selected_entity'] = entity_name
                flash(f'Entity "{entity_name}" selected successfully.', 'success')
                return redirect(url_for('reports.dashboard'))
            else:
                flash('You do not have permission to access the selected entity.', 'error')
        else:
            flash('Please select an entity.', 'error')

    # Add 'All Entities' option for Admin and Business Development Managers
    display_entities = available_entities[:] # Create a copy
    if user_role in ['admin', 'business_dev_manager'] and 'All Entities' not in display_entities:
        display_entities.insert(0, 'All Entities') # Add at the beginning

    return render_template('select_entity.html', available_entities=display_entities)

@reports_bp.route('/select_report', methods=['GET', 'POST'])
@login_required
def select_report():
    current_username = session.get('username')
    user_role = session.get('user_role') # Actual role
    selected_role = session.get('selected_role') # Session role (could be different if user tried to circumvent)

    # Sanity check: Ensure user is not a patient trying to access this route
    if selected_role == 'patient':
        flash('Patients do not select reports this way. Redirecting to your results.', 'info')
        return redirect(url_for('reports.patient_results'))
    
    # Ensure current user has a valid entity selected, unless it's a direct route from dashboard for monthly bonus
    selected_entity = session.get('selected_entity')
    report_type_param = request.args.get('report_type')

    if not selected_entity and selected_role != 'patient' and report_type_param != 'monthly_bonus':
        flash('Please select an entity first.', 'info')
        return redirect(url_for('reports.select_entity'))


    available_report_types = models.get_report_types_for_role(user_role)
    available_entities = models.get_available_entities_for_user(current_username, user_role)

    # For admin/BDM, add 'All Entities' option for selection if not already there
    if user_role in ['admin', 'business_dev_manager'] and 'All Entities' not in available_entities:
        available_entities.insert(0, 'All Entities')

    # Pre-select values if coming from dashboard link
    pre_selected_report_type = request.args.get('report_type', session.get('report_type'))
    pre_selected_entity = request.args.get('entity', session.get('selected_entity'))
    pre_selected_month = request.args.get('month', session.get('selected_month'))
    pre_selected_year = request.args.get('year', session.get('selected_year'))


    if request.method == 'POST':
        selected_report_type = request.form.get('report_type')
        selected_entity_form = request.form.get('entity')
        selected_month_form = request.form.get('month')
        selected_year_form = request.form.get('year')

        # Update session with new selections
        session['report_type'] = selected_report_type
        session['selected_entity'] = selected_entity_form
        session['selected_month'] = selected_month_form
        session['selected_year'] = selected_year_form

        # Determine where to redirect based on report type
        if selected_report_type == 'monthly_bonus':
             # Monthly bonus report requires month/year, but entity can be 'All Entities' for admins/BDM
            if not selected_month_form or not selected_year_form:
                flash('Please select a month and year for the Monthly Bonus Report.', 'error')
                # Render the form again with existing selections and error
                return render_template(
                    'select_report.html',
                    available_report_types=available_report_types,
                    available_entities=available_entities,
                    months=models.MONTHS,
                    years=models.YEARS,
                    selected_report_type=selected_report_type,
                    selected_entity=selected_entity_form,
                    selected_month=selected_month_form,
                    selected_year=selected_year_form
                )
            return redirect(url_for('reports.dashboard', report_type=selected_report_type, entity=selected_entity_form, month=selected_month_form, year=selected_year_form))
        elif selected_report_type == 'patient_results':
             # Patient results handled by a specific route, but we still need entity selected.
             # This route will only be accessible by patient or physician.
            if selected_role == 'patient':
                return redirect(url_for('reports.patient_results'))
            elif selected_role == 'physician_provider':
                return redirect(url_for('reports.patient_results', entity=selected_entity_form)) # Pass entity for physician to filter
            else:
                flash('Invalid role for Patient Results report.', 'error')
                return redirect(url_for('reports.dashboard'))
        elif selected_report_type:
            return redirect(url_for('reports.dashboard', report_type=selected_report_type, entity=selected_entity_form, month=selected_month_form, year=selected_year_form))
        else:
            flash('Please select a report type.', 'error')

    return render_template(
        'select_report.html',
        available_report_types=available_report_types,
        available_entities=available_entities,
        months=models.MONTHS,
        years=models.YEARS,
        selected_report_type=pre_selected_report_type,
        selected_entity=pre_selected_entity,
        selected_month=pre_selected_month,
        selected_year=pre_selected_year
    )

@reports_bp.route('/patient_results', methods=['GET', 'POST'])
@login_required
@role_required(['patient', 'physician_provider'])
def patient_results():
    current_username = session.get('username')
    user_role = session.get('user_role')
    patient_id = session.get('patient_id') # Only set for 'patient' role

    selected_entity_from_session = session.get('selected_entity')
    entity_param = request.args.get('entity')

    # Determine the entity to use for filtering
    target_entity = None
    if user_role == 'patient':
        # For patients, the entity is determined by their assigned entity in models.py
        user_info = models.get_user(current_username)
        if user_info and user_info.get('entities'):
            target_entity = user_info['entities'][0] # Assuming patient has only one assigned entity
        if not patient_id:
            flash("Error: Patient ID not found for your account.", 'error')
            return redirect(url_for('auth.logout')) # Force logout if no patient ID
    elif user_role == 'physician_provider':
        # For physicians, it comes from the selected entity (via select_entity or dashboard link)
        target_entity = entity_param if entity_param else selected_entity_from_session
        if not target_entity:
            flash("Please select an entity to view patient results.", 'info')
            return redirect(url_for('reports.select_entity'))
        
        # Verify physician has access to this entity
        available_entities = models.get_available_entities_for_user(current_username, user_role)
        if target_entity not in available_entities:
            flash(f"You do not have access to view patient results for {target_entity}.", 'error')
            return redirect(url_for('reports.select_entity'))

    if not target_entity:
        flash("Could not determine the entity for patient results.", 'error')
        return redirect(url_for('reports.dashboard'))

    patient_name = models.get_user(current_username).get('full_name', current_username) if user_role == 'physician_provider' else current_username

    if user_role == 'patient':
        results_by_dos = models.get_patient_result_files(patient_id, target_entity)
        if not results_by_dos:
            message = "No patient results found for your ID at this entity."
        else:
            message = None
        return render_template('patient_results.html', patient_name=patient_name, results_by_dos=results_by_dos, message=message)

    elif user_role == 'physician_provider':
        # For physicians, we might need a search form for patient ID
        search_patient_id = request.args.get('patient_id') or request.form.get('patient_id')
        results_by_dos = {}
        message = None

        if search_patient_id:
            results_by_dos = models.get_patient_result_files(search_patient_id, target_entity)
            if not results_by_dos:
                message = f"No results found for Patient ID: {search_patient_id} at {target_entity}."
            else:
                message = f"Results for Patient ID: {search_patient_id} at {target_entity}."
        else:
            message = "Enter a Patient ID to view results."

        return render_template(
            'patient_results.html',
            patient_name=patient_name,
            results_by_dos=results_by_dos,
            message=message,
            current_search_patient_id=search_patient_id,
            selected_entity=target_entity, # Pass selected entity to template
            show_search_form=True # Indicate to the template to show the search form
        )
    return redirect(url_for('reports.dashboard')) # Fallback


@reports_bp.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy.html')

@reports_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html')

@reports_bp.route('/static/dummy_files/<path:filename>')
def serve_dummy_files(filename):
    # This route is purely for demonstrating file downloads in the dummy data setup.
    # In a real application, these files would be served from a secure cloud storage (S3, GCS)
    # or a dedicated static file server, with proper access control.
    dummy_files_dir = os.path.join(reports_bp.root_path, 'static', 'dummy_files')
    if not os.path.exists(dummy_files_dir):
        os.makedirs(dummy_files_dir)
        # Create some dummy files if they don't exist
        with open(os.path.join(dummy_files_dir, 'First_Bio_Lab_Brochure.pdf'), 'w') as f:
            f.write("Dummy PDF content for First Bio Lab Brochure")
        with open(os.path.join(dummy_files_dir, 'First_Bio_Lab_Services.pptx'), 'w') as f:
            f.write("Dummy PPTX content for First Bio Lab Services")
        with open(os.path.join(dummy_files_dir, 'Genetics_Overview.pdf'), 'w') as f:
            f.write("Dummy PDF content for Genetics Overview")
        with open(os.path.join(dummy_files_dir, 'AIM_Labs_Prospectus.pdf'), 'w') as f:
            f.write("Dummy PDF content for AIM Labs Prospectus")
        with open(os.path.join(dummy_files_dir, 'Patient_Report_AB123_2025_03.pdf'), 'w') as f:
            f.write("Dummy PDF content for Patient Report AB123 - March 2025")
        with open(os.path.join(dummy_files_dir, 'Lab_Results_AB123_2025_03.pdf'), 'w') as f:
            f.write("Dummy PDF content for Lab Results AB123 - March 2025")
        with open(os.path.join(dummy_files_dir, 'Patient_Report_AB123_2024_11.pdf'), 'w') as f:
            f.write("Dummy PDF content for Patient Report AB123 - Nov 2024")
        with open(os.path.join(dummy_files_dir, 'Patient_Report_CD456_2025_01.pdf'), 'w') as f:
            f.write("Dummy PDF content for Patient Report CD456 - Jan 2025")
        with open(os.path.join(dummy_files_dir, 'Patient_Report_IJ345_2025_05.pdf'), 'w') as f:
            f.write("Dummy PDF content for Patient Report IJ345 - May 2025")
    return send_from_directory(dummy_files_dir, filename)
