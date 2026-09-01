from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from . import db
from .models import Challenge, Solve, CTFSettings


admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


@admin.before_request
def check_admin():

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    if not current_user.is_admin:
        return "Access denied", 403



@admin.route("/")
def dashboard():

    challenges = (
        Challenge.query
        .order_by(
            Challenge.category,
            Challenge.base_points
        )
        .all()
    )

    solve_count = Solve.query.count()

    settings = CTFSettings.query.first()

    if settings is None:
        settings = CTFSettings(
            decay_exponent=0.5
        )

        db.session.add(settings)
        db.session.commit()

    return render_template(
        "admin/dashboard.html",
        challenges=challenges,
        solve_count=solve_count,
        settings=settings
    )



@admin.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings():

    config = CTFSettings.query.first()

    if config is None:
        config = CTFSettings(
            decay_exponent=0.5
        )

        db.session.add(config)
        db.session.commit()

    if request.method == "POST":

        decay = request.form.get(
            "decay_exponent",
            ""
        ).strip()

        try:
            decay = float(decay)

        except ValueError:
            flash("Decay value must be a number.")
            return redirect(
                url_for("admin.settings")
            )

        # Prevent ridiculous values.
        if decay < 0.1 or decay > 2.0:

            flash(
                "Decay exponent must be between 0.1 and 2.0."
            )

            return redirect(
                url_for("admin.settings")
            )

        config.decay_exponent = decay

        db.session.commit()

        flash(
            f"Point decay updated to {decay:.2f}."
        )

        return redirect(
            url_for("admin.settings")
        )

    return render_template(
        "admin/settings.html",
        settings=config
    )



@admin.route(
    "/challenge/create",
    methods=["GET", "POST"]
)
def create_challenge():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        flag = request.form.get(
            "flag",
            ""
        ).strip()

        points = request.form.get(
            "points",
            ""
        ).strip()

        if not all([
            name,
            category,
            description,
            flag,
            points
        ]):

            flash(
                "Please fill in all fields."
            )

            return redirect(
                url_for("admin.create_challenge")
            )

        try:

            points = int(points)

            if points <= 0:
                raise ValueError

        except ValueError:

            flash(
                "Points must be a positive integer."
            )

            return redirect(
                url_for("admin.create_challenge")
            )

        challenge = Challenge(
            name=name,
            category=category,
            description=description,
            base_points=points,
            visible=True
        )

        challenge.set_flag(flag)

        db.session.add(challenge)
        db.session.commit()

        flash(
            "Challenge created!"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "admin/create_challenge.html"
    )



@admin.route(
    "/challenge/<int:challenge_id>/edit",
    methods=["GET", "POST"]
)
def edit_challenge(challenge_id):

    challenge = db.get_or_404(
        Challenge,
        challenge_id
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        points = request.form.get(
            "points",
            ""
        ).strip()

        new_flag = request.form.get(
            "flag",
            ""
        ).strip()

        visible = (
            request.form.get("visible") == "on"
        )

        if not name or not category or not description:

            flash(
                "Name, category and description are required."
            )

            return redirect(
                url_for(
                    "admin.edit_challenge",
                    challenge_id=challenge.id
                )
            )

        try:

            points = int(points)

            if points <= 0:
                raise ValueError

        except ValueError:

            flash(
                "Points must be a positive integer."
            )

            return redirect(
                url_for(
                    "admin.edit_challenge",
                    challenge_id=challenge.id
                )
            )

        challenge.name = name
        challenge.category = category
        challenge.description = description
        challenge.base_points = points
        challenge.visible = visible

        if new_flag:
            challenge.set_flag(new_flag)

        try:

            db.session.commit()

        except IntegrityError:

            db.session.rollback()

            flash(
                "Could not update the challenge."
            )

            return redirect(
                url_for(
                    "admin.edit_challenge",
                    challenge_id=challenge.id
                )
            )

        flash(
            "Challenge updated!"
        )

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "admin/edit_challenge.html",
        challenge=challenge
    )



@admin.route(
    "/challenge/<int:challenge_id>/delete",
    methods=["POST"]
)
def delete_challenge(challenge_id):

    challenge = db.get_or_404(
        Challenge,
        challenge_id
    )

    db.session.delete(challenge)
    db.session.commit()

    flash(
        "Challenge deleted."
    )

    return redirect(
        url_for("admin.dashboard")
    )



@admin.route("/solves")
def solves():

    solves = (
        Solve.query
        .order_by(
            Solve.timestamp.desc()
        )
        .all()
    )

    return render_template(
        "admin/solves.html",
        solves=solves
    )

