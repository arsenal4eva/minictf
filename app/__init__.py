import os

from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required


db = SQLAlchemy()
login_manager = LoginManager()


def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = "j%5W@Ckf7RXcU6smNG7k$7wR$7&ciCD6"

    if os.environ.get("VERCEL"):
        database_path = "/tmp/minictf.db"
    else:
        database_path = "/home/arsenal4eva/Projects/minictf/minictf.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager.init_app(app)

    login_manager.login_view = "auth.login"


    from .models import (
        User,
        Team,
        Challenge,
        Solve,
        Hint
    )

    from .admin import admin
    from .models import User, Team, Challenge, Solve,Hint
    from .auth import auth
    from .challenges import challenges
    from .teams import teams
    from .scoreboard import scoreboard



    app.register_blueprint(auth)
    app.register_blueprint(challenges)
    app.register_blueprint(admin)
    app.register_blueprint(teams)
    app.register_blueprint(scoreboard)



    @app.route("/")
    def index():

        return render_template(
            "index.html"
        )


    @app.route("/dashboard")
    @login_required
    def dashboard():

        if current_user.is_admin:

            return redirect(
                url_for("admin.dashboard")
            )

        return render_template(
            "dashboard.html"
        )


    with app.app_context():

        db.create_all()


    return app
