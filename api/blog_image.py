"""
API for Blog Post Images
========================

Mirrors the pfp_api pattern.

Endpoints
---------
GET    /api/blog/images?post_id=<id>        — list filenames for a post (public)
GET    /api/blog/images/data?post_id=<id>   — return base64 payload for all images (public)
POST   /api/blog/images                     — upload one image      (Admin)
DELETE /api/blog/images                     — delete one image      (Admin)
DELETE /api/blog/images/all                 — delete all for a post (Admin)
"""

from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource

from api.authorize import token_required
from model.blog_image import (
    blog_image_upload,
    blog_image_decode,
    blog_image_delete,
    blog_images_delete_all,
    blog_images_list,
)
from model.blog import BlogPost

blog_image_api = Blueprint('blog_image_api', __name__, url_prefix='/api')
api = Api(blog_image_api)


class BlogImageAPI:

    class _List(Resource):
        """
        GET  /api/blog/images?post_id=<id>
             Returns a JSON list of filenames stored for the post.
             Public — no auth required.
        """
        def get(self):
            post_id = request.args.get('post_id')
            if not post_id:
                return {'message': 'post_id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            filenames = blog_images_list(str(post_id))
            return jsonify({'post_id': post_id, 'images': filenames})

    class _Data(Resource):
        """
        GET  /api/blog/images/data?post_id=<id>
             Returns JSON list of {filename, data} objects where data is a
             base64 string ready to use in an <img src="data:image/png;base64,…"> tag.
             Public — no auth required.
        """
        def get(self):
            post_id = request.args.get('post_id')
            if not post_id:
                return {'message': 'post_id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            filenames = blog_images_list(str(post_id))
            result = []
            for fn in filenames:
                encoded = blog_image_decode(str(post_id), fn)
                if encoded:
                    result.append({'filename': fn, 'data': encoded})

            return jsonify({'post_id': post_id, 'images': result})

    class _Upload(Resource):
        """
        POST /api/blog/images
             Upload one image (base64) and attach it to a post.

             Request JSON
             ------------
             {
               "post_id": 7,
               "image":   "<base64 string or data-URI>"
             }

             Returns
             -------
             { "filename": "7_<uuid>.png" }
        """
        @token_required("Admin")
        def post(self):
            body = request.get_json()
            if not body:
                return {'message': 'JSON body required'}, 400

            post_id = body.get('post_id')
            if not post_id:
                return {'message': 'post_id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            image_data = body.get('image')
            if not image_data:
                return {'message': 'image (base64) is required'}, 400

            filename = blog_image_upload(image_data, str(post_id))
            if not filename:
                return {'message': 'An error occurred while uploading the image'}, 500

            return jsonify({'filename': filename, 'post_id': post_id})

    class _Delete(Resource):
        """
        DELETE /api/blog/images
               Delete a single image for a post.

               Request JSON: { "post_id": 7, "filename": "7_abc.png" }
        """
        @token_required("Admin")
        def delete(self):
            body = request.get_json()
            if not body:
                return {'message': 'JSON body required'}, 400

            post_id  = body.get('post_id')
            filename = body.get('filename')

            if not post_id:
                return {'message': 'post_id is required'}, 400
            if not filename:
                return {'message': 'filename is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            if not blog_image_delete(str(post_id), filename):
                return {'message': 'An error occurred while deleting the image, check permissions'}, 500

            return {'message': f'Image {filename} deleted successfully'}, 200

    class _DeleteAll(Resource):
        """
        DELETE /api/blog/images/all
               Delete every image for a post (e.g. when the post itself is deleted).

               Request JSON: { "post_id": 7 }
        """
        @token_required("Admin")
        def delete(self):
            body = request.get_json()
            if not body:
                return {'message': 'JSON body required'}, 400

            post_id = body.get('post_id')
            if not post_id:
                return {'message': 'post_id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            if not blog_images_delete_all(str(post_id)):
                return {'message': 'An error occurred while deleting images'}, 500

            return {'message': f'All images for post {post_id} deleted successfully'}, 200


# ── register routes ────────────────────────────────────────────────────────────
api.add_resource(BlogImageAPI._List,      '/blog/images')
api.add_resource(BlogImageAPI._Data,      '/blog/images/data')
api.add_resource(BlogImageAPI._Upload,    '/blog/images/upload')
api.add_resource(BlogImageAPI._Delete,    '/blog/images/delete')
api.add_resource(BlogImageAPI._DeleteAll, '/blog/images/all')