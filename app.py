# How to run:
# 1) cd to folder with project
# 2) python app.py
# 3) Go to 127.0.0.1:5000
#
# How to access DB:
# 1) In putty > host is academic-mysql.cc.gatech.edu
# 2) your gt username and password
# 3) mysql -u cs4400_Group_8 -p
# 4) i8vZtVC5
# 5) use cs4400_Group_8

################################################################################
################################################################################

from flask import Flask, jsonify, request, render_template, url_for, logging, session, flash, redirect
import pymysql
from passlib.hash import md5_crypt
from wtforms import Form, SelectField, BooleanField, StringField, PasswordField, validators, ValidationError, RadioField, DateTimeField
from functools import wraps
import re
from random import randint
import json
import datetime
import time
import sys

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
    flash('You are now logged out.', 'success')
    return redirect(url_for('index'))

class PassengerForm(Form):
    cur = connection.cursor()
    cur.execute("SELECT StopID, Name, Fare "
                "FROM Station")
    stations = cur.fetchall()
    cur.close()

    startStationsList = []
    for station in stations:
        startStationsList.append((station['Name'], station['Name'] + ' - $' + str(station['Fare'])))

    endStationsList = []
    for station in stations:
        endStationsList.append((station['StopID'], station['Name']))

    start = SelectField('', choices=startStationsList)
    end = SelectField('', choices=endStationsList)

@app.route('/change-breezecard', methods=['POST'])
def changeBreezecard():
    breezecard = request.form['breezecard']
    cur = connection.cursor()
    cur.execute("SELECT Value "
                "FROM Breezecard "
                "WHERE BreezecardNum = %s"
                , breezecard)
    value = cur.fetchone()

    return json.dumps(str(value['Value']))

@app.route('/begin-trip', methods=['POST'])
def beginTrip():
    breezecard = request.form['breezecard']
    startStation = request.form['start']
    balance = request.form['balance']

    cur = connection.cursor()
    cur.execute("SELECT Fare, StopID "
                "FROM Station "
                "WHERE Name = %s"
                , startStation)

    station = cur.fetchone()
    fare = station['Fare']
    stopId = station['StopID']

    if float(fare) > float(balance):
        cur.close()
        return json.dumps(str("low"))

    cur.execute("INSERT INTO Trip (Fare, BreezecardNum, StartsAt, EndsAt)"
                "VALUES (%s, %s, %s, %s)"
                , (float(fare), breezecard, stopId, None))

    cur.execute("UPDATE Breezecard "
                "SET Value = %s - %s "
                "WHERE BreezecardNum = %s"
                , (float(balance), float(fare), breezecard))

    connection.commit()
    cur.close()

    return json.dumps(str(float(balance) - float(fare)))

@app.route('/end-trip', methods=['POST'])
def endTrip():
    breezecard = request.form['breezecard']
    startStation = request.form['start']
    endId = request.form['end']

    cur = connection.cursor()

    cur.execute("SELECT StopID "
                "FROM Station "
                "WHERE Name = %s"
                , startStation)
    station = cur.fetchone()
    startId = station['StopID']

    cur.execute("SELECT StartTime "
                 "FROM Trip "
                 "WHERE BreezecardNum = %s AND StartsAt = %s "
                 "ORDER BY StartTime DESC LIMIT 1"
                 , (breezecard, startId))
    trip = cur.fetchone()
    startTime = trip['StartTime']

    cur.execute("UPDATE Trip "
                "SET EndsAt = %s "
                "WHERE BreezecardNum = %s AND StartTime = %s"
                , (endId, breezecard, startTime))

    connection.commit()
    cur.close()
    return None

@app.route('/passenger', methods= ['POST', 'GET'])
@is_logged_in
@is_passenger
def passenger():
    form = PassengerForm(request.form)

    cur = connection.cursor()
    cur.execute("SELECT BreezecardNum, Value "
                "FROM Breezecard "
                "WHERE Owner = %s "
                "AND BreezecardNum NOT IN (SELECT BreezecardNum FROM Conflict)",
                session['username'])

    breezecards = cur.fetchall()
    cur.close()

    return render_template('passenger.html', form=form, breezecards = breezecards)

