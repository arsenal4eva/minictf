from flask import Blueprint,render_template,request,redirect,url_for,flash

from flask_login import login_user,logout_user,login_required,current_user

from . import db
from .models import User


auth = Blueprint(
    "auth",
    __name__
)


@auth.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("auth.register"))

        if len(username) < 3:
            flash("Username must be at least 3 characters.")
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash("Username already exists.")
            return redirect(url_for("auth.register"))

        user = User(
            username=username
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created! You can now log in.")

        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(
            username=username
        ).first()

        if user and user.check_password(password):

            login_user(user)

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("index"))
