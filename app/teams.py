from flask import Blueprint, render_template, request, redirect, url_for, flash

from flask_login import login_required, current_user

from . import db
from .models import Team, JoinRequest, User, Solve


teams = Blueprint(
    "teams",
    __name__,
    url_prefix="/teams"
)


MAX_TEAM_SIZE = 4


def recalculate_team_score(team):
    """
    Recalculate a team's score from the solves of its
    current members.

    Each challenge is only counted once per team.
    """

    solved_challenges = {}

    for user in team.users:

        for solve in user.solves:

            challenge_id = solve.challenge_id

            if challenge_id not in solved_challenges:
                solved_challenges[challenge_id] = solve.challenge.points

    team.score = sum(solved_challenges.values())

    return len(solved_challenges)


def get_team_flag_count(team):
    """
    Return the number of unique challenges solved
    by the team's current members.
    """

    challenge_ids = set()

    for user in team.users:
        for solve in user.solves:
            challenge_ids.add(solve.challenge_id)

    return len(challenge_ids)


@teams.route("/")
@login_required
def index():

    if current_user.team:
        return redirect(
            url_for(
                "teams.team",
                team_id=current_user.team_id
            )
        )

    teams_list = (
        Team.query
        .order_by(Team.name.asc())
        .all()
    )

    pending_request = (
        JoinRequest.query
        .filter_by(user_id=current_user.id)
        .first()
    )

    return render_template(
        "teams.html",
        teams=teams_list,
        pending_request=pending_request
    )


@teams.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if current_user.team:
        flash("You are already in a team.")
        return redirect(url_for("teams.index"))

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        if not name:
            flash("Team name is required.")
            return redirect(url_for("teams.create"))

        if len(name) < 3:
            flash("Team name must be at least 3 characters.")
            return redirect(url_for("teams.create"))

        if len(name) > 80:
            flash("Team name must be 80 characters or less.")
            return redirect(url_for("teams.create"))

        existing = Team.query.filter_by(
            name=name
        ).first()

        if existing:
            flash("Team already exists.")
            return redirect(url_for("teams.create"))

        team = Team(
            name=name,
            score=0,
            owner_id=current_user.id
        )

        db.session.add(team)

        db.session.flush()

        current_user.team_id = team.id

        db.session.commit()

        flash(
            f"Team '{name}' created. You are now the team leader."
        )

        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    return render_template("create_team.html")


@teams.route("/join/<int:team_id>", methods=["POST"])
@login_required
def request_join(team_id):

    # Absolutely prevent joining another team.
    if current_user.team is not None:
        flash("You are already in a team.")
        return redirect(url_for("teams.index"))

    team = db.get_or_404(
        Team,
        team_id
    )

    if len(team.users) >= MAX_TEAM_SIZE:
        flash("That team is full.")
        return redirect(url_for("teams.index"))

    # Prevent multiple pending requests.
    existing_request = JoinRequest.query.filter_by(
        user_id=current_user.id,
        team_id=team.id
    ).first()

    if existing_request:
        flash("You have already requested to join this team.")
        return redirect(url_for("teams.index"))

    other_request = JoinRequest.query.filter(
        JoinRequest.user_id == current_user.id,
        JoinRequest.team_id != team.id
    ).first()

    if other_request:
        flash("You already have a pending team request.")
        return redirect(url_for("teams.index"))

    join_request = JoinRequest(
        user_id=current_user.id,
        team_id=team.id
    )

    db.session.add(join_request)
    db.session.commit()

    flash(
        f"Join request sent to '{team.name}'."
    )

    return redirect(
        url_for("teams.index")
    )


@teams.route("/requests")
@login_required
def requests():

    if current_user.team is None:
        flash("You are not in a team.")
        return redirect(url_for("teams.index"))

    if current_user.team.owner_id != current_user.id:
        flash("Only the team leader can manage join requests.")
        return redirect(
            url_for(
                "teams.team",
                team_id=current_user.team_id
            )
        )

    join_requests = (
        JoinRequest.query
        .filter_by(team_id=current_user.team_id)
        .order_by(JoinRequest.timestamp.asc())
        .all()
    )

    return render_template(
        "team_requests.html",
        join_requests=join_requests,
        max_team_size=MAX_TEAM_SIZE
    )


