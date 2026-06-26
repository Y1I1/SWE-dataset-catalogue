import sys

from app import create_app
from app.extensions import db
from app.models.user import User


def usage():
    print("Usage:")
    print("  python scripts/reset_password.py <email> <new_password>")
    print("  python scripts/reset_password.py --all <new_password>")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        usage()
        return 2

    target = argv[1]
    new_password = argv[2]

    app = create_app()
    with app.app_context():
        if target == "--all":
            users = User.query.all()
            if not users:
                print("No users found.")
                return 1
            for user in users:
                user.set_password(new_password)
                print(f"Password updated for {user.email}")
            db.session.commit()
            print(f"Done — {len(users)} user(s) updated.")
            return 0

        user = User.query.filter_by(email=target).first()
        if not user:
            print(f"User not found: {target}")
            return 1
        user.set_password(new_password)
        db.session.commit()
        print(f"Password updated for {target}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
