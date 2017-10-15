from flask import Flask, request, render_template, url_for
app = Flask(__name__)

#To start local server:
#1) In command line go to directory with project
#2) Type FLASK_APP=app.py
#3) For debugger mode type FLASK_DEBUG=1 (this auto-reloads the page upon code changes)
#4) Type flask run
#5) Copy resulting IP address into url bar

app.config.update(
    TEMPLATES_AUTO_RELOAD=True,
    EXPLAIN_TEMPLATE_LOADING=True)

#render login page
@app.route('/')
def index():
    return render_template('index.html')

#render user login page

#render admin login page
@app.route('/admin')
def admin():
    return render_template('admin.html')


