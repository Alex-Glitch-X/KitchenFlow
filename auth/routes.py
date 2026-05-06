from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Please fill in all fields.", "danger")
            return render_template("auth/login.html")
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            log_action("login_failed", f"username={username}")
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")
        login_user(user)
        log_action("login_success", f"user={user.username} role={user.role}")
        return redirect(url_for("auth.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    log_action("logout")
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/auth/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        cur = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not current_user.check_password(cur):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "warning")
        elif new != confirm:
            flash("New passwords do not match.", "warning")
        else:
            current_user.set_password(new)
            from extensions import db
            db.session.commit()
            log_action("password_changed")
            flash("Password updated successfully.", "success")
            return redirect(url_for("auth.dashboard"))
    return render_template("auth/change_password.html")


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    role = current_user.role
    if role == "manager":
        return redirect(url_for("manager.dashboard"))
    elif role == "chef":
        return redirect(url_for("chef.dashboard"))
    elif role == "packer":
        return redirect(url_for("packer.dashboard"))
    elif role == "quality":
        return redirect(url_for("quality.dashboard"))
    return redirect(url_for("auth.login"))
