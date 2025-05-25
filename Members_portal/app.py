
from flask import Flask, render_template, request, redirect, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# User and entity setup
users = {
    'Andrew S': {'password': 'password1', 'entities': ['First Bio Lab','First Bio Genetics','First Bio Lab of Illinois']},
    'AIM Laboratories': {'password': 'password2', 'entities': ['AIM Laboratories']},
    'AMICO Dx': {'password': 'password3', 'entities': ['AMICO Dx']},
    'Enviro Labs': {'password': 'password4', 'entities': ['Enviro Labs']},
    'Stat Labs': {'password': 'password5', 'entities': ['Stat Labs']},
    'Celano Venture': {'password': 'password6', 'entities': ['Celano Venture']},
    'HCM Crew LLC': {'password': 'password7', 'entities': ['HCM Crew LLC']},
    'Andrew': {'password': 'password8', 'entities': []},
    'House': {'password': 'password9', 'entities': []},
    'Celano/GD': {'password': 'password10', 'entities': ['Celano/GD']},
    'SAV LLC': {'password': 'password11', 'entities': ['SAV LLC']},
     'Andrew S2': {'password': 'password12', 'entities': ['Andrew S']},
    'Sonny': {'password': 'password13', 'entities': []},
     'GD Laboratory/360 Health': {'password': 'password14', 'entities': ['GD Laboratory/360 Health']},
       '2AZ Investments LLC': {'password': 'password15', 'entities': ['2AZ Investments LLC']},
         'GD Laboratory': {'password': 'password16', 'entities': ['GD Laboratory']},
      'HCM Crew LLC/ 360 Health': {'passwordaccount_id: 17', 'entities': ['HCM Crew LLC/ 360 Health']},
        'DarangT': {'password': 'password18', 'entities': ['DarangT']},
          'BobS': {'password': 'password19', 'entities': ['BobS']}
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect('/select_report')
        else:
            return 'Invalid credentials', 401
    return render_template('login.html')

@app.route('/select_report', methods=['GET', 'POST'])
def select_report():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    available_entities = users[username]['entities']
    if not available_entities:
        return render_template('unauthorized.html')
    if request.method == 'POST':
        report_type = request.form['report_type']
        session['report_type'] = report_type
        return redirect('/dashboard')
    return render_template('select_report.html', available_entities=available_entities)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    rep = session['username']
    report_type = session.get('report_type')

    df = pd.read_csv('data.csv')
    rep_data = df[df['Rep'] == rep]

    if report_type == 'financials':
         files = [{'name': '2023 Full Report.pdf', 'webViewLink': '/static/example1.pdf'}, {'name': '2024 Full Report.pdf', 'webViewLink': '/static/example2.pdf'},{'name': '2025 YTD Financials.pdf', 'webViewLink': '/static/example1.pdf'}, {'name': '2025 Last Month Financials.pdf', 'webViewLink': '/static/example2.pdf'}]
         return render_template('dashboard.html', data=rep_data.to_dict(orient='records'), rep=rep, report_type=report_type, files=files)
    elif report_type == 'monthly_bonus':
         return render_template('monthly_bonus.html', data=rep_data.to_dict(orient='records'), rep=rep, report_type=report_type)
    else:
        return "Invalid report type", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__":
    app.run(debug=True)

