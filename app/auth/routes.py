from datetime import datetime, timedelta, timezone

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterForm
from app.db import db
from app.models import LoginAttempt, User, UserRole

_MAX_ATTEMPTS = 10
_WINDOW = timedelta(minutes=1)


def _client_ip() -> str:
    return request.remote_addr or "unknown"


def _is_rate_limited() -> bool:
    cutoff = datetime.now(timezone.utc) - _WINDOW
    count = LoginAttempt.query.filter(
        LoginAttempt.ip_address == _client_ip(),
        LoginAttempt.attempted_at >= cutoff,
    ).count()
    return count >= _MAX_ATTEMPTS


def _record_failed_attempt() -> None:
    old_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    LoginAttempt.query.filter(LoginAttempt.attempted_at < old_cutoff).delete()
    db.session.add(LoginAttempt(ip_address=_client_ip()))
    db.session.commit()


def _clear_attempts() -> None:
    LoginAttempt.query.filter_by(ip_address=_client_ip()).delete()
    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("catalogue.list_datasets"))

    form = RegisterForm()
    if request.method == "POST" and form.validate():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(email=email, full_name=form.full_name.data.strip(), role=UserRole.viewer)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created.", "success")
            return redirect(url_for("catalogue.list_datasets"))

    return render_template("auth/register.html", form=form, title="Register")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("catalogue.list_datasets"))

    if request.method == "POST" and _is_rate_limited():
        flash("Too many login attempts. Please wait a minute and try again.", "error")
        return render_template("auth/login.html", form=LoginForm(), title="Sign in")

    form = LoginForm()
    if request.method == "POST" and form.validate():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email, is_active=True).first()
        if user is None or not user.check_password(form.password.data):
            _record_failed_attempt()
            flash("Invalid email or password.", "error")
        else:
            _clear_attempts()
            login_user(user)
            flash("Signed in successfully.", "success")
            return redirect(url_for("catalogue.list_datasets"))

    return render_template("auth/login.html", form=form, title="Sign in")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))
