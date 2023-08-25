from flask import render_template, url_for, session, redirect, request, flash
from jobwarden.app import app
from jobwarden.database import Database, Rank
from passlib.hash import bcrypt
from email.utils import parseaddr

db = Database()


def recheck_login(session):
    print(f"Recheck: user {session.get('current_user')}")
    if session.get("current_user") is None:
        print("Redirect")
        return redirect(url_for("login"))


@app.route("/")
def index():
    # make sure the user is logged in
    if session.get("current_user") is None:
        return redirect(url_for("login"))

    session["is_admin"] = db.check_is_admin(session.get("current_user"))

    print(session.get("current_user"))
    username = db.get_username(session.get("current_user"))[0]
    return render_template(
        "index.html", username=username, is_admin=session["is_admin"]
    )


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        username = request.form.get("username")
        pwd = request.form.get("password")

        user_id, pwd_hash = db.get_password(username)
        if user_id is None:
            flash(
                "There was a problem logging in. Please check username and password is correct."
            )
            return render_template("login.html")

        if bcrypt.verify(pwd, pwd_hash):
            session["current_user"] = user_id
            session["username"] = username
            db.create_login(user_id)

        return redirect(url_for("index"))


@app.route("/logout", methods=["GET"])
def logout():
    session["current_user"] = None
    session["username"] = None
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        pwd_hash = bcrypt.hash(password)

        # check access token
        access_token = request.form.get("access_token")
        if access_token != app.config["ACCESS_TOKEN"]:
            flash("Incorrect access token", "error")
            return render_template("register.html")

        # check email
        e = parseaddr(email)[1]
        if not e == email:
            print(e)
            flash("Invalid email", "error")
            return render_template("register.html")

        success = db.create_applicant(username, email, pwd_hash)

        if success:
            flash(
                "Your application has been submitted. Please wait for an admin to approve it."
            )
            return redirect(url_for("login"))
        else:
            flash("An error occurred creating your application")
            render_template("register.html")


@app.route("/admin", methods=["GET"])
def admin():
    recheck_login(session)
    logins = db.get_logins()
    return render_template("admin.html", logins=logins)


@app.route("/employees", methods=["GET", "POST"])
def employee_page():
    recheck_login(session)
    if session.get("current_user") is None or not session.get("is_admin", False):
        return redirect(url_for("index"))

    applicants = db.get_applications()
    users = db.get_all_users()
    logins = db.get_logins()

    if request.method == "POST":
        print(request.form.get(""))
        if request.form.get("Approve"):
            db.approve_applicant(
                username=request.form["username"], email=request.form["email"]
            )
            return redirect(url_for("employee_page"))

        elif request.form.get("Reject"):
            db.reject_applicant(
                username=request.form.get("username"), email=request.form.get("email")
            )
            return redirect(url_for("employee_page"))

    return render_template(
        "employees.html",
        applicants=applicants,
        users=users,
        logins=logins,
        ranks=Rank.__members__,
    )


@app.route("/change-employees", methods=["POST"])
def change_employees():
    # TODO for security, prompt to re-login when changing users
    recheck_login(session)

    # [('rank-names', 'current_rank'), ('rank-names', 'ADMIN'), ('rank-names', 'current_rank')])
    # get all users in order of ID
    users = db.get_all_users()
    # get which rank in form is not `current_rank`
    # this process was very tedious to figure out
    for i, r in enumerate(request.form.getlist("rank-names")):
        print("new_rank:", r)
        if r != "current_rank":
            new_rank = r
            userid = i + 1
            db.change_rank(userid, new_rank)
    # redirect back to employees page
    return redirect(url_for("employee_page"))


@app.route("/jobs", methods=["GET", "POST"])
def jobs():
    recheck_login(session)
    # jobs = db.get_all_jobs()
    customers = db.get_customer_names()
    return render_template("jobs.html", customers=customers)


@app.route("/customers", methods=["GET", "POST"])
def customers():
    recheck_login(session)
    customers = db.get_customer_names()
    return render_template("customers.html")
