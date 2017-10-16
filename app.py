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

#render login/registration page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/passenger')
def passenger():
    return render_template('passenger.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/station-management')
def station_management():
    return render_template('station_management.html')

@app.route('/admin/station-management/create-station')
def create_station():
    return render_template('create_station.html')

@app.route('/admin/station-detail/1')
def station_detail(id=1):
    return render_template('station_detail.html', id=id)

@app.route('/admin/suspended-cards')
def suspended_cards():
    return render_template('suspended_cards.html')

@app.route('/admin/card-management')
def card_management_admin():
    return render_template('card_management_admin.html')

@app.route('/admin/flow-report')
def flow_report():
    return render_template('flow_report.html')

@app.route('/passenger/card-management')
def card_management_passenger():
    return render_template('card_management_passenger.html')

@app.route('/passenger/trip-history')
def trip_history():
    return render_template('trip_history.html')