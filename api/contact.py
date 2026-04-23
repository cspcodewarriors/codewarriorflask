"""
Endpoints
─────────────────────────────────────────────────────────────────────────
POST   /api/sip/contact/involved          submit Get Involved form  (any login)
POST   /api/sip/contact/help              submit Get Help form      (any login)
GET    /api/sip/contact/pending           pending volunteer requests (Admin)
GET    /api/sip/contact                   list submissions           (Admin)
GET    /api/sip/contact/<id>              single submission          (Admin)
PATCH  /api/sip/contact/<id>              update status              (Admin)
PATCH  /api/sip/contact/<id>/approve      approve volunteer request  (Admin)
PATCH  /api/sip/contact/<id>/decline      decline volunteer request  (Admin)
DELETE /api/sip/contact/<id>              hard delete                (Admin)
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource

from api.authorize import token_required
from __init__ import db
from model.contact import SipContactSubmission
from model.notification import Notification

# Human-readable labels for selections (mirrors frontend SEL_LABELS)
_SEL_LABELS = {
    "volunteer":            "Volunteer",
    "member":               "Join as a Member",
    "transitional-housing": "Transitional Housing",
    "live-your-dream":      "Live Your Dream",
    "dream-it-be-it":       "Dream It Be It",
    "abraxas":              "Abraxas Scholarship",
    "colegio":              "Colegio La Esperanza",
}


sip_contact_api = Blueprint('sip_contact_api', __name__, url_prefix='/api')
api = Api(sip_contact_api)

# ── Allowed values ────────────────────────────────────────────────────────────

INVOLVED_SELECTIONS = {"volunteer", "member"}

HELP_SELECTIONS = {
    "transitional-housing",
    "live-your-dream",
    "dream-it-be-it",
    "abraxas",
    "colegio",
}

VALID_STATUSES = {"new", "in_progress", "resolved", "approved", "declined"}


# ── Resources ─────────────────────────────────────────────────────────────────

class SipContactAPI:

    class _Involved(Resource):
        """
        POST /api/sip/contact/involved
        Body: { "selection": "volunteer" | "member", "message": "..." }
        uid is resolved from the JWT cookie inside SipContactSubmission.__init__()
        — same pattern as BlogPost.__init__() resolving author from cookie.
        """
        @token_required()
        def post(self):
            body = request.get_json(silent=True) or {}

            selection = body.get("selection", "").strip().lower()
            if selection not in INVOLVED_SELECTIONS:
                return {
                    "message": f"selection must be one of: {', '.join(sorted(INVOLVED_SELECTIONS))}."
                }, 422

            try:
                submission = SipContactSubmission(
                    form_type = "involved",
                    selection = selection,
                    message   = body.get("message", "").strip() or None,
                )
            except ValueError as e:
                return {"message": str(e)}, 401

            result = submission.create()
            if not result:
                return {"message": "Failed to save submission."}, 400

            return jsonify(result.read())

    class _Help(Resource):
        """
        POST /api/sip/contact/help
        Body: { "selection": "<program-slug>", "message": "..." }
        uid is resolved from the JWT cookie inside SipContactSubmission.__init__().
        """
        @token_required()
        def post(self):
            body = request.get_json(silent=True) or {}

            selection = body.get("selection", "").strip().lower()
            if selection not in HELP_SELECTIONS:
                return {
                    "message": f"selection must be one of: {', '.join(sorted(HELP_SELECTIONS))}."
                }, 422

            try:
                submission = SipContactSubmission(
                    form_type = "help",
                    selection = selection,
                    message   = body.get("message", "").strip() or None,
                )
            except ValueError as e:
                return {"message": str(e)}, 401

            result = submission.create()
            if not result:
                return {"message": "Failed to save submission."}, 400

            return jsonify(result.read())

    class _Pending(Resource):
        """
        GET /api/sip/contact/pending
        Returns all 'involved' submissions whose status is 'new' (awaiting approval).
        Admin only.
        """
        @token_required("Admin")
        def get(self):
            items = (
                SipContactSubmission.query
                .filter_by(form_type="involved", status="new")
                .order_by(SipContactSubmission.created_at.asc())
                .all()
            )
            return {
                "items": [s.read() for s in items],
                "count": len(items),
            }, 200

    class _Approve(Resource):
        """
        PATCH /api/sip/contact/<id>/approve
        Sets an 'involved' submission's status to 'approved' and sends the
        submitting user a notification. Admin only.
        """
        @token_required("Admin")
        def patch(self, submission_id):
            sub = db.session.get(SipContactSubmission, submission_id)
            if sub is None:
                return {"message": "Submission not found."}, 404
            if sub.form_type != "involved":
                return {"message": "Only 'Get Involved' submissions can be approved."}, 422

            sub.status      = "approved"
            sub.reviewed_by = g.current_user._uid
            sub.updated_at  = datetime.now(timezone.utc)
            db.session.commit()

            try:
                label = _SEL_LABELS.get(sub.selection, sub.selection)
                notif = Notification(
                    uid   = sub.uid,
                    title = "Your request was approved!",
                    body  = (
                        f"Great news! Your request to {label} with "
                        f"Soroptimist International of Poway has been approved."
                    ),
                )
                db.session.add(notif)
                db.session.commit()
            except Exception:
                db.session.rollback()

            return jsonify(sub.read())

    class _Decline(Resource):
        """
        PATCH /api/sip/contact/<id>/decline
        Sets an 'involved' submission's status to 'declined' and sends the
        submitting user a notification. Admin only.
        """
        @token_required("Admin")
        def patch(self, submission_id):
            sub = db.session.get(SipContactSubmission, submission_id)
            if sub is None:
                return {"message": "Submission not found."}, 404
            if sub.form_type != "involved":
                return {"message": "Only 'Get Involved' submissions can be declined."}, 422

            sub.status      = "declined"
            sub.reviewed_by = g.current_user._uid
            sub.updated_at  = datetime.now(timezone.utc)
            db.session.commit()

            try:
                label = _SEL_LABELS.get(sub.selection, sub.selection)
                notif = Notification(
                    uid   = sub.uid,
                    title = "Update on your volunteer request",
                    body  = (
                        f"Thank you for your interest in {label}. "
                        f"Unfortunately, your request was not approved at this time. "
                        f"Please feel free to reach out if you have any questions."
                    ),
                )
                db.session.add(notif)
                db.session.commit()
            except Exception:
                db.session.rollback()

            return jsonify(sub.read())

    class _List(Resource):
        """
        GET /api/sip/contact
        Paginated list with optional filters (Admin only).

        Query params:
          form_type  – 'involved' | 'help'
          status     – 'new' | 'in_progress' | 'resolved' | 'approved' | 'declined'
          page       – integer (default 1)
          per_page   – integer 1–100 (default 25)
        """
        @token_required("Admin")
        def get(self):
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
                return {"message": "page and per_page must be integers."}, 400

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

            return {
                "items":    [s.read() for s in pagination.items],
                "total":    pagination.total,
                "page":     pagination.page,
                "per_page": pagination.per_page,
                "pages":    pagination.pages,
            }, 200

    class _Detail(Resource):
        """
        GET    /api/sip/contact/<id>  fetch one submission  (Admin)
        PATCH  /api/sip/contact/<id>  update status         (Admin)
        DELETE /api/sip/contact/<id>  hard delete           (Admin)
        """
        @token_required("Admin")
        def get(self, submission_id):
            sub = db.session.get(SipContactSubmission, submission_id)
            if sub is None:
                return {"message": "Submission not found."}, 404
            return jsonify(sub.read())

        @token_required("Admin")
        def patch(self, submission_id):
            sub = db.session.get(SipContactSubmission, submission_id)
            if sub is None:
                return {"message": "Submission not found."}, 404

            body       = request.get_json(silent=True) or {}
            new_status = body.get("status", "").strip().lower()

            if new_status and new_status not in VALID_STATUSES:
                return {
                    "message": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}."
                }, 422

            if new_status:
                sub.status = new_status

            sub.reviewed_by = g.current_user._uid
            sub.updated_at  = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify(sub.read())

        @token_required("Admin")
        def delete(self, submission_id):
            sub = db.session.get(SipContactSubmission, submission_id)
            if sub is None:
                return {"message": "Submission not found."}, 404

            sub.delete()
            return {"message": "Submission deleted.", "id": submission_id}, 200


# ── Register routes ───────────────────────────────────────────────────────────
api.add_resource(SipContactAPI._Involved, '/sip/contact/involved')
api.add_resource(SipContactAPI._Help,     '/sip/contact/help')
api.add_resource(SipContactAPI._Pending,  '/sip/contact/pending')
api.add_resource(SipContactAPI._List,     '/sip/contact')
api.add_resource(SipContactAPI._Detail,   '/sip/contact/<int:submission_id>')
api.add_resource(SipContactAPI._Approve,  '/sip/contact/<int:submission_id>/approve')
api.add_resource(SipContactAPI._Decline,  '/sip/contact/<int:submission_id>/decline')