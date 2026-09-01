from app import create_app, db
from app.models import User


app = create_app()


username = input("Username to make admin: ").strip()


with app.app_context():

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        print("User not found.")
    else:

        user.is_admin = True

        db.session.commit()

        print(
            f"{username} is now an administrator."
        )
