from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from functools import wraps
from collections import defaultdict
from models import (Order, OrderItem, Meal, Task, Ingredient, User,
                    Component, ComponentIngredient, PackingRecord,
                    QualityCheck, AuditLog)
from extensions import db, log_action
from datetime import date
import csv
import io

manager_bp = Blueprint("manager", __name__)


def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "manager":
            flash("Access denied.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _safe_int(s, default=1, lo=1, hi=100):
    try:
        v = int(s)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def compute_order_requirements(order):
    """Return list of {ingredient, required, available, shortfall}."""
    totals = defaultdict(float)
    for item in order.order_items:
        for comp in item.meal.components:
            for link in comp.ingredient_links:
                totals[link.ingredient_id] += link.quantity * item.quantity
    out = []
    for ing_id, qty in totals.items():
        ing = db.session.get(Ingredient, ing_id)
        if not ing:
            continue
        out.append({
            "ingredient": ing,
            "required": round(qty, 3),
            "available": ing.stock,
            "shortfall": round(max(0.0, qty - ing.stock), 3),
        })
    out.sort(key=lambda r: (-r["shortfall"], r["ingredient"].name))
    return out


def compute_global_purchase_list():
    """Aggregate requirements across all open (non-completed) orders."""
    open_statuses = {"Pending", "In Progress", "Ready for Packing"}
    totals = defaultdict(float)
    for order in Order.query.all():
        if order.status not in open_statuses:
            continue
        for item in order.order_items:
            for comp in item.meal.components:
                for link in comp.ingredient_links:
                    totals[link.ingredient_id] += link.quantity * item.quantity
    rows = []
    for ing in Ingredient.query.all():
        required = round(totals.get(ing.id, 0.0), 3)
        shortfall = round(max(0.0, required - ing.stock), 3)
        rows.append({
            "ingredient": ing,
            "required": required,
            "available": ing.stock,
            "shortfall": shortfall,
        })
    rows.sort(key=lambda r: (-r["shortfall"], r["ingredient"].name))
    return rows


@manager_bp.route("/dashboard")
@login_required
@manager_required
def dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    total_orders = len(orders)
    in_progress = sum(1 for o in orders if o.status == "In Progress")
    completed = sum(1 for o in orders if o.status in ("Approved", "Completed"))
    pending = sum(1 for o in orders if o.status == "Pending")
    low_stock = Ingredient.query.filter(Ingredient.stock < Ingredient.min_stock).all()
    return render_template("manager/dashboard.html",
                           orders=orders, total_orders=total_orders,
                           in_progress=in_progress, completed=completed,
                           pending=pending, low_stock=low_stock)


@manager_bp.route("/orders/new", methods=["GET", "POST"])
@login_required
@manager_required
def new_order():
    meals = Meal.query.all()
    chefs = User.query.filter_by(role="chef").all()
    if request.method == "POST":
        customer = request.form.get("customer_name", "").strip()
        delivery = request.form.get("delivery_date", "").strip()
        meal_ids = request.form.getlist("meal_ids")
        quantities = request.form.getlist("quantities")
        if not customer or not delivery or not meal_ids:
            flash("Please fill all required fields.", "danger")
            return render_template("manager/new_order.html", meals=meals, chefs=chefs)
        try:
            delivery_d = date.fromisoformat(delivery)
        except ValueError:
            flash("Invalid delivery date.", "danger")
            return render_template("manager/new_order.html", meals=meals, chefs=chefs)

        order = Order(customer_name=customer, delivery_date=delivery_d, status="In Progress")
        db.session.add(order)
        db.session.flush()

        # quantities[] is positional with meals rendered in form, but only checked
        # meal_ids POST. Build a map by meal_id from the parallel hidden quantity input.
        # Form sends `qty_<meal_id>` for safety (template updated accordingly).
        for mid in meal_ids:
            mid_int = int(mid)
            qty = _safe_int(request.form.get(f"qty_{mid}"), default=1, lo=1, hi=100)
            meal = db.session.get(Meal, mid_int)
            if not meal:
                continue
            db.session.add(OrderItem(order_id=order.id, meal_id=mid_int, quantity=qty))
            for comp in meal.components:
                # Per-(order, meal, component) chef key avoids collisions
                key = f"chef_{mid}_{comp.id}"
                chef_id = request.form.get(key)
                t = Task(order_id=order.id, component_id=comp.id,
                         chef_id=int(chef_id) if chef_id else None,
                         status="Not Started")
                db.session.add(t)
        db.session.commit()
        log_action("order_created", f"order_id={order.id} customer={customer}")
        flash(f"Order for {customer} created successfully!", "success")
        return redirect(url_for("manager.order_detail", order_id=order.id))
    return render_template("manager/new_order.html", meals=meals, chefs=chefs)


@manager_bp.route("/orders/<int:order_id>")
@login_required
@manager_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("manager.dashboard"))
    tasks = Task.query.filter_by(order_id=order_id).all()
    requirements = compute_order_requirements(order)
    return render_template("manager/order_detail.html",
                           order=order, tasks=tasks, requirements=requirements)


