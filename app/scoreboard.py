from flask import Blueprint, render_template
from flask_login import login_required

from . import db
from .models import Team, User, Challenge


scoreboard = Blueprint(
    "scoreboard",
    __name__,
    url_prefix="/scoreboard"
)


def calculate_scores():

    users = User.query.all()


    for user in users:

        user.score = sum(
            solve.challenge.points
            for solve in user.solves
        )


    teams = Team.query.all()

    for team in teams:

        solved_challenges = {
            solve.challenge_id
            for user in team.users
            for solve in user.solves
        }

        team.score = sum(
            Challenge.query.get(challenge_id).points
            for challenge_id in solved_challenges
        )

    db.session.commit()


@scoreboard.route("/")
@login_required
def index():

    calculate_scores()

    teams = Team.query.all()

    entries = []

    for team in teams:

        solved_challenges = {
            solve.challenge_id
            for user in team.users
            for solve in user.solves
        }

        entries.append({
            "team": team,
            "score": team.score,
            "flag_count": len(solved_challenges)
        })

    entries.sort(
        key=lambda entry: (
            -entry["score"],
            entry["team"].name.lower()
        )
    )

    return render_template(
        "scoreboard.html",
        entries=entries
    )

