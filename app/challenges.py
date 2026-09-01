from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from . import db
from .models import Challenge, Solve, User


challenges = Blueprint(
    "challenges",
    __name__,
    url_prefix="/challenges"
)


@challenges.route("/")
@login_required
def list_challenges():

    challenge_list = (
        Challenge.query
        .filter_by(visible=True)
        .order_by(
            Challenge.category,
            Challenge.base_points
        )
        .all()
    )

    solved_ids = {
        solve.challenge_id
        for solve in current_user.solves
    }

    team_solved_ids = set()

    if current_user.team_id is not None:

        team_solves = (
            Solve.query
            .join(
                User,
                Solve.user_id == User.id
            )
            .filter(
                User.team_id == current_user.team_id
            )
            .all()
        )

        team_solved_ids = {
            solve.challenge_id
            for solve in team_solves
        }

    return render_template(
        "challenges.html",
        challenges=challenge_list,
        solved_ids=solved_ids,
        team_solved_ids=team_solved_ids
    )


@challenges.route(
    "/<int:challenge_id>",
    methods=["GET", "POST"]
)
@login_required
def challenge(challenge_id):

    challenge = db.get_or_404(
        Challenge,
        challenge_id
    )

    if (
        not challenge.visible
        and not current_user.is_admin
    ):
        return "Challenge not here yet", 404

    already_solved = Solve.query.filter_by(
        user_id=current_user.id,
        challenge_id=challenge.id
    ).first() is not None

    team_solved = False

    if current_user.team_id is not None:

        team_solved = (
            Solve.query
            .join(
                User,
                Solve.user_id == User.id
            )
            .filter(
                Solve.challenge_id == challenge.id,
                User.team_id == current_user.team_id
            )
            .first()
            is not None
        )

    if request.method == "POST":


        if current_user.team is None:

            flash(
                "You must join or create a team before "
                "submitting flags."
            )

            return redirect(
                url_for("teams.index")
            )


        if already_solved:

            flash(
                "You already solved this challenge."
            )

            return redirect(
                url_for(
                    "challenges.challenge",
                    challenge_id=challenge.id
                )
            )


        if team_solved:

            flash(
                "Your team has already solved this challenge."
            )

            return redirect(
                url_for(
                    "challenges.challenge",
                    challenge_id=challenge.id
                )
            )

        submitted_flag = request.form.get(
            "flag",
            ""
        ).strip()

        if not submitted_flag:

            flash("Enter a flag.")

            return redirect(
                url_for(
                    "challenges.challenge",
                    challenge_id=challenge.id
                )
            )


        if not challenge.check_flag(
            submitted_flag
        ):

            flash(
                "Wrong flag, try again."
            )

            return redirect(
                url_for(
                    "challenges.challenge",
                    challenge_id=challenge.id
                )
            )


        solve = Solve(
            user_id=current_user.id,
            challenge_id=challenge.id
        )

        db.session.add(solve)

        try:

            db.session.commit()

        except IntegrityError:

            db.session.rollback()

            flash(
                "This challenge has already been solved."
            )

            return redirect(
                url_for(
                    "challenges.challenge",
                    challenge_id=challenge.id
                )
            )


        recalculate_scores()

        flash(
            f"Correct flag! "
            f"The challenge is currently worth "
            f"{challenge.points} points."
        )

        return redirect(
            url_for(
                "challenges.challenge",
                challenge_id=challenge.id
            )
        )

    return render_template(
        "challenge.html",
        challenge=challenge,
        already_solved=already_solved,
        team_solved=team_solved
    )


def recalculate_scores():

    """
    Recalculate every user's and team's score
    from the current challenge values.

    This means point decay automatically affects
    old solves.
    """

    users = User.query.all()

    for user in users:
        user.score = 0

    for user in users:

        solved_challenges = set()

        for solve in user.solves:
            solved_challenges.add(
                solve.challenge_id
            )

        user.score = sum(
            solve.challenge.points
            for solve in user.solves
        )

    from .models import Team

    teams = Team.query.all()

    for team in teams:
        team.score = 0

    for team in teams:

        solved_challenges = set()

        for user in team.users:

            for solve in user.solves:

                solved_challenges.add(
                    solve.challenge_id
                )

        team.score = sum(
            Challenge.query.get(challenge_id).points
            for challenge_id in solved_challenges
        )

    db.session.commit()