@manager_bp.route("/inventory")
@login_required
@manager_required
def inventory():
    ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return render_template("manager/inventory.html", ingredients=ingredients)


@manager_bp.route("/inventory/update/<int:ingr_id>", methods=["POST"])
@login_required
@manager_required
def update_stock(ingr_id):
    ingr = db.session.get(Ingredient, ingr_id)
    if not ingr:
        flash("Ingredient not found.", "danger")
        return redirect(url_for("manager.inventory"))
    new_stock = request.form.get("stock", type=float)
    if new_stock is not None and new_stock >= 0:
        old = ingr.stock
        ingr.stock = new_stock
        db.session.commit()
        log_action("inventory_update",
                   f"ingredient={ingr.name} old={old} new={new_stock}")
        flash(f"Stock updated for {ingr.name}.", "success")
    return redirect(url_for("manager.inventory"))


@manager_bp.route("/purchase-list")
@login_required
@manager_required
def purchase_list():
    rows = compute_global_purchase_list()
    shortfall_rows = [r for r in rows if r["shortfall"] > 0]
    return render_template("manager/purchase_list.html",
                           rows=rows, shortfall_rows=shortfall_rows)


@manager_bp.route("/purchase-list/download")
@login_required
@manager_required
def download_purchase_list():
    rows = compute_global_purchase_list()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Ingredient", "Unit", "Required", "Available", "Shortfall"])
    for r in rows:
        w.writerow([r["ingredient"].name, r["ingredient"].unit,
                    r["required"], r["available"], r["shortfall"]])
    out.seek(0)
    return Response(out, mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment;filename=purchase_list.csv"})


@manager_bp.route("/users")
@login_required
@manager_required
def users():
    all_users = User.query.all()
    return render_template("manager/users.html", users=all_users)


@manager_bp.route("/users/delete/<int:uid>", methods=["POST"])
@login_required
@manager_required
def delete_user(uid):
    u = db.session.get(User, uid)
    if not u:
        flash("User not found.", "danger")
        return redirect(url_for("manager.users"))
    if u.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("manager.users"))
    if u.role == "chef":
        active = Task.query.filter(Task.chef_id == u.id,
                                   Task.status != "Ready").count()
        if active:
            flash(f"Cannot delete {u.username}: {active} active task(s) assigned. "
                  f"Reassign or finish them first.", "warning")
            return redirect(url_for("manager.users"))
        # Null-out historical task assignments
        Task.query.filter_by(chef_id=u.id).update({Task.chef_id: None})
    db.session.delete(u)
    db.session.commit()
    log_action("user_deleted", f"username={u.username}")
    flash("User deleted.", "success")
    return redirect(url_for("manager.users"))


@manager_bp.route("/report")
@login_required
@manager_required
def report():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("manager/report.html", orders=orders)


@manager_bp.route("/report/download")
@login_required
@manager_required
def download_report():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Customer", "Delivery Date", "Status", "Created At"])
    for o in orders:
        writer.writerow([o.id, o.customer_name, o.delivery_date, o.status,
                         o.created_at.strftime("%Y-%m-%d %H:%M")])
    output.seek(0)
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition":
                             "attachment;filename=kitchenflow_report.csv"})


@manager_bp.route("/audit")
@login_required
@manager_required
def audit():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(500).all()
    return render_template("manager/audit.html", logs=logs)
