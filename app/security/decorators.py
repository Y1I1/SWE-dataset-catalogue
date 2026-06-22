from functools import wraps

from flask import abort, redirect, url_for
from flask_login import current_user

from app.models.user import UserRole


def role_required(*roles: UserRole):

    allowed = {role if isinstance(role, UserRole) else UserRole(role) for role in roles}

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in allowed:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
