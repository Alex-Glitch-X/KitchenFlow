from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from collections import defaultdict
from models import Order, OrderItem, PackingRecord, Ingredient
from extensions import db, log_action

packer_bp = Blueprint("packer", __name__)


def packer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "packer":
            flash("Access denied.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@packer_bp.route("/dashboard")
@login_required
@packer_required
def dashboard():
    orders = (Order.query
              .filter(Order.status.in_(["Ready for Packing", "Rejected"]))
              .order_by(Order.delivery_date.asc())
              .all())
    return render_template("packer/dashboard.html", orders=orders)


@packer_bp.route("/order/<int:order_id>/instructions")
@login_required
@packer_required
def instructions(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.status not in ("Ready for Packing", "Rejected"):
        flash("This order is not ready for packing yet.", "warning")
        return redirect(url_for("packer.dashboard"))
    return render_template("packer/instructions.html", order=order)


def _build_label_data(item):
    """Aggregate ingredients + allergens across the meal's components."""
    ing_qty = defaultdict(float)
    allergens = set()
    for comp in item.meal.components:
        for link in comp.ingredient_links:
            ing_qty[link.ingredient.id] += link.quantity * item.quantity
            if link.ingredient.allergen:
                allergens.add(link.ingredient.allergen)
    rows = []
    for ing_id, qty in ing_qty.items():
        ing = db.session.get(Ingredient, ing_id)
        rows.append({"name": ing.name, "qty": round(qty, 3), "unit": ing.unit})
    rows.sort(key=lambda r: -r["qty"])
    return rows, sorted(allergens)


@packer_bp.route("/order/<int:order_id>/labels")
@login_required
@packer_required
def labels(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("packer.dashboard"))
    label_blocks = []
    for item in order.order_items:
        ings, allergens = _build_label_data(item)
        label_blocks.append({"item": item, "ingredients": ings, "allergens": allergens})
    return render_template("packer/labels.html", order=order, label_blocks=label_blocks)


@packer_bp.route("/order/<int:order_id>/confirm", methods=["POST"])
@login_required
@packer_required
def confirm_packing(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("packer.dashboard"))
    if order.status not in ("Ready for Packing", "Rejected"):
        flash("This order is not in a packable state.", "warning")
        return redirect(url_for("packer.dashboard"))
    # Idempotent: only one packing record per order
    existing = PackingRecord.query.filter_by(order_id=order.id).first()
    if not existing:
        db.session.add(PackingRecord(order_id=order.id, packer_id=current_user.id,
                                     status="Packed"))
    order.status = "Packed"
    db.session.commit()
    log_action("order_packed", f"order_id={order.id}")
    flash(f"Order #{order.id} marked as packed!", "success")
    return redirect(url_for("packer.dashboard"))
