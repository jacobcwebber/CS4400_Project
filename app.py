# How to run if you're Brett:
# 1) cd to folder with project
# 2) export FLASK_APP=app.py
# 3) flash run
#
# Otherwise:
# 1) cd to folder with project
# 2) python app.py
#
# How to access DB:
# 1) In putty > host is academic-mysql.cc.gatech.edu
# 2) your gt username and password
# 3) mysql -u cs4400_Group_8 -p
# 4) i8vZtVC5
# 5) use cs4400_Group_8

##########################################################
##########################################################

from flask import Flask, request, render_template, url_for, logging, session, flash, redirect
import pymysql
from passlib.hash import md5_crypt
from wtforms import Form, BooleanField, StringField, TextAreaField, PasswordField, validators, ValidationError, IntegerField, RadioField
from functools import wraps
import re
from random import randint

app = Flask(__name__)

connection = pymysql.connect(host='academic-mysql.cc.gatech.edu',
                             user='cs4400_Group_8',
                             password='i8vZtVC5',
                             db='cs4400_Group_8',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor
)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

#use WTForms API to create easy form authentications
class RegisterForm(Form):
    username = StringField('', [
        validators.Length(min=4, max=25, message='Username must be 4 to 25 characters long')],
        render_kw={"placeholder": "username"})
    email = StringField('', render_kw={"placeholder": "email"})
    password = PasswordField('', [
        validators.Length(min=8, message="Password must be at least 8 digits long."),
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')],
        render_kw={"placeholder": "password"})
    confirm = PasswordField('', render_kw={"placeholder": "confirm password"})
    breezecard = StringField('', render_kw={"placeholder": "breezecard number"})

    #custom validation using regex for ensuring email address is valid
    def validate_email(form, field):
        if len(field.data) < 5 or len(field.data) > 35:
            raise ValidationError('Email must be 5 to 35 characters long')
        if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", field.data):
            raise ValidationError('Please submit a valid email')

    def validate_breezecard(form, field):
        try:
            int(field.data)
        except:
            raise ValidationError('Breezecard Number must be an integer.')
        if len(str(field.data)) != 16:
            raise ValidationError('Breezecard Number must be 16 digits')

@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.username.data
        email = form.email.data
        password = md5_crypt.encrypt(str(form.password.data))
        number = int(form.breezecard.data)

        cur = connection.cursor()

        try:
            cur.execute("INSERT INTO User(Username, Password) VALUES (%s, %s)", (username, password))
            cur.execute("INSERT INTO Passenger(Username, Email) VALUES (%s, %s)", (username, email))
        except pymysql.IntegrityError:
            flash('This username is already taken. Please try again.', 'danger')
            return redirect(url_for('register'))

        #used to distinguish between "new" and "existing" buzzcard
        if request.form['options'] == 'existing':
            try:
                cur.execute("INSERT INTO Breezecard(BreezecardNum, Value, Owner) VALUES(%s, %s, %s)", (number, 0.00, username))
            except pymysql.IntegrityError:
                flash('This Breezecard Number is already taken. Please try again.', 'danger')
                return redirect(url_for('register'))
        else:
            number = randint(0000000000000000, 9999999999999999)
            try:
                cur.execute("INSERT INTO Breezecard(BreezecardNum, Value, Owner) VALUES(%s, %s, %s)", (number, 0.00, username))
            except pymysql.IntegrityError:
                flash('This Breezecard Number is already taken. Please try again.', 'danger')
                return redirect(url_for('register'))

        connection.commit()
        cur.close()

        flash('Congratulations! You are now registered.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_attempt = request.form['password']

        cur = connection.cursor()

        result = cur.execute("SELECT * "
                             "FROM User "
                             "WHERE Username = %s"
                             , [username])

        if result > 0:
            data = cur.fetchone()
            password = data['Password']

            #checks if passwords match and logs you in if they do
            if md5_crypt.verify(password_attempt, password):
                session['logged_in'] = True
                session['username'] = username

                #sets admin session status from db query
                cur.execute("SELECT IsAdmin "
                            "FROM User "
                            "WHERE Username = %s"
                            , [username])

                if cur.fetchone()['IsAdmin'] == 1:
                    session['admin'] = True
                else:
                    session['admin'] = False

                flash('Welcome, ' + username + '. You are now logged in.', 'success')
                return redirect(url_for('index'))

            else:
                error = 'Invalid login.'
                return render_template('login.html', error=error)
            cur.close()

        else:
            error = "Username not found."
            return render_template('login.html', error=error)

    return render_template('login.html')

# disallows anyone to manipulate url manually to go to specific pages
# (i.e. cannot access passenger page if not logged in)
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash ('Unauthorized, please log in.', 'danger')
            return redirect(url_for('login'))
    return wrap

# disallows anyone to manipulate url manually to go to specific pages
# (i.e. passenger cannot change url to /admin to access admin settings)
def is_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['admin'] == True:
            return f(*args, **kwargs)
        else:
            flash ('Requires administrator access.', 'danger')
            return redirect(url_for('index'))
    return wrap

def is_passenger(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session['admin'] == False:
            return f(*args, **kwargs)
        else:
            flash ('Requires passenger access.', 'danger')
            return redirect(url_for('index'))
    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

@app.route('/passenger')
@is_logged_in
@is_passenger
def passenger():
    return render_template('passenger.html')

@app.route('/admin')
@is_logged_in
@is_admin
def admin():
    return render_template('admin.html')

@app.route('/station-management')
def station_management():
    return render_template('station_management.html')

class CreateStationForm(Form):
    name = StringField('')
    stopId = StringField('')
    fare = StringField('')
    stationType = RadioField('', choices=['Train Station', 'Bus Station'])
    intersection = StringField('')
    openStation = BooleanField('')

@app.route('/create-station')
def create_station():
    form = CreateStationForm(request.form)

    return render_template('create_station.html', form=form)

@app.route('/station-detail/<string:id>/')
@is_logged_in
@is_admin
def station_detail(id):
    cur = connection.cursor()
    result = cur.execute("SELECT * FROM stations WHERE id = %s", [id])
    station = result.fetchone()

    return render_template('station_detail.html', id=station)

@app.route('/suspended-cards')
@is_logged_in
def suspended_cards():
    return render_template('suspended_cards.html')

class AdminCardManagementForm(Form):
    owner = StringField('')
    number = StringField('')
    value_lower = StringField('')
    value_upper = StringField('')
    show_suspended = BooleanField('')
    set_value = StringField('')
    transfer_to = StringField('')

@app.route('/card-management-admin')
@is_logged_in
@is_admin
def card_management_admin():
    form = AdminCardManagementForm(request.form)

    return render_template('card_management_admin.html', form=form)

class FlowReportForm(Form):
    start = StringField('')
    end = StringField('')

@app.route('/flow-report')
@is_logged_in
@is_admin
def flow_report():
    form = FlowReportForm(request.form)

    return render_template('flow_report.html', form=form)

@app.route('/passenger/card-management-passenger')
@is_logged_in
@is_passenger
def card_management_passenger():
    return render_template('card_management_passenger.html')

@app.route('/trip-history/<string:id>/')
@is_logged_in
def trip_history():
    return render_template('trip_history.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404

if __name__ == '__main__':
    app.secret_key='supersecretkey'
    app.run(debug=True)
