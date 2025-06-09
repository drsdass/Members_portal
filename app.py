
from flask import Flask, session

app = Flask(__name__)

@app.route('/')
def index():
    user_role = session.get('role')
    return f'User role is: {user_role}'
