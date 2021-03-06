from flask import Flask, render_template, request, session, redirect
from mysqlconnection import MySQLConnector
import os, md5, binascii, datetime, re

app = Flask(__name__)
app.secret_key = ":)"
mysql = MySQLConnector(app, "walldb")

def setup_session():
	if not "username" in session:
		session["username"] = None

	if not "password_hash" in session:
		session["password_hash"] = None

def get_message_list():
	select_query = "SELECT messages.message_text, messages.id AS message_id, messages.updated_at AS time, users.username "
	select_query += "FROM messages JOIN users ON messages.user_id = users.id "
	select_query += "ORDER BY messages.id DESC"

	return mysql.query_db(select_query)

@app.route("/")
def index():
	setup_session()

	return render_template("index.html", message_list=get_message_list())

def get_current_user_id():
	select_query = "SELECT id FROM users WHERE username = :username AND password_hash = :password_hash"
	select_data = {
		"username": session["username"],
		"password_hash": session["password_hash"]
	}

	user_id = mysql.query_db(select_query, select_data)

	if len(user_id) == 1 and "id" in user_id[0]:
		return user_id[0]["id"]

	return -1

@app.route("/post/message", methods=["POST"])
def submit():
	user_id = get_current_user_id()

	if get_current_user_id() != -1:
		insert_query = "INSERT INTO messages (user_id, message_text, created_at, updated_at) "
		insert_query += "VALUES (:user_id, :message_text, :now, :now)"

		insert_data = {
			"user_id": user_id,
			"message_text": request.form["message"],
			"now": str(datetime.datetime.now())
		}

		mysql.query_db(insert_query, insert_data)
	else:
		return render_template("message.html", message="Something went wrong. (0)")

	return render_template("index.html", message_list=get_message_list())
	

################## LOG IN ##################

@app.route("/login")
def login():
	setup_session()

	if session["username"] == None:
		return render_template("login.html")

	return render_template("message.html", message="You are already logged in.")

@app.route("/login/process", methods=["POST"])
def process_login():
	select_query = "SELECT * FROM users WHERE username = :username"
	select_data = { "username": request.form["username"] }

	row_data = mysql.query_db(select_query, select_data)

	if len(row_data) > 0:
		password_hash = md5.new(request.form["password"] + row_data[0]["password_salt"]).hexdigest()

		if password_hash == row_data[0]["password_hash"]: # Successful login
			success = True

			setup_session()

			session["username"] = request.form["username"]
			session["password_hash"] = password_hash

			return redirect("/login/success")

	return render_template("login.html", message="Invalid log-in details.")

@app.route("/login/success")
def successful_login():
	return render_template("message.html", message="Successfully logged in.")

################## REGISTRATION ##################

@app.route("/register")
def register():
	if session["username"] == None:
		return render_template("register.html")

	return render_template("message.html", message="You are already logged in.")

def validate_registration(form):
	errors = []

	username_regex = r"^[a-zA-Z0-9][ A-Za-z0-9_-]*$"
	email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

	if len(form["username"]) < 3:
		errors += ["Username must be at least 3 characters long."]

	elif not re.match(username_regex, form["username"].rstrip()):
		errors += ["Username must contain only letters, numbers, hyphens, and underscores."]

	if len(form["email"]) == 0 or not re.match(email_regex, form["email"].rstrip()):
		errors += ["Invalid email address."]

	return errors


@app.route("/register/process", methods=["POST"])
def process_register():
	errors = validate_registration(request.form)

	if len(errors) > 0:
		return render_template("register.html", message="<br />".join(errors))

	select_query = "SELECT * FROM users WHERE username = :username OR email = :email"

	select_data = {
		"username": request.form["username"],
		"email": request.form["email"]
	}

	if len(mysql.query_db(select_query, select_data)) == 0: # Valid registration
		insert_query = "INSERT INTO users (username, password_hash, password_salt, email, created_at, updated_at) "
		insert_query += "VALUES (:username, :password_hash, :password_salt, :email, :now, :now)"

		password_salt = str(binascii.b2a_hex(os.urandom(15)))

		insert_data = {
			"username": request.form["username"],
			"password_hash": md5.new(request.form["password"] + password_salt).hexdigest(),
			"password_salt": password_salt,
			"email": request.form["email"],
			"now": str(datetime.datetime.now()) # because NOW() doesn't work for some reason
		}

		mysql.query_db(insert_query, insert_data)

		setup_session()

		session["username"] = request.form["username"]
		session["password_hash"] = insert_data["password_hash"]

		return redirect("/register/success")

	return render_template("register.html", message="Account with username or email already exists.")

@app.route("/register/success")
def successful_register():
	return render_template("message.html", message="Successfully registered.")

@app.route("/logout")
def logout():
	session["username"] = None

	return render_template("index.html")

app.run(debug=True)