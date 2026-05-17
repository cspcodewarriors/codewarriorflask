"""
Endpoints
─────────────────────────────────────────────────────────────────────────
GET    /api/ig/token     return stored token        (public — called by frontend)
POST   /api/ig/token     save a new token           (localhost only)
POST   /api/ig/refresh   refresh token via Instagram (localhost only)
"""

import functools
from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource

from model.ig_token import read_token, write_token, refresh_token


ig_api = Blueprint('ig_api', __name__, url_prefix='/api')
api = Api(ig_api)


def localhost_only(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if request.remote_addr not in ('127.0.0.1', '::1'):
            return {'error': 'Forbidden'}, 403
        return fn(*args, **kwargs)
    return wrapper


class IgAPI:

    class _Token(Resource):
        """
        GET  /api/ig/token  — called by the blog frontend to fetch the token.
        POST /api/ig/token  — one-time setup; localhost only.
                              Body: { "token": "IGQ..." }
        """
        def get(self):
            token = read_token()
            if not token:
                return {'error': 'No token configured'}, 404
            return jsonify({'token': token})

        @localhost_only
        def post(self):
            body  = request.get_json(silent=True) or {}
            token = body.get('token', '').strip()
            if not token:
                return {'error': 'token field required'}, 400
            write_token(token)
            return {'ok': True, 'message': 'Token saved.'}, 200

    class _Refresh(Resource):
        """
        POST /api/ig/refresh — called by cron job; localhost only.
        Exchanges the stored token for a fresh 60-day one.
        """
        @localhost_only
        def post(self):
            try:
                new_token, expires_in = refresh_token()
                return {'ok': True, 'expires_in': expires_in}, 200
            except Exception as e:
                return {'error': str(e)}, 500


api.add_resource(IgAPI._Token,   '/ig/token')
api.add_resource(IgAPI._Refresh, '/ig/refresh')