@teams.route(
    "/requests/<int:request_id>/approve",
    methods=["POST"]
)
@login_required
def approve_request(request_id):

    join_request = db.get_or_404(
        JoinRequest,
        request_id
    )

    team = join_request.team

    if team.owner_id != current_user.id:
        flash("Only the team leader can approve requests.")
        return redirect(url_for("teams.index"))

    # Prevent a user from being added to two teams.
    if join_request.user.team is not None:

        db.session.delete(join_request)
        db.session.commit()

        flash("That user is already in a team.")
        return redirect(url_for("teams.requests"))

    if len(team.users) >= MAX_TEAM_SIZE:
        flash("Your team is already full.")
        return redirect(url_for("teams.requests"))

    join_request.user.team = team

    db.session.flush()

    # Their existing solves now count for this team.
    recalculate_team_score(team)

    db.session.delete(join_request)

    db.session.commit()

    flash(
        f"{join_request.user.username} joined the team."
    )

    return redirect(
        url_for("teams.requests")
    )


@teams.route(
    "/requests/<int:request_id>/reject",
    methods=["POST"]
)
@login_required
def reject_request(request_id):

    join_request = db.get_or_404(
        JoinRequest,
        request_id
    )

    if join_request.team.owner_id != current_user.id:
        flash("Only the team leader can reject requests.")
        return redirect(url_for("teams.index"))

    username = join_request.user.username

    db.session.delete(join_request)
    db.session.commit()

    flash(
        f"Join request from {username} rejected."
    )

    return redirect(
        url_for("teams.requests")
    )


@teams.route("/leave", methods=["POST"])
@login_required
def leave():

    if current_user.team is None:
        flash("You are not currently in a team.")
        return redirect(url_for("teams.index"))

    team = current_user.team

    if team.owner_id == current_user.id:
        flash(
            "Team leaders cannot leave their team. "
            "Transfer ownership first."
        )

        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    current_user.team = None

    db.session.flush()

    # The player's solves leave the team's score.
    recalculate_team_score(team)

    db.session.commit()

    flash(
        f"You left '{team.name}'."
    )

    return redirect(
        url_for("teams.index")
    )


@teams.route(
    "/<int:team_id>/kick/<int:user_id>",
    methods=["POST"]
)
@login_required
def kick(team_id, user_id):

    team = db.get_or_404(
        Team,
        team_id
    )

    if team.owner_id != current_user.id:
        flash("Only the team leader can kick members.")
        return redirect(url_for("teams.index"))

    if user_id == current_user.id:
        flash("You cannot kick yourself.")
        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    user = db.get_or_404(
        User,
        user_id
    )

    if user.team_id != team.id:
        flash("That user is not in your team.")
        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    username = user.username

    user.team = None

    db.session.flush()

    # Remove the player's solves from the team's totals.
    recalculate_team_score(team)

    db.session.commit()

    flash(
        f"{username} was removed from the team."
    )

    return redirect(
        url_for(
            "teams.team",
            team_id=team.id
        )
    )


@teams.route(
    "/<int:team_id>/transfer/<int:user_id>",
    methods=["POST"]
)
@login_required
def transfer_ownership(team_id, user_id):

    team = db.get_or_404(
        Team,
        team_id
    )

    if team.owner_id != current_user.id:
        flash("Only the team leader can transfer ownership.")
        return redirect(url_for("teams.index"))

    if user_id == current_user.id:
        flash("You already own this team.")
        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    new_owner = db.get_or_404(
        User,
        user_id
    )

    if new_owner.team_id != team.id:
        flash("That user is not a member of your team.")
        return redirect(
            url_for(
                "teams.team",
                team_id=team.id
            )
        )

    team.owner_id = new_owner.id

    db.session.commit()

    flash(
        f"{new_owner.username} is now the team leader."
    )

    return redirect(
        url_for(
            "teams.team",
            team_id=team.id
        )
    )


@teams.route(
    "/<int:team_id>/delete",
    methods=["POST"]
)
@login_required
def delete(team_id):

    team = db.get_or_404(
        Team,
        team_id
    )

    if team.owner_id != current_user.id:
        flash("Only the team leader can delete the team.")
        return redirect(url_for("teams.index"))

    # Remove membership first.
    for user in team.users:
        user.team = None

    # Delete pending join requests.
    JoinRequest.query.filter_by(
        team_id=team.id
    ).delete(
        synchronize_session=False
    )

    db.session.delete(team)

    db.session.commit()

    flash("Team deleted.")

    return redirect(
        url_for("teams.index")
    )


@teams.route("/<int:team_id>")
@login_required
def team(team_id):

    team = db.get_or_404(
        Team,
        team_id
    )

    # Keep the stored score synchronized.
    recalculate_team_score(team)
    db.session.commit()

    flag_count = get_team_flag_count(team)

    return render_template(
        "team.html",
        team=team,
        flag_count=flag_count,
        max_team_size=MAX_TEAM_SIZE
    )

