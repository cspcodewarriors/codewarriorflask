"""
SIP Contact Approval API
────────────────────────────────────────────────────────────────────────
Extends the existing sip_contact_api with admin-only approval endpoints
for "Get Involved" (volunteer / member) submissions.

New Endpoints
─────────────────────────────────────────────────────────────────────────
GET   /api/sip/contact/pending          pending Get Involved count + list  (Admin)
PATCH /api/sip/contact/<id>/approve     approve a Get Involved request     (Admin)
PATCH /api/sip/contact/<id>/decline     decline a Get Involved request     (Admin)

Changes to existing behaviour
──────────────────────────────
• VALID_STATUSES is expanded to include 'approved' and 'declined'.
• These two new routes must be registered on the SAME Blueprint as the
  existing sip_contact_api so they share the /api prefix.

How to wire it up
──────────────────
In your main app factory (e.g. __init__.py or main.py) import and register
this blueprint alongside the existing one:

    from api.sip_contact_approval import sip_approval_api
    app.register_blueprint(sip_approval_api)

The existing sip_contact_api blueprint stays unchanged — this file only
adds new routes and does not modify the model.

Model note
──────────
SipContactSubmission.status already accepts any string, so 'approved' and
'declined' are valid without a schema migration.  The only thing you may
want to do is update the VALID_STATUSES set in the existing api/contact.py
to include them so the PATCH /api/sip/contact/<id> filter still works:

    VALID_STATUSES = {"new", "in_progress", "resolved", "approved", "declined"}
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, g
from flask_restful import Api, Resource

from api.authorize import token_required
from __init__ import db
from model.contact import SipContactSubmission


# ── Blueprint ─────────────────────────────────────────────────────────────────

sip_approval_api = Blueprint("sip_approval_api", __name__, url_prefix="/api")
api = Api(sip_approval_api)


# ── Resources ─────────────────────────────────────────────────────────────────

class SipPendingAPI(Resource):
    """
    GET /api/sip/contact/pending

    Returns all 'Get Involved' submissions whose status is 'new'.
    Used by the notification bell to show admins how many requests
    need attention, and to populate the approval-tray cards.

    Response shape
    ──────────────
    {
        "count": 3,
        "items": [ { ...submission fields... }, ... ]
    }
    """

    @token_required("Admin")
    def get(self):
        pending = (
            SipContactSubmission.query
            .filter_by(form_type="involved", status="new")
            .order_by(SipContactSubmission.created_at.asc())   # oldest first
            .all()
        )
        return {
            "count": len(pending),
            "items": [s.read() for s in pending],
        }, 200


class SipApproveAPI(Resource):
    """
    PATCH /api/sip/contact/<id>/approve

    Marks the submission as 'approved' and records which admin acted.
    Only valid for 'Get Involved' submissions (form_type == 'involved').
    """

    @token_required("Admin")
    def patch(self, submission_id):
        sub = db.session.get(SipContactSubmission, submission_id)
        if sub is None:
            return {"message": "Submission not found."}, 404

        if sub.form_type != "involved":
            return {
                "message": "Only 'Get Involved' submissions can be approved."
            }, 422

        if sub.status in ("approved", "declined"):
            return {
                "message": f"Submission has already been {sub.status}."
            }, 409

        sub.status      = "approved"
        sub.reviewed_by = g.current_user._uid
        sub.updated_at  = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(sub.read())


class SipDeclineAPI(Resource):
    """
    PATCH /api/sip/contact/<id>/decline

    Marks the submission as 'declined' and records which admin acted.
    Only valid for 'Get Involved' submissions (form_type == 'involved').
    """

    @token_required("Admin")
    def patch(self, submission_id):
        sub = db.session.get(SipContactSubmission, submission_id)
        if sub is None:
            return {"message": "Submission not found."}, 404

        if sub.form_type != "involved":
            return {
                "message": "Only 'Get Involved' submissions can be declined."
            }, 422

        if sub.status in ("approved", "declined"):
            return {
                "message": f"Submission has already been {sub.status}."
            }, 409

        sub.status      = "declined"
        sub.reviewed_by = g.current_user._uid
        sub.updated_at  = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify(sub.read())


# ── Register routes ───────────────────────────────────────────────────────────

api.add_resource(SipPendingAPI,  "/sip/contact/pending")
api.add_resource(SipApproveAPI,  "/sip/contact/<int:submission_id>/approve")
api.add_resource(SipDeclineAPI,  "/sip/contact/<int:submission_id>/decline")