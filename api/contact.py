from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, request, jsonify, g
from __init__ import db
from model.contact import SipContactSubmission


sip_contact_bp = Blueprint("sip_contact", __name__)

# ── Allowed values ────────────────────────────────────────────────────────────

INVOLVED_SELECTIONS = {"volunteer", "member"}

HELP_SELECTIONS = {
    "transitional-housing",
    "live-your-dream",
    "dream-it-be-it",
    "abraxas",
    "colegio",
}

VALID_STATUSES = {"new", "in_progress", "resolved"}


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _current_user():
    """Return the current user from g (populated by your existing auth layer)."""
    return getattr(g, "current_user", None)


def login_required(f):
    """Decorator: reject unauthenticated requests with 401."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _current_user() is None:
            return jsonify({"message": "Authentication required."}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Decorator: reject non-admins with 403."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if user is None:
            return jsonify({"message": "Authentication required."}), 401
        if not getattr(user, "is_admin", False):
            return jsonify({"message": "Admin access required."}), 403
        return f(*args, **kwargs)
    return wrapper


# ── Submission endpoints ──────────────────────────────────────────────────────

@sip_contact_bp.route("/api/sip/contact/involved", methods=["POST"])
@login_required
def submit_involved():
    """
    Submit the 'Get Involved' form.

    Body: { "selection": "volunteer" | "member", "message": "..." }
    uid is taken from the authenticated session.
    """
    data = request.get_json(silent=True) or {}

    selection = data.get("selection", "").strip().lower()
    if selection not in INVOLVED_SELECTIONS:
        return jsonify({
            "message": f"selection must be one of: {', '.join(sorted(INVOLVED_SELECTIONS))}."
        }), 422

    user = _current_user()
    submission = SipContactSubmission(
        uid       = str(getattr(user, "uid", None) or getattr(user, "id", "")),
        form_type = "involved",
        selection = selection,
        message   = data.get("message", "").strip() or None,
    )
    db.session.add(submission)
    db.session.commit()

    return jsonify(submission.to_dict()), 201


@sip_contact_bp.route("/api/sip/contact/help", methods=["POST"])
@login_required
def submit_help():
    """
    Submit the 'Get Help' form.

    Body: { "selection": "<program-slug>", "message": "..." }
    uid is taken from the authenticated session.
    """
    data = request.get_json(silent=True) or {}

    selection = data.get("selection", "").strip().lower()
    if selection not in HELP_SELECTIONS:
        return jsonify({
            "message": f"selection must be one of: {', '.join(sorted(HELP_SELECTIONS))}."
        }), 422

    user = _current_user()
    submission = SipContactSubmission(
        uid       = str(getattr(user, "uid", None) or getattr(user, "id", "")),
        form_type = "help",
        selection = selection,
        message   = data.get("message", "").strip() or None,
    )
    db.session.add(submission)
    db.session.commit()

    return jsonify(submission.to_dict()), 201


# ── Admin endpoints ───────────────────────────────────────────────────────────

@sip_contact_bp.route("/api/sip/contact", methods=["GET"])
@admin_required
def list_contacts():
    """
    Paginated list with optional filters.

    Query params:
      form_type  – 'involved' | 'help'
      status     – 'new' | 'in_progress' | 'resolved'
      page       – integer (default 1)
      per_page   – integer 1–100 (default 25)
    """
    query = SipContactSubmission.query

    form_type = request.args.get("form_type", "").strip().lower()
    if form_type in ("involved", "help"):
        query = query.filter_by(form_type=form_type)

    status = request.args.get("status", "").strip().lower()
    if status in VALID_STATUSES:
        query = query.filter_by(status=status)

    query = query.order_by(SipContactSubmission.created_at.desc())

    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 25))))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "items":    [s.to_dict() for s in pagination.items],
        "total":    pagination.total,
        "page":     pagination.page,
        "per_page": pagination.per_page,
        "pages":    pagination.pages,
    }), 200


@sip_contact_bp.route("/api/sip/contact/<int:submission_id>", methods=["GET"])
@admin_required
def get_contact(submission_id):
    """Fetch one submission by ID."""
    sub = db.session.get(SipContactSubmission, submission_id)
    if sub is None:
        return jsonify({"message": "Submission not found."}), 404
    return jsonify(sub.to_dict()), 200


@sip_contact_bp.route("/api/sip/contact/<int:submission_id>", methods=["PATCH"])
@admin_required
def update_contact(submission_id):
    """
    Update the status of a submission.

    Body: { "status": "in_progress" | "resolved" | "new" }
    """
    sub = db.session.get(SipContactSubmission, submission_id)
    if sub is None:
        return jsonify({"message": "Submission not found."}), 404

    data       = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip().lower()

    if new_status and new_status not in VALID_STATUSES:
        return jsonify({
            "message": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}."
        }), 422

    if new_status:
        sub.status = new_status

    user = _current_user()
    if user:
        sub.reviewed_by = str(getattr(user, "uid", None) or getattr(user, "id", ""))

    sub.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(sub.to_dict()), 200


@sip_contact_bp.route("/api/sip/contact/<int:submission_id>", methods=["DELETE"])
@admin_required
def delete_contact(submission_id):
    """Permanently delete a submission."""
    sub = db.session.get(SipContactSubmission, submission_id)
    if sub is None:
        return jsonify({"message": "Submission not found."}), 404

    db.session.delete(sub)
    db.session.commit()

    return jsonify({"message": "Submission deleted.", "id": submission_id}), 200