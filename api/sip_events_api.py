"""
SIP Events API
CRUD endpoints for Soroptimist International of Poway calendar events.

Endpoints:
  GET    /api/sip/events          - list all events (public)
  GET    /api/sip/events/<id>     - get single event (public)
  POST   /api/sip/events          - create event  (Admin only)
  PUT    /api/sip/events/<id>     - update event  (Admin only)
  DELETE /api/sip/events/<id>     - delete event  (Admin only)
"""
from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from model.sip_event import SipEvent
from api.authorize import auth_required
from __init__ import db

sip_events_api = Blueprint('sip_events_api', __name__, url_prefix='/api/sip')
api = Api(sip_events_api)


class SipEventsAPI:

    class _List(Resource):
        def get(self):
            """Return all events sorted by date ascending."""
            return jsonify(SipEvent.get_all())

        @auth_required(roles='Admin')
        def post(self):
            """Create a new event. Requires Admin role."""
            data = request.get_json() or {}
            required = ['title', 'date', 'startTime', 'endTime', 'location']
            missing = [f for f in required if not data.get(f)]
            if missing:
                return {'message': f"Missing required fields: {', '.join(missing)}"}, 400

            try:
                event = SipEvent(
                    title=data['title'],
                    date=data['date'],
                    start_time=data['startTime'],
                    end_time=data['endTime'],
                    location=data['location'],
                    notes=data.get('notes', ''),
                    event_type=data.get('eventType', 'blue'),
                ).create()
                return jsonify(event.read())
            except ValueError as e:
                return {'message': str(e)}, 400
            except Exception as e:
                return {'message': 'Server error', 'error': str(e)}, 500

    class _Item(Resource):
        def get(self, event_id):
            """Return a single event by ID."""
            event = SipEvent.get_by_id(event_id)
            if not event:
                return {'message': 'Event not found'}, 404
            return jsonify(event.read())

        @auth_required(roles='Admin')
        def put(self, event_id):
            """Update an existing event. Requires Admin role."""
            event = SipEvent.get_by_id(event_id)
            if not event:
                return {'message': 'Event not found'}, 404

            data = request.get_json() or {}
            try:
                event.update(data)
                return jsonify(event.read())
            except Exception as e:
                return {'message': 'Update failed', 'error': str(e)}, 500

        @auth_required(roles='Admin')
        def delete(self, event_id):
            """Delete an event. Requires Admin role."""
            event = SipEvent.get_by_id(event_id)
            if not event:
                return {'message': 'Event not found'}, 404

            try:
                event.delete()
                return {'message': 'Event deleted'}, 200
            except Exception as e:
                return {'message': 'Delete failed', 'error': str(e)}, 500


api.add_resource(SipEventsAPI._List, '/events')
api.add_resource(SipEventsAPI._Item, '/events/<int:event_id>')
