from flask import Flask, request, render_template, url_for, logging, session, flash, redirect
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from functools import wraps

app = Flask(__name__)

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'marta_app'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#initialize MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

class RegisterForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()

        flash('Congratulations! You are now registered.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_attempt = request.form['password']

        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_attempt, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in.', 'success')
                return redirect(url_for('dashboard'))

            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            cur.close()

        else:
            error = "Username not found"
            return render_template('login.html', error=error)

    render_template('login.html')

# TODO: Figure out how this works more
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash ('Unauthorized, please login.', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

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

@app.route('/admin/station-detail/<string:id>/')
def station_detail(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM stations WHERE id = %s", [id])
    station = result.fetchone()

    return render_template('station_detail.html', id=station)

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

if __name__ == '__main__':
    app.run(debug=True)

    KEVIN IS A MAJOR LOSER