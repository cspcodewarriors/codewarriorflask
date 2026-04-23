from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from __init__ import app, db


class Notification(db.Model):
    """
    Stores in-app notifications for users.

    Columns
    -------
    id          auto-incrementing primary key
    uid         _uid of the recipient user
    title       short notification heading
    body        optional longer description
    is_read     False until the user views/dismisses it
    created_at  UTC timestamp
    """

    __tablename__ = "notifications"

    id         = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    uid        = db.Column(db.String(128),  nullable=False, index=True)
    title      = db.Column(db.String(128),  nullable=False)
    body       = db.Column(db.Text,         nullable=True)
    is_read    = db.Column(db.Boolean,      nullable=False, default=False)
    created_at = db.Column(db.DateTime,     nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    def read(self):
        return {
            "id":         self.id,
            "uid":        self.uid,
            "title":      self.title,
            "body":       self.body,
            "is_read":    self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def __repr__(self):
        return (
            f"<Notification id={self.id} uid={self.uid!r} "
            f"read={self.is_read} title={self.title!r}>"
        )


def initNotifications():
    """Create the notifications table if it doesn't exist."""
    with app.app_context():
        db.create_all()
        print("notifications table ready.")
