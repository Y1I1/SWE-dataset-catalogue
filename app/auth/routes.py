from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterForm
from app.db import db
from app.extensions import limiter
from app.models import User, UserRole


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
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("catalogue.list_datasets"))

    form = LoginForm()
    if request.method == "POST" and form.validate():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email, is_active=True).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "error")
        else:
            login_user(user)
            flash("Signed in successfully.", "success")
            next_page = url_for("catalogue.list_datasets")
            return redirect(next_page)

    return render_template("auth/login.html", form=form, title="Sign in")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))
