
from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def home():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'], role=session.get('role'))
    return redirect(url_for('select_role'))

@app.route('/select_role', methods=['GET', 'POST'])
def select_role():
    if request.method == 'POST':
        role = request.form['role']
        session['role'] = role
        return redirect(url_for('login', role=role))
    return render_template('select_role.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        session['username'] = username
        session['role'] = role
        return redirect(url_for('home'))
    return render_template('login.html', role=role)

@app.route('/select_report')
def select_report():
    return render_template('select_report.html', username=session.get('username'), role=session.get('role'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('select_role'))

if __name__ == '__main__':
    app.run(debug=True)
