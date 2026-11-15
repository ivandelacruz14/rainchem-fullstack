from app.extensions import db


class Setting(db.Model):
    """Small key/value store for things an admin can change without redeploying
    (for example the GCash number shown at checkout)."""

    __tablename__ = "settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text(length=4294967295), nullable=True)


def get_setting(key, default=""):
    row = db.session.get(Setting, key)
    if row is None or row.value is None:
        return default
    return row.value


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
