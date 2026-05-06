from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import Task, Order
from extensions import db, log_action
from datetime import datetime

chef_bp = Blueprint("chef", __name__)


def chef_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "chef":
            flash("Access denied.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@chef_bp.route("/dashboard")
@login_required
@chef_required
def dashboard():
    tasks = (Task.query.filter_by(chef_id=current_user.id)
             .order_by(Task.updated_at.desc()).all())
    not_started = [t for t in tasks if t.status == "Not Started"]
    in_progress = [t for t in tasks if t.status == "In Progress"]
    ready = [t for t in tasks if t.status == "Ready"]
    return render_template("chef/dashboard.html",
                           tasks=tasks, not_started=not_started,
                           in_progress=in_progress, ready=ready)


# Don't downgrade order past these terminal/forward states
DOWNSTREAM_STATES = {"Packed", "Approved", "Rejected", "Completed"}


@chef_bp.route("/task/<int:task_id>/update", methods=["POST"])
@login_required
@chef_required
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        flash("Task not found.", "danger")
        return redirect(url_for("chef.dashboard"))
    if task.chef_id != current_user.id:
        flash("Not your task.", "danger")
        return redirect(url_for("chef.dashboard"))
    new_status = request.form.get("status")
    valid_transitions = {
        "Not Started": ["In Progress"],
        "In Progress": ["Ready"],
        "Ready": [],
    }
    if new_status not in valid_transitions.get(task.status, []):
        flash("Invalid status transition.", "warning")
        return redirect(url_for("chef.dashboard"))

    task.status = new_status
    task.updated_at = datetime.utcnow()
    db.session.flush()

    order = db.session.get(Order, task.order_id)
    if order and order.status not in DOWNSTREAM_STATES:
        all_tasks = Task.query.filter_by(order_id=task.order_id).all()
        all_ready = all(t.status == "Ready" for t in all_tasks)
        any_started = any(t.status in ("In Progress", "Ready") for t in all_tasks)
        if all_ready:
            order.status = "Ready for Packing"
        elif any_started:
            order.status = "In Progress"

    db.session.commit()
    log_action("task_status_update",
               f"task_id={task.id} order_id={task.order_id} -> {new_status}")
    flash(f"Task updated to '{new_status}'.", "success")
    return redirect(url_for("chef.dashboard"))
