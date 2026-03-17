""" Database model for Soroptimist International of Poway — Event Blog System """
from flask_login import UserMixin
from datetime import date
from sqlalchemy.exc import IntegrityError
import json

from __init__ import app, db


""" Helper Functions """

def today_date():
    """Returns today's date as a string in YYYY-MM-DD format."""
    return date.today().isoformat()


""" Database Models """


class BlogPost(db.Model):
    """
    BlogPost Model

    Represents a blog post created by an admin after completing a Soroptimist event.
    Modeled after a GitHub Issues-style submission form, where admins fill out a
    title, description, and event date to publish a post.

    Attributes:
        id (Column): The primary key, a unique integer identifier for the blog post.
        _author (Column): A string representing the name of the admin who created the post.
        _event_date (Column): A string (ISO format: YYYY-MM-DD) representing the date the event took place.
        _title (Column): A string representing the title of the blog post / event.
        _description (Column): A text field containing the admin's write-up of the event.
        _created_at (Column): A string representing the date the blog post was submitted. Defaults to today.
        _published (Column): A boolean indicating whether the post is visible to the public. Defaults to False.
        _program_tag (Column): An optional string tag linking the post to a specific SIP program
                               (e.g. "Live Your Dream", "STAT!", "Dream It Be It").
    """
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    _user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship("User", backref=db.backref("blog_posts", cascade="all, delete-orphan"))
    _author = db.Column(db.String(255), unique=False, nullable=False)
    _event_date = db.Column(db.String(50), unique=False, nullable=False)
    _title = db.Column(db.String(255), unique=False, nullable=False)
    _description = db.Column(db.Text, unique=False, nullable=False)
    _created_at = db.Column(db.String(50), unique=False, nullable=False, default=today_date)
    _published = db.Column(db.Boolean, default=False, nullable=False)
    _program_tag = db.Column(db.String(255), unique=False, nullable=True)

    def __init__(self, user_id, author, event_date, title, description, program_tag=None, published=False):
        """
        Constructor for BlogPost.

        :param user_id: Foreign key linking to the User who created this post.
        :param author: Display name of the admin submitting the post (denormalized for convenience).
        :param event_date: Date of the event in YYYY-MM-DD format.
        :param title: Title of the blog post.
        :param description: Full description / write-up of the event.
        :param program_tag: Optional — the SIP program this event is associated with.
        :param published: Whether the post is immediately visible. Defaults to False (draft).
        """
        self._user_id = user_id
        self._author = author
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
        self._user_id = user_id
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
        :return: dict representation of the blog post.
        """
        return {
            "id": self.id,
            "user_id": self._user_id,
            "author": self.user.name if self.user else self.author,
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

        :param inputs: A dictionary of fields to update.
        :return: self if successful, None if IntegrityError occurs.
        """
        if not isinstance(inputs, dict):
            return self

        author = inputs.get("author", "")
        event_date = inputs.get("event_date", "")
        title = inputs.get("title", "")
        description = inputs.get("description", "")
        published = inputs.get("published", None)
        program_tag = inputs.get("program_tag", None)

        if author:
            self.author = author
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
    Call this from your main app initialization alongside initUsers().
    """
    with app.app_context():
        db.create_all()

        # Sample posts — one per SIP program to validate the tagging system
        posts = [
            BlogPost(
                author="Jane Smith",
                event_date="2025-03-01",
                title="Spring Live Your Dream Awards Ceremony",
                description="This year's Live Your Dream ceremony recognized five incredible women from the Poway community. Each recipient shared her story of perseverance, family, and hope. The evening raised over $3,000 in additional donations to fund next year's grants.",
                program_tag="Live Your Dream",
                published=True
            ),
            BlogPost(
                author="Maria Lopez",
                event_date="2025-02-14",
                title="Dream It, Be It Career Day at Poway High",
                description="Over 60 girls attended our Dream It, Be It career workshop at Poway High School. Volunteers from fields including medicine, engineering, and education shared their journeys. Students left with goal-setting worksheets and mentor contact cards.",
                program_tag="Dream It Be It",
                published=True
            ),
            BlogPost(
                author="Sarah Chen",
                event_date="2025-01-20",
                title="STAT! Awareness and Resource Fair",
                description="We partnered with three local nonprofits to host a resource fair for human trafficking survivors. Attendees received information on legal aid, counseling services, and job training programs. Over 40 survivors connected with services during the event.",
                program_tag="STAT!",
                published=False
            ),
            BlogPost(
                author="Admin",
                event_date="2025-03-10",
                title="Abraxas Scholarship Presentation 2025",
                description="We proudly presented this year's Abraxas Scholarship to two outstanding students who demonstrated exceptional dedication to their education despite significant personal challenges. Both recipients plan to pursue community college in the fall.",
                program_tag="Abraxas Scholarship",
                published=False
            ),
        ]

        for post in posts:
            try:
                post.create()
            except IntegrityError:
                db.session.remove()
                print(f"Record already exists or error for post: {post.title}")