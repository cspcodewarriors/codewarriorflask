""" Database model for Soroptimist International of Poway — Event Blog System """
from datetime import date
from sqlalchemy.exc import IntegrityError
from flask import request as flask_request, current_app
import jwt
import json

from __init__ import app, db


""" Helper Functions """

def today_date():
    """Returns today's date as a string in YYYY-MM-DD format."""
    return date.today().isoformat()


def get_user_from_cookie():
    """
    Resolves the current user from the JWT cookie.
    Returns the User object if valid, or None if the cookie is missing or invalid.
    This is used by BlogPost.__init__() so the model can stamp the author
    automatically without the caller needing to pass user_id explicitly.
    """
    from model.user import User
    try:
        token = flask_request.cookies.get(current_app.config.get("JWT_TOKEN_NAME", "jwt_token"))
        if not token:
            # Fallback: check Authorization header
            auth_header = flask_request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "") if auth_header else None
        if not token:
            return None
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return User.query.filter_by(_uid=data.get("_uid")).first()
    except Exception:
        return None


""" Database Models """


class BlogPost(db.Model):
    """
    BlogPost Model

    Represents a blog post created by an admin after completing a Soroptimist event.
    Modeled after a GitHub Issues-style submission form, where admins fill out a
    title, description, and event date to publish a post.

    Author identity (_user_id and _author) are resolved automatically from the
    JWT cookie at creation time — callers do not pass user identity manually.

    Attributes:
        id (Column): The primary key, a unique integer identifier for the blog post.
        _user_id (Column): Foreign key to the users table, resolved from the JWT cookie.
        _author (Column): Denormalized author name snapshot for fast reads without a join.
        _event_date (Column): A string (ISO format: YYYY-MM-DD) representing when the event took place.
        _title (Column): A string representing the title of the blog post / event.
        _description (Column): A text field containing the admin's write-up of the event.
        _created_at (Column): A string representing when the post was submitted. Defaults to today.
        _published (Column): A boolean indicating whether the post is visible to the public. Defaults to False.
        _program_tag (Column): An optional string tag linking the post to a specific SIP program
                               (e.g. "Live Your Dream", "STAT!", "Dream It Be It").
    """
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    _user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    _author = db.Column(db.String(255), unique=False, nullable=False)
    _event_date = db.Column(db.String(50), unique=False, nullable=False)
    _title = db.Column(db.String(255), unique=False, nullable=False)
    _description = db.Column(db.Text, unique=False, nullable=False)
    _created_at = db.Column(db.String(50), unique=False, nullable=False, default=today_date)
    _published = db.Column(db.Boolean, default=False, nullable=False)
    _program_tag = db.Column(db.String(255), unique=False, nullable=True)

    # Relationship back to User — use post.user.name to get the live name from the DB
    user = db.relationship("User", backref=db.backref("blog_posts", cascade="all, delete-orphan"))

    def __init__(self, event_date, title, description, program_tag=None, published=False):
        """
        Constructor for BlogPost.

        Author identity is resolved automatically from the JWT cookie —
        no need to pass user_id or author name as parameters.

        :param event_date: Date of the event in YYYY-MM-DD format.
        :param title: Title of the blog post.
        :param description: Full description / write-up of the event.
        :param program_tag: Optional — the SIP program this event is associated with.
        :param published: Whether the post is immediately visible. Defaults to False (draft).
        :raises ValueError: If no valid user session is found in the cookie.
        """
        current_user = get_user_from_cookie()
        if current_user is None:
            raise ValueError("Cannot create BlogPost: no valid user session found in cookie.")

        self._user_id = current_user.id
        self._author = current_user.name  # Denormalized snapshot of name at post time
        self._event_date = event_date
        self._title = title
        self._description = description
        self._created_at = today_date()
        self._published = published
        self._program_tag = program_tag

    # --- Property Getters and Setters ---

    @property
    def author(self):
        return self._author

    @author.setter
    def author(self, author):
        self._author = author

    @property
    def event_date(self):
        return self._event_date

    @event_date.setter
    def event_date(self, event_date):
        self._event_date = event_date

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def created_at(self):
        return self._created_at

    @property
    def published(self):
        return self._published

    @published.setter
    def published(self, published):
        self._published = bool(published)

    @property
    def program_tag(self):
        return self._program_tag

    @program_tag.setter
    def program_tag(self, program_tag):
        self._program_tag = program_tag

    # --- String Representation ---

    def __repr__(self):
        return f"BlogPost(id={self.id}, title={self._title}, author={self._author}, event_date={self._event_date}, published={self._published})"

    def __str__(self):
        return json.dumps(self.read())

    # --- CRUD Operations ---

    def create(self):
        """
        CRUD Create: Add a new blog post to the database.
        :return: self if successful, None if IntegrityError occurs.
        """
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def read(self):
        """
        CRUD Read: Convert the blog post to a dictionary for API responses.
        Returns the live user name from the relationship if available,
        falling back to the denormalized _author field.
        :return: dict representation of the blog post.
        """
        return {
            "id": self.id,
            "user_id": self._user_id,
            "author": self.user.name if self.user else self._author,
            "event_date": self.event_date,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "published": self.published,
            "program_tag": self.program_tag,
        }

    def update(self, inputs):
        """
        CRUD Update: Update blog post fields from a dictionary of inputs.
        Follows the same pattern as User.update() — only updates fields that are provided.
        Note: user_id and author cannot be changed after creation.

        :param inputs: A dictionary of fields to update.
        :return: self if successful, None if IntegrityError occurs.
        """
        if not isinstance(inputs, dict):
            return self

        event_date = inputs.get("event_date", "")
        title = inputs.get("title", "")
        description = inputs.get("description", "")
        published = inputs.get("published", None)
        program_tag = inputs.get("program_tag", None)

        if event_date:
            self.event_date = event_date
        if title:
            self.title = title
        if description:
            self.description = description
        if published is not None:
            self.published = published
        if program_tag is not None:
            self.program_tag = program_tag

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None
        return self

    def delete(self):
        """
        CRUD Delete: Remove this blog post from the database.
        :return: None
        """
        try:
            db.session.delete(self)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return None

    def publish(self):
        """
        Convenience method to publish a draft post.
        :return: self
        """
        self._published = True
        db.session.commit()
        return self

    def unpublish(self):
        """
        Convenience method to revert a post back to draft status.
        :return: self
        """
        self._published = False
        db.session.commit()
        return self


