import sys

from app import create_app
from app.extensions import db
from app.models.user import User


def usage():
    print("Usage: python scripts/reset_password.py <email> <new_password>")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        usage()
        return 2

    email = argv[1]
    new_password = argv[2]

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User not found: {email}")
            return 1
        user.set_password(new_password)
        db.session.commit()
        print(f"Password updated for {email}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
