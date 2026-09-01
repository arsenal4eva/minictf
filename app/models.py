from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager


class Team(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    # This is kept as a cached value for compatibility,
    # but the scoreboard recalculates it from solves.
    score = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    users = db.relationship(
        "User",
        back_populates="team",
        foreign_keys="User.team_id"
    )

    owner = db.relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="owned_team",
        post_update=True
    )


class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # Cached value. Scoreboard recalculates it.
    score = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=True
    )

    team = db.relationship(
        "Team",
        back_populates="users",
        foreign_keys=[team_id]
    )

    owned_team = db.relationship(
        "Team",
        foreign_keys="Team.owner_id",
        back_populates="owner",
        uselist=False
    )

    solves = db.relationship(
        "Solve",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Challenge(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    category = db.Column(
        db.String(50),
        nullable=False
    )

    # Original challenge value.
    base_points = db.Column(
        db.Integer,
        nullable=False
    )

    flag_hash = db.Column(
        db.String(255),
        nullable=False
    )

    visible = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    solves = db.relationship(
        "Solve",
        back_populates="challenge",
        cascade="all, delete-orphan"
    )

    hints = db.relationship(
        "Hint",
        back_populates="challenge",
        cascade="all, delete-orphan"
    )

    @property
    def points(self):
        """
        Current challenge value.

        P(n) = P0 / (n + 1)^k

        n = number of unique teams that solved it
        k = global decay exponent
        """

        team_ids = {
            solve.user.team_id
            for solve in self.solves
            if solve.user.team_id is not None
        }

        n = len(team_ids)

        settings = CTFSettings.query.first()

        if settings is None:
            decay_exponent = 0.5
        else:
            decay_exponent = settings.decay_exponent

        current_points = (
            self.base_points /
            ((n + 1) ** decay_exponent)
        )

        return max(
            1,
            round(current_points)
        )

    def set_flag(self, flag):
        self.flag_hash = generate_password_hash(flag)

    def check_flag(self, flag):
        return check_password_and_hash(
            flag,
            self.flag_hash
        )


class Solve(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("challenge.id"),
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User",
        back_populates="solves"
    )

    challenge = db.relationship(
        "Challenge",
        back_populates="solves"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "challenge_id",
            name="unique_user_challenge"
        ),
    )


class Hint(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("challenge.id"),
        nullable=False
    )

    text = db.Column(
        db.Text,
        nullable=False
    )

    cost = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    challenge = db.relationship(
        "Challenge",
        back_populates="hints"
    )


class JoinRequest(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    team_id = db.Column(
        db.Integer,
        db.ForeignKey("team.id"),
        nullable=False
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = db.relationship(
        "User"
    )

    team = db.relationship(
        "Team"
    )


class CTFSettings(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    decay_exponent = db.Column(
        db.Float,
        default=0.5,
        nullable=False
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(
        User,
        int(user_id)
    )


def check_password_and_hash(
    value,
    password_hash
):
    return check_password_hash(
        password_hash,
        value
    )