""" Database Initialization and Test Data """

def initBlogPosts():
    """
    Creates the blog_posts table and seeds it with sample event posts.
    Since we are outside a request context, user_id is set directly from the
    first Admin user found in the DB. Run initUsers() before this.
    """
    with app.app_context():
        from model.user import User
        db.create_all()

        # Find the admin user to attribute seed posts to
        admin = User.query.filter_by(_role="Admin").first()
        if not admin:
            print("initBlogPosts: No Admin user found — skipping seed data. Run initUsers() first.")
            return

        seed_posts = [
            {
                "event_date": "2025-03-01",
                "title": "Spring Live Your Dream Awards Ceremony",
                "description": "This year's Live Your Dream ceremony recognized five incredible women from the Poway community. Each recipient shared her story of perseverance, family, and hope. The evening raised over $3,000 in additional donations to fund next year's grants.",
                "program_tag": "Live Your Dream",
                "published": True,
            },
            {
                "event_date": "2025-02-14",
                "title": "Dream It, Be It Career Day at Poway High",
                "description": "Over 60 girls attended our Dream It, Be It career workshop at Poway High School. Volunteers from fields including medicine, engineering, and education shared their journeys. Students left with goal-setting worksheets and mentor contact cards.",
                "program_tag": "Dream It Be It",
                "published": True,
            },
            {
                "event_date": "2025-01-20",
                "title": "STAT! Awareness and Resource Fair",
                "description": "We partnered with three local nonprofits to host a resource fair for human trafficking survivors. Attendees received information on legal aid, counseling services, and job training programs. Over 40 survivors connected with services during the event.",
                "program_tag": "STAT!",
                "published": False,
            },
            {
                "event_date": "2025-03-10",
                "title": "Abraxas Scholarship Presentation 2025",
                "description": "We proudly presented this year's Abraxas Scholarship to two outstanding students who demonstrated exceptional dedication to their education despite significant personal challenges. Both recipients plan to pursue community college in the fall.",
                "program_tag": "Abraxas Scholarship",
                "published": False,
            },
        ]

        for data in seed_posts:
            try:
                # Bypass __init__ cookie logic since we are outside a request context
                post = BlogPost.__new__(BlogPost)
                post._user_id = admin.id
                post._author = admin.name
                post._event_date = data["event_date"]
                post._title = data["title"]
                post._description = data["description"]
                post._created_at = today_date()
                post._published = data["published"]
                post._program_tag = data["program_tag"]
                post.create()
            except IntegrityError:
                db.session.remove()
                print(f"Record already exists or error for post: {data['title']}")