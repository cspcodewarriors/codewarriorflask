""" API for Soroptimist International of Poway — Event Blog System """
from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from __init__ import app, db
from api.authorize import token_required
from model.blog import BlogPost
from model.user import User

blog_api = Blueprint('blog_api', __name__, url_prefix='/api')

api = Api(blog_api)


class BlogAPI:

    class _CRUD(Resource):
        """
        Main blog post CRUD operations.

        POST   /api/blog  — Admin creates a new blog post (saved as draft by default)
        GET    /api/blog  — Anyone can read all published posts; Admins see all including drafts
        PUT    /api/blog  — Admin updates an existing post by id
        DELETE /api/blog  — Admin deletes a post by id
        """

        @token_required("Admin")
        def post(self):
            """
            Create a new blog post.

            Reads from the JSON body. The author name is pulled automatically
            from the authenticated user via the foreign key — no need to pass it manually.

            Required fields: event_date, title, description
            Optional fields: program_tag, published (bool, defaults to False)

            Returns:
                JSON response with the created blog post or an error message.
            """
            current_user = g.current_user
            body = request.get_json()

            # Validate required fields
            event_date = body.get('event_date')
            if not event_date:
                return {'message': 'event_date is required (YYYY-MM-DD)'}, 400

            title = body.get('title')
            if not title or len(title) < 2:
                return {'message': 'title is required and must be at least 2 characters'}, 400

            description = body.get('description')
            if not description or len(description) < 2:
                return {'message': 'description is required and must be at least 2 characters'}, 400

            # Optional fields
            program_tag = body.get('program_tag', None)
            published = body.get('published', False)

            # Build and save the post — author name comes from the linked User record
            post = BlogPost(
                user_id=current_user.id,
                author=current_user.name,
                event_date=event_date,
                title=title,
                description=description,
                program_tag=program_tag,
                published=published
            )

            result = post.create()
            if not result:
                return {'message': 'Failed to create blog post, possible duplicate or database error'}, 400

            return jsonify(result.read())

        def get(self):
            """
            Retrieve blog posts.

            - Public users see only published posts.
            - Admins (via token) see all posts including drafts.

            Query Parameters:
                program_tag (str): Filter posts by SIP program tag.
                published (bool): Filter by published status (Admin only).

            Returns:
                JSON list of blog post dictionaries.
            """
            # Check if an admin token was provided — admins see all posts
            auth_header = request.cookies.get(app.config.get("JWT_TOKEN_NAME", "jwt_token")) or \
                          request.headers.get("Authorization", "").replace("Bearer ", "")

            is_admin = False
            if auth_header:
                try:
                    import jwt
                    data = jwt.decode(auth_header, app.config["SECRET_KEY"], algorithms=["HS256"])
                    user = User.query.filter_by(_uid=data.get("_uid")).first()
                    if user and user.is_admin():
                        is_admin = True
                except Exception:
                    pass

            # Build base query
            query = BlogPost.query

            # Filter by program tag if provided
            program_tag = request.args.get('program_tag')
            if program_tag:
                query = query.filter_by(_program_tag=program_tag)

            # Non-admins only see published posts
            if not is_admin:
                query = query.filter_by(_published=True)
            else:
                # Admins can optionally filter by published status
                published_filter = request.args.get('published')
                if published_filter is not None:
                    query = query.filter_by(_published=published_filter.lower() == 'true')

            posts = query.order_by(BlogPost._event_date.desc()).all()
            return jsonify([post.read() for post in posts])

        @token_required("Admin")
        def put(self):
            """
            Update an existing blog post.

            Requires 'id' in the JSON body to identify the post.
            Only provided fields are updated — same pattern as User.update().

            Returns:
                JSON response with the updated blog post or an error message.
            """
            body = request.get_json()

            post_id = body.get('id')
            if not post_id:
                return {'message': 'Post id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            result = post.update(body)
            if not result:
                return {'message': 'Failed to update blog post'}, 400

            return jsonify(result.read())

        @token_required("Admin")
        def delete(self):
            """
            Delete a blog post.

            Requires 'id' in the JSON body.

            Returns:
                Success message or error.
            """
            body = request.get_json()

            post_id = body.get('id')
            if not post_id:
                return {'message': 'Post id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            post_data = post.read()
            post.delete()

            return {'message': f'Deleted blog post: {post_data["title"]}'}, 200

    class _Publish(Resource):
        """
        Publish / unpublish a blog post.

        POST /api/blog/publish  — Toggle published status for a post by id
        """

        @token_required("Admin")
        def post(self):
            """
            Publish or unpublish a blog post.

            Required fields: id, published (bool)

            Returns:
                JSON response with the updated blog post.
            """
            body = request.get_json()

            post_id = body.get('id')
            if not post_id:
                return {'message': 'Post id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            published = body.get('published')
            if published is None:
                return {'message': 'published (bool) is required'}, 400

            if published:
                post.publish()
            else:
                post.unpublish()

            return jsonify(post.read())

    class _ByUser(Resource):
        """
        Retrieve all blog posts written by a specific user.

        GET /api/blog/user  — Returns posts for the current user (or a target uid if Admin)
        """

        @token_required()
        def get(self):
            """
            Get blog posts by user.

            Query Parameters:
                uid (str): Target user's uid — Admin only. Defaults to current user.

            Returns:
                JSON list of blog posts belonging to the user.
            """
            current_user = g.current_user

            uid = request.args.get('uid')
            if uid and current_user.is_admin():
                user = User.query.filter_by(_uid=uid).first()
                if not user:
                    return {'message': f'User {uid} not found'}, 404
            else:
                user = current_user

            posts = BlogPost.query.filter_by(_user_id=user.id).order_by(BlogPost._event_date.desc()).all()
            return jsonify([post.read() for post in posts])

    class _Single(Resource):
        """
        Retrieve a single blog post by id.

        GET /api/blog/post?id=<id>
        """

        def get(self):
            """
            Get a single blog post by id.

            Query Parameters:
                id (int): The blog post id.

            Returns:
                JSON representation of the blog post, or 404 if not found / not published.
            """
            post_id = request.args.get('id')
            if not post_id:
                return {'message': 'Post id is required'}, 400

            post = BlogPost.query.get(post_id)
            if not post:
                return {'message': f'Blog post {post_id} not found'}, 404

            # Non-admins can only view published posts
            auth_header = request.cookies.get(app.config.get("JWT_TOKEN_NAME", "jwt_token")) or \
                          request.headers.get("Authorization", "").replace("Bearer ", "")
            is_admin = False
            if auth_header:
                try:
                    import jwt
                    data = jwt.decode(auth_header, app.config["SECRET_KEY"], algorithms=["HS256"])
                    user = User.query.filter_by(_uid=data.get("_uid")).first()
                    if user and user.is_admin():
                        is_admin = True
                except Exception:
                    pass

            if not post.published and not is_admin:
                return {'message': 'Blog post not found or not published'}, 404

            return jsonify(post.read())

    # Register all endpoints
    api.add_resource(_CRUD,    '/blog')
    api.add_resource(_Publish, '/blog/publish')
    api.add_resource(_ByUser,  '/blog/user')
    api.add_resource(_Single,  '/blog/post')