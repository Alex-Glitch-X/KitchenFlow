from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from models import Order, QualityCheck
from extensions import db, log_action

quality_bp = Blueprint("quality", __name__)


def quality_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "quality":
            flash("Access denied.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@quality_bp.route("/dashboard")
@login_required
@quality_required
def dashboard():
    orders = Order.query.filter_by(status="Packed").order_by(Order.delivery_date.asc()).all()
    return render_template("quality/dashboard.html", orders=orders)


@quality_bp.route("/order/<int:order_id>/inspect")
@login_required
@quality_required
def inspect(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.status != "Packed":
        flash("This order is not ready for inspection.", "warning")
        return redirect(url_for("quality.dashboard"))
    return render_template("quality/inspect.html", order=order)


@quality_bp.route("/order/<int:order_id>/submit", methods=["POST"])
@login_required
@quality_required
def submit_check(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("quality.dashboard"))
    decision = request.form.get("decision", "approve")
    notes = request.form.get("notes", "").strip()
    checks = ["packaging", "items", "labelling", "temperature", "contamination"]
    passed = all(request.form.get(c) for c in checks)

    result = "Approved" if (decision == "approve" and passed) else "Rejected"
    order.status = result

    qc = QualityCheck(order_id=order.id, inspector_id=current_user.id,
                      result=result, notes=notes)
    db.session.add(qc)
    db.session.commit()
    log_action("quality_decision",
               f"order_id={order.id} result={result} notes_len={len(notes)}")

    if result == "Approved":
        flash(f"Order #{order.id} approved for delivery! ✓", "success")
    else:
        flash(f"Order #{order.id} rejected — sent back to packer.", "danger")
    return redirect(url_for("quality.dashboard"))
