from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'Index page'

@app.route('/register/')
def register():
    return 'Registration page'

@app.route('/login/')
def login():
    return 'Login page'