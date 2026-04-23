"""
Endpoints
─────────────────────────────────────────────────────────────────────────
GET   /api/notifications                list notifications for current user
PATCH /api/notifications/<id>/read      mark one notification as read
POST  /api/notifications/read-all       mark all notifications as read
"""

from flask import Blueprint, jsonify, g
from flask_restful import Api, Resource

from api.authorize import token_required
from __init__ import db
from model.notification import Notification


notification_api = Blueprint('notification_api', __name__, url_prefix='/api')
api = Api(notification_api)


class NotificationAPI:

    class _List(Resource):
        """
        GET /api/notifications
        Returns up to 50 most-recent notifications for the logged-in user,
        newest first. Also includes an unread count.
        """
        @token_required()
        def get(self):
            items = (
                Notification.query
                .filter_by(uid=g.current_user._uid)
                .order_by(Notification.created_at.desc())
                .limit(50)
                .all()
            )
            unread = sum(1 for n in items if not n.is_read)
            return {
                "items":  [n.read() for n in items],
                "unread": unread,
            }, 200

    class _MarkRead(Resource):
        """
        PATCH /api/notifications/<id>/read
        Marks a single notification as read (owner only).
        """
        @token_required()
        def patch(self, notif_id):
            n = db.session.get(Notification, notif_id)
            if n is None or n.uid != g.current_user._uid:
                return {"message": "Notification not found."}, 404
            n.is_read = True
            db.session.commit()
            return jsonify(n.read())

    class _MarkAllRead(Resource):
        """
        POST /api/notifications/read-all
        Marks every unread notification for the current user as read.
        """
        @token_required()
        def post(self):
            Notification.query.filter_by(
                uid=g.current_user._uid, is_read=False
            ).update({"is_read": True})
            db.session.commit()
            return {"message": "All notifications marked as read."}, 200


# Note: /read-all must be registered before /<int:notif_id>/read so Flask
# doesn't try to coerce "read-all" as an integer.
api.add_resource(NotificationAPI._List,       '/notifications')
api.add_resource(NotificationAPI._MarkAllRead,'/notifications/read-all')
api.add_resource(NotificationAPI._MarkRead,   '/notifications/<int:notif_id>/read')