@app.route('/admin')
@is_logged_in
@is_admin
def admin():
    return render_template('admin.html')

@app.route('/station-management')
@is_logged_in
@is_admin
def station_management():
    cur = connection.cursor()
    cur.execute("SELECT * "
                "FROM Station")

    stations = cur.fetchall()
    cur.close()

    return render_template('station_management.html', stations=stations)

class CreateStationForm(Form):
    name = StringField('', [validators.InputRequired()])
    stopId = StringField('', [
        validators.InputRequired()])
    fare = StringField('')
    isTrain = RadioField('', [
        validators.InputRequired()],
        choices=[('train', 'Train Station'), ('bus', 'Bus Station')])
    intersection = StringField('', render_kw={"placeholder": "Nearest intersection"})
    closedStatus = BooleanField('')

    def validate_fare(form, field):
        try:
            float(field.data)
        except:
            raise ValidationError('Fare must be a number.')
        if float(field.data) < 0 or float(field.data) > 50:
            raise ValidationError('Fare must be between 0 and 50')

@app.route('/create-station', methods=['POST', 'GET'])
@is_logged_in
def create_station():
    form = CreateStationForm(request.form)

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        stopId = request.form['stopId']
        fare = request.form['fare']
        if request.form['isTrain'] == 'train':
            isTrain = 1
        else:
            isTrain = 0
            intersection = request.form['intersection']
        if request.form.get('closedStatus'):
            closedStatus = 0;
        else:
            closedStatus = 1;

        cur = connection.cursor()

        try:
            cur.execute("INSERT INTO Station "
                        "VALUES (%s, %s, %s, %s, %s)"
                        , (stopId, name, float(fare), closedStatus, isTrain))
        except pymysql.IntegrityError:
            flash('This station already exists.', 'danger')
            return redirect(url_for('station_management'))

        if isTrain == 0:
            cur.execute("INSERT INTO BusStation "
                        "VALUES (%s, %s)"
                        , (stopId, intersection))
        connection.commit()
        cur.close()

        flash('Your station has been created.', 'success')
        return redirect(url_for('station_management'))

    return render_template('create_station.html', form=form)

class StationDetailForm(Form):
    fare = StringField('')
    closedStatus = BooleanField('')

@app.route('/station-detail/<string:id>/', methods=['POST', 'GET'])
@is_logged_in
@is_admin
def station_detail(id):
    form = StationDetailForm(request.form)

    cur = connection.cursor()
    cur.execute("SELECT * FROM Station s LEFT OUTER JOIN BusStation b "
                         "ON s.StopID = b.StopID "
                         "WHERE s.StopID = %s"
                         , [id])
    station = cur.fetchone()
    cur.close()

    form.fare.data = str(station['Fare'])
    form.closedStatus.data = not station['ClosedStatus']

    if request.method == 'POST':
        fare = request.form['fare']
        if request.form.get('closedStatus'):
            closedStatus = 0;
        else:
            closedStatus = 1;

        cur = connection.cursor()
        cur.execute("UPDATE Station "
                    "SET Fare = %s, ClosedStatus = %s "
                    "WHERE StopID = %s"
                    , (float(fare), closedStatus, id))
        connection.commit()
        cur.close()

        flash('Your station has updated.', 'success')
        return redirect(url_for('station_management'))

    return render_template('station_detail.html', form=form, station=station)

@app.route('/assign-owner', methods=["POST"])
def assign_owner():
    number = request.form['number']
    newOwner = request.form['newOwner']
    previousOwner = request.form['previousOwner']
    assignTo = request.form['assignTo']
    #assignTo == 1; assign to NEW owner
    cur = connection.cursor()
    if assignTo== 1:
        cur.execute("UPDATE Breezecard SET Owner = %s "
            "WHERE BreezecardNum = %s"
            , (number,newOwner))
        cur.execute("DELETE FROM Conflict WHERE BreezecardNum = %s"
            , number)
    else:
        cur.execute("UPDATE Breezecard SET Owner = %s "
            "WHERE BreezecardNum = %s"
            , (number,previousOwner))
        cur.execute("DELETE FROM Conflict WHERE BreezecardNum = %s"
            , number)
    connection.commit()
    cur.close()
    print(number + newOwner + previousOwner + assignTo, file=sys.stderr)
    return render_template('suspended_cards.html', cards=cards)

