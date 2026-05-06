from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # manager/chef/packer/quality
    name = db.Column(db.String(120), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Ingredient(db.Model):
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False)
    stock = db.Column(db.Float, default=0.0)
    min_stock = db.Column(db.Float, default=5.0)
    allergen = db.Column(db.String(60))  # e.g. "gluten", "dairy"


class Meal(db.Model):
    __tablename__ = "meals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    components = db.relationship("Component", backref="meal", lazy=True)


class Component(db.Model):
    __tablename__ = "components"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    instructions = db.Column(db.Text)
    prep_time = db.Column(db.Integer, default=15)
    ingredient_links = db.relationship("ComponentIngredient", backref="component",
                                       lazy=True, cascade="all, delete-orphan")


class ComponentIngredient(db.Model):
    """Junction: how much of an ingredient one unit of a component needs."""
    __tablename__ = "component_ingredients"
    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("components.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    ingredient = db.relationship("Ingredient")
    __table_args__ = (db.UniqueConstraint("component_id", "ingredient_id"),)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order_items = db.relationship("OrderItem", backref="order", lazy=True,
                                  cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    meal = db.relationship("Meal")


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    component_id = db.Column(db.Integer, db.ForeignKey("components.id"), nullable=False)
    chef_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True)
    status = db.Column(db.String(30), default="Not Started")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship("Order")
    component = db.relationship("Component")
    chef = db.relationship("User")


class PackingRecord(db.Model):
    __tablename__ = "packing_records"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, unique=True)
    packer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                          nullable=True)
    packed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default="Packed")
    order = db.relationship("Order")
    packer = db.relationship("User")


class QualityCheck(db.Model):
    __tablename__ = "quality_checks"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    inspector_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True)
    result = db.Column(db.String(20))
    notes = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship("Order")
    inspector = db.relationship("User")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
                        nullable=True)
    username = db.Column(db.String(80))   # snapshotted in case user is deleted
    action = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.Text)
