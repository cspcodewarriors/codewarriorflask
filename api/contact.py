"""
api/sip_contact.py

REST API for Soroptimist International of Poway contact-form submissions.
Follows the same pattern as blog_api.py — flask_restful Resources with
@token_required from api.authorize.  Auth uses the JWT cookie (same as
the blog page), not an Authorization header.

Endpoints
─────────────────────────────────────────────────────────────────────────
POST   /api/sip/contact/involved     submit Get Involved form  (any login)
POST   /api/sip/contact/help         submit Get Help form      (any login)
GET    /api/sip/contact              list submissions           (Admin)
GET    /api/sip/contact/<id>         single submission          (Admin)
PATCH  /api/sip/contact/<id>         update status              (Admin)
DELETE /api/sip/contact/<id>         hard delete                (Admin)

Registration — add to __init__.py:
    from api.sip_contact import sip_contact_api
    app.register_blueprint(sip_contact_api)
"""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource

from api.authorize import token_required
from __init__ import db
from model.contact import SipContactSubmission


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

VALID_STATUSES = {"new", "in_progress", "resolved"}


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

    class _List(Resource):
        """
        GET /api/sip/contact
        Paginated list with optional filters (Admin only).

        Query params:
          form_type  – 'involved' | 'help'
          status     – 'new' | 'in_progress' | 'resolved'
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
api.add_resource(SipContactAPI._List,     '/sip/contact')
api.add_resource(SipContactAPI._Detail,   '/sip/contact/<int:submission_id>')