@app.route('/suspended-cards', methods =['POST', 'GET'])
@is_logged_in
def suspended_cards():
    cur = connection.cursor()
    cur.execute("SELECT B.BreezecardNum, C.Username AS NewOwner, C.DateTime AS DateSuspended, B.Owner AS PreviousOwner "
                "FROM Breezecard AS B JOIN Conflict AS C ON B.BreezecardNum = C.BreezecardNum")
    cards = cur.fetchall()

    return render_template('suspended_cards.html', cards=cards)

class AdminCardManagementForm(Form):
    owner = StringField('')
    number = StringField('')
    value_lower = StringField('')
    value_upper = StringField('')
    show_suspended = BooleanField('')
    set_value = StringField('')
    transfer_to = StringField('')

@app.route('/set-value', methods=["POST"])
def set_value():
    number = request.form['number']
    setValueTo = request.form['setValueTo']

    cur = connection.cursor()
    try:
        setValueTo = float(setValueTo)
        cur.execute("UPDATE Breezecard SET Value = %s "
        "WHERE BreezecardNum = %s",
        (setValueTo, number))
    except:
        flash("Error. Value must be a number between 0 and 1000.")
    connection.commit()
    cursor.close()
    print(number + setValueTo, file=sys.stderr)
    return redirect(url_for('card_management_admin'))

@app.route('/transfer-owner', methods=["POST"])
def transfer_owner():
    number = request.form['number']
    transferTo = request.form['transferTo']
    cur = connection.cursor()
    try:
        cur.execute("UPDATE Breezecard Set Owner = %s "
                    "WHERE BreezecardNum = %s"
                    , (transferTo, number))
        cur.execute("DELETE FROM Conflict "
                    "WHERE BreezecardNum = %s"
                    , number)
    except:
        flash("Error. Invalid Input")
    connection.commit()
    cursor.close()

    return redirect(url_for('card_management_admin'))


@app.route('/card-management-admin', methods = ['POST', 'GET'])
@is_logged_in
@is_admin
def card_management_admin():
    form = AdminCardManagementForm(request.form)
    cur = connection.cursor()
    cur.execute("SELECT * "
                "FROM Breezecard "
                "WHERE BreezecardNum NOT IN (SELECT BreezecardNum FROM Conflict)")
    allCards = cur.fetchall()

    if request.method == 'POST':
        if request.form['action'] == 'reset':
            form.owner.data = ''
            form.number.data = ''
            form.value_lower.data = ''
            form.value_upper.data = ''
            form.show_suspended.data = ''
            cur.execute("SELECT * "
                "FROM Breezecard "
                "WHERE BreezecardNum NOT IN (SELECT BreezecardNum FROM Conflict)")
            allCards = cur.fetchall()
        else:
            ownerName = request.form['owner']
            if len(ownerName) == 0:
                ownerName = "%"
            cardNumber = request.form['number']
            if len(cardNumber) == 0:
                cardNumber = "%"
            upperValue = request.form['value_lower']
            if len(upperValue) == 0:
                upperValue = 1000.00
            lowerValue = request.form['value_upper']
            if len(lowerValue) == 0:
                lowerValue = 0.00
            if request.form.get('show_suspended'):
                suspended = 1
            else:
                suspended = 0
            cur.execute("SELECT * "
                    "FROM Breezecard "
                    "WHERE BreezecardNum NOT IN (SELECT BreezecardNum FROM Conflict) "
                    "AND Owner LIKE %s AND BreezecardNum LIKE %s AND Value >= %s AND Value <= %s"
                    , ( ownerName, cardNumber, float(lowerValue), float(upperValue)))
            allCards = cur.fetchall()
            if ownerName == "%":
                cur.execute("SELECT * "
                    "FROM Breezecard "
                    "WHERE BreezecardNum NOT IN (SELECT BreezecardNum FROM Conflict) "
                    "AND Owner IS NULL AND BreezecardNum LIKE %s AND Value >= %s AND Value <= %s"
                    , ( cardNumber, float(lowerValue), float(upperValue)))
                noneCards = cur.fetchall()
                allCards.extend(noneCards)
            if suspended == 1:
                cur.execute("SELECT DISTINCT B.BreezecardNum, B.Value "
                            "FROM Breezecard AS B JOIN Conflict AS C "
                            "ON B.BreezecardNum = C.BreezecardNum WHERE Owner LIKE %s AND B.BreezecardNum LIKE %s AND Value >= %s AND Value <= %s"
                            , ( ownerName, cardNumber, float(lowerValue), float(upperValue)))
                suspendedCards = cur.fetchall()
                for card in suspendedCards:
                    card['Owner'] = 'Suspended'
                if len(suspendedCards) > 0:
                    allCards.extend(suspendedCards)
        flash('Filter has been updated.' + str(suspended) + " " + str(suspendedCards), 'success')
        cur.close()
        return render_template('card_management_admin.html', form=form, cards=allCards)

    return render_template('card_management_admin.html', form=form, cards=allCards)

