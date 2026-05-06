from extensions import db
from models import (User, Ingredient, Meal, Component, ComponentIngredient,
                    Order, OrderItem, Task)
from datetime import date, timedelta


def seed_data():
    if User.query.first():
        return

    # Users
    users = [
        User(username="HELIOS",  role="manager", name="HELIOS"),
        User(username="AURELIO", role="chef",    name="AURELIO"),
        User(username="SOLARA",  role="chef",    name="SOLARA"),
        User(username="ORION",   role="packer",  name="ORION"),
        User(username="VESPER",  role="quality", name="VESPER"),
    ]
    for u in users:
        u.set_password("password123")
    db.session.add_all(users)
    db.session.flush()

    # Ingredients (with allergen tags)
    ing_defs = [
        ("Chicken Breast", "kg", 20.0, 5.0, None),
        ("Rice",           "kg", 15.0, 3.0, None),
        ("Tomato",         "kg", 8.0,  2.0, None),
        ("Mixed Greens",   "kg", 3.0,  4.0, None),
        ("Olive Oil",      "L",  5.0,  1.0, None),
        ("Pasta",          "kg", 10.0, 2.0, "gluten"),
        ("Garlic",         "kg", 2.0,  0.5, None),
        ("Basil",          "kg", 0.5,  0.2, None),
        ("Lemon",          "kg", 1.5,  0.5, None),
        ("Salt",           "kg", 5.0,  1.0, None),
    ]
    ingredients = {}
    for name, unit, stock, min_s, allergen in ing_defs:
        ing = Ingredient(name=name, unit=unit, stock=stock, min_stock=min_s, allergen=allergen)
        db.session.add(ing)
        ingredients[name] = ing
    db.session.flush()

    # Meals
    meal1 = Meal(name="Grilled Chicken Bowl",
                 description="Grilled chicken with rice and greens")
    meal2 = Meal(name="Pasta Pomodoro",
                 description="Classic tomato pasta")
    db.session.add_all([meal1, meal2])
    db.session.flush()

    comp_defs = [
        ("Grilled Chicken", meal1.id, "Season and grill chicken breast for 12 min.", 20,
         [("Chicken Breast", 0.20), ("Olive Oil", 0.01), ("Salt", 0.005)]),
        ("Steamed Rice",    meal1.id, "Steam 200g rice until fluffy.", 15,
         [("Rice", 0.20), ("Salt", 0.003)]),
        ("Fresh Salad",     meal1.id, "Toss greens with olive oil and lemon.", 5,
         [("Mixed Greens", 0.10), ("Olive Oil", 0.01), ("Lemon", 0.05)]),
        ("Boiled Pasta",    meal2.id, "Boil pasta al dente, drain well.", 12,
         [("Pasta", 0.15), ("Salt", 0.005), ("Olive Oil", 0.01)]),
        ("Pomodoro Sauce",  meal2.id, "Simmer sauce with garlic and basil.", 15,
         [("Tomato", 0.20), ("Garlic", 0.01), ("Basil", 0.005), ("Olive Oil", 0.01)]),
    ]
    components = []
    for name, mid, instr, pt, ings in comp_defs:
        c = Component(name=name, meal_id=mid, instructions=instr, prep_time=pt)
        db.session.add(c)
        db.session.flush()
        for ing_name, qty in ings:
            db.session.add(ComponentIngredient(
                component_id=c.id,
                ingredient_id=ingredients[ing_name].id,
                quantity=qty,
            ))
        components.append(c)

    chef1 = User.query.filter_by(username="AURELIO").first()
    chef2 = User.query.filter_by(username="SOLARA").first()

    order1 = Order(customer_name="Theron Vasari",
                   delivery_date=date.today() + timedelta(days=1),
                   status="In Progress")
    order2 = Order(customer_name="Iolanthe Marchetti",
                   delivery_date=date.today() + timedelta(days=2),
                   status="Pending")
    db.session.add_all([order1, order2])
    db.session.flush()

    db.session.add_all([
        OrderItem(order_id=order1.id, meal_id=meal1.id, quantity=2),
        OrderItem(order_id=order2.id, meal_id=meal2.id, quantity=1),
    ])

    c_ids = {c.name: c.id for c in components}
    db.session.add_all([
        Task(order_id=order1.id, component_id=c_ids["Grilled Chicken"], chef_id=chef1.id, status="In Progress"),
        Task(order_id=order1.id, component_id=c_ids["Steamed Rice"],    chef_id=chef1.id, status="Not Started"),
        Task(order_id=order1.id, component_id=c_ids["Fresh Salad"],     chef_id=chef2.id, status="Not Started"),
        Task(order_id=order2.id, component_id=c_ids["Boiled Pasta"],    chef_id=chef2.id, status="Not Started"),
        Task(order_id=order2.id, component_id=c_ids["Pomodoro Sauce"],  chef_id=chef1.id, status="Not Started"),
    ])

    db.session.commit()
    print("Sample data seeded.")
