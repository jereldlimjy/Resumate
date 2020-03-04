import os
from cs50 import SQL
from flask import Flask, render_template, redirect, session, request, url_for, flash, send_file
from flask_session import Session
from tempfile import mkdtemp
from flask_bcrypt import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from io import BytesIO

from helpers import login_required, apology

# Configure application
app = Flask(__name__)
app.secret_key = 'wasdjsaidjsidjsdj'

# Create directory to save uploads

UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
upload_dir = os.path.join(app.config['UPLOAD_FOLDER'])
os.makedirs(upload_dir, exist_ok=True)

#uploads_dir = os.path.join(app.instance_path, 'uploads')
#os.makedirs(uploads_dir, exist_ok=True)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///resumate.db")

@app.route("/")
@login_required
def index():
    """Show main page with wall of resumes"""
    rows = db.execute("SELECT post, date, username, post_id, filename FROM posts JOIN users ON users.id = posts.id LEFT JOIN uploads ON uploads.id = posts.post_id ORDER BY date DESC")

    return render_template("index.html", rows=rows)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Check if username is empty
        if not username:
            return apology("do not leave your username field blank!", 403)

        # Check if password or password confirmation is empty
        elif not (password or confirmation):
            return apology("do not leave your password field blank!")

        # Check whether username already exists in user database
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        if len(rows) != 0:
            return apology("sorry, username is already taken", 403)

        # Insert new registration info into users database
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=generate_password_hash(password))
            flash("Registration success! Woohoo!")
            return render_template("login.html")

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Check whether username and password are filled
        if not (username or password):
            return apology("please ensure that all fields are filled", 403)

        # Query users database for the username entered
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Check whether username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("sorry, error logging in", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/post", methods=["GET", "POST"])
@login_required
def post():

    if request.method == "POST":

        post = request.form.get("post")

        f = request.files['file']
        filename = secure_filename(f.filename)

        if not post:
            return apology("sorry, something went wrong...", 403)

        db.execute("INSERT INTO posts (id, post, date) VALUES (:id, :post, datetime())", id=session["user_id"], post=post)

        if filename == '':
            return redirect("/")

        f.save(os.path.join(upload_dir, filename))

        row = db.execute("SELECT post_id FROM posts WHERE post = :post", post=post)

        db.execute("INSERT INTO uploads (filename, id) VALUES (:filename, :id)", filename=filename, id=row[0]["post_id"])

        return redirect("/")

@app.route("/comment", methods=["GET", "POST"])
@login_required
def comment():

    rows = db.execute("SELECT username, post, date, post_id, filename FROM posts JOIN users on posts.id = users.id LEFT JOIN uploads ON uploads.id = posts.post_id WHERE post_id = :post_id"
                      , post_id=request.values.get("post_id"))

    comments = db.execute("SELECT username, comment, date FROM comments JOIN users ON commenter_id = users.id WHERE comments.id = :post_id ORDER BY date DESC", post_id=request.values.get("post_id"))

    if request.method == "POST":

        comment = request.form.get("comment")
        post_id = request.form.get("post_id")

        db.execute("INSERT INTO comments (id, commenter_id, comment) VALUES (:id, :commenter_id, :comment)", id=post_id, commenter_id=session["user_id"], comment=comment)

        # Redirect to comment page
        return redirect(url_for('comment', post_id=post_id))

    if request.method == "GET":
        return render_template("comment.html", rows=rows, comments=comments)

@app.route("/profile")
@login_required
def profile():

    rows = db.execute("SELECT post, date, username, post_id, filename FROM posts JOIN users ON users.id = posts.id LEFT JOIN uploads ON uploads.id = posts.post_id WHERE users.id = :id ORDER BY date DESC", id=session["user_id"])

    return render_template("profile.html", rows=rows)

@app.route("/search", methods=["POST"])
@login_required
def search():

    search = request.form.get("search")

    rows = db.execute("SELECT post, date, username, post_id, filename FROM posts JOIN users ON users.id = posts.id LEFT JOIN uploads ON uploads.id = posts.post_id WHERE username = :username ORDER BY date DESC", username=search)

    if not rows:
        return apology("sorry, user not found!", 403)

    return render_template("profile.html", rows=rows)