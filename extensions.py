from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))


def log_action(action, detail=""):
    """Append an entry to the audit log. Safe to call without an active user."""
    from flask_login import current_user
    from models import AuditLog
    uid = getattr(current_user, "id", None) if getattr(current_user, "is_authenticated", False) else None
    uname = getattr(current_user, "username", "anonymous") if getattr(current_user, "is_authenticated", False) else "anonymous"
    db.session.add(AuditLog(user_id=uid, username=uname, action=action, detail=detail))
    db.session.commit()
