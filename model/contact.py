from datetime import datetime, timezone
from __init__ import db          # import the shared SQLAlchemy instance


class SipContactSubmission(db.Model):
    __tablename__ = "sip_contact_submissions"

    # ── Identity ──────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # ── Link to the submitting user ───────────────────────────────────────────
    uid = db.Column(
        db.String(128),
        nullable=False,
        index=True,
        comment="uid of the submitting user from the users table",
    )

    # ── Which form? ───────────────────────────────────────────────────────────
    form_type = db.Column(
        db.String(16),
        nullable=False,
        comment="'involved' or 'help'",
    )

    # ── Dropdown selection ────────────────────────────────────────────────────
    selection = db.Column(
        db.String(64),
        nullable=False,
        comment=(
            "For 'involved': volunteer | member.  "
            "For 'help': program slug."
        ),
    )

    # ── Optional message body ─────────────────────────────────────────────────
    message = db.Column(db.Text, nullable=True)

    # ── Workflow ──────────────────────────────────────────────────────────────
    status = db.Column(
        db.String(16),
        nullable=False,
        default="new",
        comment="new | in_progress | resolved",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Admin audit ───────────────────────────────────────────────────────────
    reviewed_by = db.Column(
        db.String(128),
        nullable=True,
        comment="uid of the admin who last changed the status",
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def to_dict(self):
        """Return a JSON-serialisable dict (used by the API layer)."""
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

    def __repr__(self):
        return (
            f"<SipContactSubmission id={self.id} "
            f"uid={self.uid!r} type={self.form_type!r} "
            f"status={self.status!r}>"
        )