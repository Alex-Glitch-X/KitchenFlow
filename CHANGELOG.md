# KitchenFlow v6 — Changelog

## Bug fixes
1. **New-order chef assignment** now uses `chef_<meal_id>_<comp_id>` keys so the same component in different meals/orders no longer collides.
2. **Quantity input** uses per-meal keys `qty_<meal_id>` and is clamped to 1–100 server-side.
3. **Order status race**: chef status updates no longer downgrade an order that has progressed to `Packed`, `Approved`, `Rejected`, or `Completed`.
4. **Packer confirm idempotency**: duplicate POSTs no longer create duplicate `PackingRecord` rows (unique constraint + lookup).
5. **Rejected orders** are now visible to packers ("Rejected — Re-pack") so the workflow can recover instead of stranding the order.
6. **User deletion**: cannot delete a chef with active tasks; orphaned task assignments are nulled out (FK `ondelete=SET NULL`).
7. **Logout** is now POST + CSRF protected (was GET).
8. **CSRF protection** enabled site-wide via Flask-WTF (`csrf_token()` injected into every form).
9. **Themed 403 / 404 / 500** error pages instead of Flask's default white screen.
10. **Body overflow** restructured so the main content area always scrolls.
11. **SQLAlchemy 2.x** — replaced legacy `Model.query.get(id)` with `db.session.get(Model, id)`.
12. **Invalid date input** in new-order is rejected gracefully instead of raising.

## New features (closing SRS / Design-Doc gaps)
- **Ingredient requirement calculation** — new `component_ingredients` join table; per-order requirements shown on order detail page.
- **Global Purchase List page** — manager sees aggregate shortfalls across open orders, with CSV download.
- **Packing labels** — printable per-meal labels with ingredients, allergen tags, basic nutrition placeholder, and a print stylesheet.
- **Audit log** — every login (success + fail), inventory update, order/task/quality decision, and user deletion is recorded; manager-only viewer at `/manager/audit`.
- **Change password** page (`/auth/change-password`) with policy (≥8 chars).
- **Allergen tagging** on ingredients flows through to labels and order detail.

## Design polish
- Sidebar "Sign out" rendered as proper form-button (keyboard accessible, CSRF-safe).
- New navigation entries (Purchase List, Audit Log) for manager.
- Themed empty / error states.
- Print-friendly stylesheet for labels.

## Files changed / added
- Updated: `app.py`, `extensions.py`, `models.py`, `seed.py`, `requirements.txt`,
  `auth/routes.py`, `manager/routes.py`, `chef/routes.py`, `packer/routes.py`,
  `quality/routes.py`, all templates under `templates/`.
- Added: `templates/manager/purchase_list.html`, `templates/manager/audit.html`,
  `templates/auth/change_password.html`, `templates/packer/labels.html`,
  `templates/errors/error.html`.

## Notes
- The DB schema has new tables (`component_ingredients`, `audit_logs`) and new columns
  (`ingredients.allergen`). Delete the old `instance/kitchenflow.db` file once before
  first run so the seeder can repopulate fresh data.


## v7 — Identity & Palette
- Renamed all demo accounts to professional all-caps call-signs:
  HELIOS (Manager), AURELIO & SOLARA (Chefs), ORION (Packer), VESPER (Quality).
- Replaced common demo customer names with distinctive ones:
  Theron Vasari, Iolanthe Marchetti.
- New "Onyx & Saffron" palette: deep onyx surfaces (#0b0d10), saffron gold
  primary (#e6b54a), warm copper accent (#d97a3a), sage success (#6fbf8f).
  Light theme rebalanced to a warm parchment tone (#f6f3ec / #b07d11).
- Updated login hint and order placeholder copy to match new identity.
