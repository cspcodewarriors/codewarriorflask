"""
model/sip_contact.py

SQLAlchemy model for Soroptimist International of Poway contact-form
submissions.

Only stores what the forms actually collect:
  - form_type   'involved' | 'help'
  - selection   dropdown value
  - message     optional free text

uid is stamped from the JWT cookie at save time (same pattern as BlogPost),
so personal info is never duplicated — it lives on the User record.

Table: sip_contact_submissions
DB:    user_management.db
"""

from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from flask import request as flask_request, current_app
import jwt
import json

from __init__ import app, db


def _get_user_from_cookie():
    """
    Resolve the current user from the JWT cookie or Authorization header.
    Mirrors get_user_from_cookie() in model/blog.py exactly.
    Returns a User object or None.
    """
    from model.user import User
    try:
        token = flask_request.cookies.get(
            current_app.config.get("JWT_TOKEN_NAME", "jwt_token")
        )
        if not token:
            auth_header = flask_request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "") if auth_header else None
        if not token:
            return None
        data = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        return User.query.filter_by(_uid=data.get("_uid")).first()
    except Exception:
        return None


class SipContactSubmission(db.Model):
    """
    Stores every submission from the SIP contact page.

    Columns
    -------
    id            auto-incrementing primary key
    uid           _uid of the submitting user (from JWT cookie)
    form_type     'involved' | 'help'
    selection     dropdown value chosen by the user
    message       optional free-text message
    status        'new' | 'in_progress' | 'resolved'
    created_at    UTC timestamp of submission
    updated_at    UTC timestamp of last status change
    reviewed_by   _uid of the admin who last changed the status
    """

    __tablename__ = "sip_contact_submissions"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid         = db.Column(db.String(128), nullable=False, index=True)
    form_type   = db.Column(db.String(16),  nullable=False)
    selection   = db.Column(db.String(64),  nullable=False)
    message     = db.Column(db.Text,        nullable=True)
    status      = db.Column(db.String(16),  nullable=False, default="new")
    created_at  = db.Column(db.DateTime,    nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime,    nullable=False,
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))
    reviewed_by = db.Column(db.String(128), nullable=True)

    def __init__(self, form_type, selection, message=None):
        """
        Constructor — uid is resolved automatically from the JWT cookie,
        mirroring how BlogPost resolves author from the cookie.

        :raises ValueError: if no valid user session is found.
        """
        current_user = _get_user_from_cookie()
        if current_user is None:
            raise ValueError(
                "Cannot create SipContactSubmission: no valid user session found."
            )

        self.uid       = current_user._uid
        self.form_type = form_type
        self.selection = selection
        self.message   = message or None
        self.status    = "new"

    def read(self):
        return {
            "id":          self.id,
            "uid":         self.uid,
            "form_type":   self.form_type,
            "selection":   self.selection,
            "message":     self.message,
            "status":      self.status,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
            "reviewed_by": self.reviewed_by,
        }

    # Keep to_dict() as an alias so the API layer can use either name
    def to_dict(self):
        return self.read()

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    def __repr__(self):
        return (
            f"<SipContactSubmission id={self.id} uid={self.uid!r} "
            f"type={self.form_type!r} status={self.status!r}>"
        )

    def __str__(self):
        return json.dumps(self.read())


def initSipContact():
    """Create the sip_contact_submissions table if it doesn't exist."""
    with app.app_context():
        db.create_all()
        print("sip_contact_submissions table ready.")