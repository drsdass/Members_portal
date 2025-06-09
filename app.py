
from flask import Flask, render_template, redirect, url_for, session, request
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load data
try:
    df = pd.read_csv('data.csv')
    print("data.csv loaded successfully.")
except Exception as e:
    df = pd.DataFrame()
    print(f"Error loading data.csv: {e}")

try:
    access_df = pd.read_csv('access.csv')
    print("access.csv loaded successfully.")
except Exception as e:
    access_df = pd.DataFrame()
    print(f"Error loading access.csv: {e}")

# Login route
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        session['role'] = role
        return redirect(url_for('home'))
    return render_template('login.html', role=role)

@app.route('/')
def home():
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('select_role'))
    return render_template('dashboard.html', username=session['username'], role=session['role'])

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    if request.method == 'POST':
        selected_role = request.form.get('role')
        return redirect(url_for('login', role=selected_role))
    return render_template('select_role.html')

@app.route('/select_report')
def select_report():
    if 'username' not in session or 'role' not in session:
        return redirect(url_for('select_role'))

    username = session['username']
    role = session['role']

    try:
        user_row = access_df[access_df['Admin'] == username]
        user_authorized_entities = user_row.drop(columns='Admin').loc[:, lambda df: df.eq('Yes') | df.eq('Yes.')].columns.tolist()
    except Exception as e:
        print(f"Access error: {e}")
        user_authorized_entities = []

    months = [{'value': f'{i:02}', 'name': pd.to_datetime(f'2025-{i:02}-01').strftime('%B')} for i in range(1, 13)]
    years = sorted(df['Year'].dropna().unique().astype(str), reverse=True)

    return render_template(
        'select_report.html',
        username=username,
        role=role,
        user_authorized_entities=user_authorized_entities,
        available_report_types=[
            {'value': 'financials', 'name': 'Financials Report'},
            {'value': 'monthly_bonus', 'name': 'Monthly Bonus Report'},
            {'value': 'requisitions', 'name': 'Requisitions'},
            {'value': 'marketing_material', 'name': 'Marketing Material'},
            {'value': 'patient_specific', 'name': 'Patient Specific Reports'}
        ],
        months=months,
        years=years,
        selected_entity='',
        selected_report_type='',
        selected_month='',
        selected_year=''
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('select_role'))

if __name__ == '__main__':
    app.run(debug=True)

# For Gunicorn
app = app
