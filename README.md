# KitchenFlow

Kitchen management web app for managers, chefs, packers and quality supervisors.
Implements the requirements in *KitchenFlow System Requirements Specification* and
*KitchenFlow System Design Description*.

## Stack
Python 3.10+ · Flask 3 · Flask-Login · Flask-WTF (CSRF) · SQLAlchemy · SQLite

## Run

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

The first run creates `instance/kitchenflow.db` and seeds demo data automatically.
**If you upgraded from v5, delete `instance/kitchenflow.db` once** so the new tables
(`component_ingredients`, `audit_logs`) and the `allergen` column get created.

## Demo accounts (password: `password123`)
| Role | Username |
|---|---|
| Manager | `HELIOS` |
| Chef | `AURELIO`, `SOLARA` |
| Packer | `ORION` |
| Quality | `VESPER` |

## What's new in v6
See `CHANGELOG.md`.
