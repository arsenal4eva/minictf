from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "j%5W@Ckf7RXcU6smNG7k$7wR$7&ciCD6"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///minictf.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    from .models import User
    from .auth import auth

    app.register_blueprint(auth)


    @app.route("/")
    def index():
        return render_template("index.html")



    @app.route("/dashboard")
    @login_required

    def dashboard():
        return render_template("dashboard.html")

    with app.app_context():
        db.create_all()

    return app