class FlowReportForm(Form):
    start = StringField('')
    end = StringField('')

@app.route('/flow-report', methods = ['POST', 'GET'])
@is_logged_in
@is_admin
def flow_report():
    form = FlowReportForm(request.form)
    cur = connection.cursor()
    cur.execute("SELECT S.Name As Station, IFNULL(PIn.PassengersIn,0) AS InFlow, IFNULL(POut.PassengersOut,0) AS OutFlow, IFNULL(PIn.PassengersIN,0) - IFNULL(POut.PassengersOut,0) AS NetFlow, IFNULL(PIn.Revenue, 0) AS Revenue "
                "FROM (Station as S "
                "LEFT JOIN (SELECT DISTINCT StartsAt AS StartStation, COUNT(Fare) As PassengersIn, SUM(Fare) As Revenue "
                "FROM Trip GROUP BY StartsAt) AS PIn ON S.StopID = PIn.StartStation) "
                "LEFT JOIN (SELECT DISTINCT EndsAt AS EndStation, COUNT(Fare) As PassengersOut FROM Trip GROUP BY EndsAt) AS POut ON S.StopID = POut.EndStation "
                "WHERE PIn.PassengersIn >0 OR POut.PassengersOut >0")
    flowReport = cur.fetchall()
    if request.method == 'POST':
        if request.form['action'] == 'reset':
            form.start.data = ''
            form.end.data = ''
            cur.execute("SELECT S.Name As Station, IFNULL(PIn.PassengersIn,0) AS InFlow, IFNULL(POut.PassengersOut,0) as OutFlow, IFNULL(PIn.PassengersIN,0) - IFNULL(POut.PassengersOut,0) AS NetFlow, IFNULL(PIn.Revenue, 0) AS Revenue "
                        "FROM (Station as S LEFT JOIN (SELECT DISTINCT StartsAt AS StartStation, COUNT(Fare) As PassengersIn, SUM(Fare) As Revenue "
                        "FROM Trip GROUP BY StartsAt) AS PIn ON S.StopID = PIn.StartStation) LEFT JOIN (SELECT DISTINCT EndsAt AS EndStation, COUNT(Fare) As PassengersOut "
                        "FROM Trip GROUP BY EndsAt) AS POut ON S.StopID = POut.EndStation "
                        "WHERE PIn.PassengersIn >0 OR POut.PassengersOut >0")
            flowReport = cur.fetchall()
            cur.close()
            flash('Fliter has been reset', 'success')
        else:
            # try:
                startTime = request.form['start']
                endTime = request.form['end']
                if len(startTime) == 0:
                    startTime = '1950-01-01 00:00:00'
                if len(endTime) == 0:
                    endTime = '2020-12-31 23:59:59'
                cur.execute("SELECT S.Name AS Station, IFNULL(PIn.PassengersIn,0) AS InFlow, IFNULL(POut.PassengersOut,0) as OutFlow, IFNULL(PIn.PassengersIN,0) - IFNULL(POut.PassengersOut,0) AS NetFlow, IFNULL(PIn.Revenue, 0) AS Revenue "
                        "FROM (Station as S LEFT JOIN (SELECT DISTINCT StartsAt AS StartStation, COUNT(Fare) As PassengersIn, SUM(Fare) As Revenue "
                        "FROM Trip wHERE StartTime BETWEEN %s AND %s GROUP BY StartsAt) AS PIn ON S.StopID = PIn.StartStation) LEFT JOIN (SELECT DISTINCT EndsAt AS EndStation, COUNT(Fare) As PassengersOut "
                        "FROM Trip GROUP BY EndsAt) AS POut ON S.StopID = POut.EndStation "
                        "WHERE PIn.PassengersIn >0 OR POut.PassengersOut > 0"
                        , (datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S'), datetime.datetime.strptime(endTime, '%Y-%m-%d %H:%M:%S')))
                flowReport = cur.fetchall()
                flash('Filter Updated', 'success')
                cur.close()
            # except:
            #     flash('Incorrect time format. Please put time as YYYY-MM-DD HH:MM:SS', 'danger')
        return render_template('flow_report.html', form=form, flowReport=flowReport)
    cur.close()
    return render_template('flow_report.html', form=form, flowReport=flowReport)

class PassengerCardManagementForm(Form):
    number = StringField('')
    creditCard = StringField('')
    value = StringField('', render_kw={"placeholder": "Enter CC #"})

    def validate_number(form, field):
        try:
            int(field.data)
        except:
            raise ValidationError('Breezecard Number must be an integer.')
        if len(str(field.data)) != 16:
            raise ValidationError('Breezecard Number must be 16 digits')

@app.route('/add-value-passenger', methods=['POST'])
def add_value_passenger():
    breezecard = request.form['breezecard']
    value = request.form['value']

    cur = connection.cursor()

    cur.execute("SELECT Value "
                "FROM Breezecard "
                "WHERE BreezecardNum = %s"
                , breezecard)
    card = cur.fetchone()
    existingValue = card['Value']

    cur.execute("UPDATE Breezecard "
                "SET Value = %s "
                "WHERE BreezecardNum = %s"
                , (float(existingValue) + float(value), breezecard))
    connection.commit()
    cur.close()

    if float(existingValue) + float(value) > 10000:
        newValue = str(9999.99)
    else:
        newValue = str(float(existingValue) + float(value))
    return json.dumps(newValue)

@app.route('/card-management-passenger', methods = ['POST', 'GET'])
@is_logged_in
@is_passenger
def card_management_passenger():
    form = PassengerCardManagementForm(request.form)
    cur = connection.cursor()
    cur.execute("SELECT BreezecardNum, Value "
                "FROM Breezecard "
                "WHERE Owner = %s AND BreezecardNum NOT IN (SELECT DISTINCT BreezecardNum FROM Conflict)"
                ,session['username'])
    cards = cur.fetchall()
    cur.close()

    if request.method == 'POST':
        if request.form['action'] == 'add-card' and form.validate():
            breezecardNum = request.form['number']

            cur = connection.cursor()
            try:
                cur.execute("INSERT INTO Breezecard "
                            "VALUES (%s, 0.00, %s)"
                            , (breezecardNum, session['username']))
                connection.commit()
                flash('Card added.', 'success')
                return redirect(url_for('card_management_passenger'))

            except pymysql.IntegrityError:
                cur.execute("SELECT * "
                            "FROM Breezecard "
                            "WHERE BreezecardNum = %s"
                            , breezecardNum)

                owner = cur.fetchone()

                if owner['Owner'] == None:
                    cur.execute("UPDATE Breezecard "
                                "SET Owner = %s "
                                "WHERE BreezecardNum = %s"
                                , (session['username'], breezecardNum))
                    connection.commit()
                    cur.close()
                    flash('Card added.', 'success')
                    return redirect(url_for('card_management_passenger'))

                else:
                    ts = time.time()
                    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                    cur.execute("INSERT INTO Conflict "
                                "VALUES (%s, %s, %s)"
                                , (session['username'], breezecardNum, timestamp))
                    result = cur.execute("SELECT * FROM Breezecard "
                                         "WHERE Owner = (SELECT Owner FROM Breezecard WHERE BreezecardNum = %s) "
                                         "AND BreezecardNum NOT IN (SELECT DISTINCT BreezecardNum FROM Conflict)"
                                         , breezecardNum)
                    connection.commit()

                    if result == 0:
                        #Make sure we check random number doesn't already exist
                        randomNumber = randint(0000000000000000, 9999999999999999)
                        cur.execute("SELECT Owner "
                                    "FROM Breezecard "
                                    "WHERE BreezecardNum = %s"
                                    , breezecardNum)
                        owner = cur.fetchone()
                        cur.execute("INSERT INTO Breezecard Values (%s, 0.00, %s)"
                                    , (randomNumber, owner['Owner']))
                        connection.commit()
                        cur.close()


                    flash('Card is already taken.', 'danger')
                    return redirect(url_for('card_management_passenger'))
            cur.close()

        elif request.form['action'] == 'add-value':
            value = request.form['value']
            breezecard = request.data

    return render_template('card_management_passenger.html', form=form, cards = cards)

class TripHistoryForm(Form):
    start =StringField('')
    end = StringField('')
@app.route('/trip-history', methods = ['POST', 'GET'])
@is_logged_in
def trip_history():
    form = TripHistoryForm(request.form)

    cur = connection.cursor()
    cur.execute("SELECT t.StartTime, s1.Name AS StartName, s2.Name AS EndName, t.Fare, t.BreezecardNum "
                "FROM Trip as t LEFT JOIN Breezecard as b ON t.BreezecardNum = b.BreezecardNum "
                "JOIN Station as s1 ON s1.StopID = t.StartsAt "
                "JOIN Station as s2 ON s2.StopID = t.EndsAt "
                "WHERE b.Owner = %s"
                , (session['username']))
    trips = cur.fetchall()
    if request.method == 'POST':
        if request.form['action'] == 'reset':
            form.start.data = ''
            form.end.data = ''
            cur.execute("SELECT t.StartTime, s1.Name AS StartName, s2.Name AS EndName, t.Fare, t.BreezecardNum "
                "FROM Trip as t LEFT JOIN Breezecard as b ON t.BreezecardNum = b.BreezecardNum "
                "JOIN Station as s1 ON s1.StopID = t.StartsAt "
                "JOIN Station as s2 ON s2.StopID = t.EndsAt "
                "WHERE b.Owner = %s"
                , (session['username']))
            trips = cur.fetchall()
            flash('Filter reset', 'success')
        else:
            try:
                startTime = request.form['start']
                endTime = request.form['end']
                if len(startTime) == 0:
                    startTime = '1950-01-01 00:00:00'
                if len(endTime) == 0:
                    endTime = '2020-12-31 23:59:59'
                cur.execute("SELECT t.StartTime, s1.Name AS StartName, s2.Name AS EndName, t.Fare, t.BreezecardNum "
                            "FROM Trip as t LEFT JOIN Breezecard as b ON t.BreezecardNum = b.BreezecardNum "
                            "JOIN Station as s1 ON s1.StopID = t.StartsAt "
                            "JOIN Station as s2 ON s2.StopID = t.EndsAt "
                            "WHERE b.Owner = %s AND t.StartTime BETWEEN %s AND %s"
                            , (session['username'], datetime.datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S'), datetime.datetime.strptime(endTime, '%Y-%m-%d %H:%M:%S')))
                trips = cur.fetchall()
                cur.close()
            except:
                flash('Incorrect time format. Please put time as YYYY-MM-DD HH:MM:SS', 'danger')
            flash('Filter Updated', 'success')
        return render_template('trip_history.html', form=form, trips=trips)

    cur.close()
    return render_template('trip_history.html', form=form, trips=trips)

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404

if __name__ == '__main__':
    app.secret_key='supersecretkey'
    app.run(debug=True)
