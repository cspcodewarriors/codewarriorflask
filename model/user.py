""" database dependencies to support sqliteDB examples """
from flask import current_app
from flask_login import UserMixin
from datetime import date
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

from __init__ import app, db
from model.github import GitHubUser
from model.kasm import KasmUser

""" Helper Functions """

def default_year():
    """Returns the default year for user enrollment based on the current month."""
    current_month = date.today().month
    current_year = date.today().year
    # If current month is between August (8) and December (12), the enrollment year is next year.
    if 7 <= current_month <= 12:
        current_year = current_year + 1
    return current_year 

""" Database Models """

''' Tutorial: https://www.sqlalchemy.org/library.html#tutorials, try to get into Python shell and follow along '''

class UserSection(db.Model):
    """ 
    UserSection Model

    A many-to-many relationship between the 'users' and 'sections' tables.

    Attributes:
        user_id (Column): An integer representing the user's unique identifier, a foreign key that references the 'users' table.
        section_id (Column): An integer representing the section's unique identifier, a foreign key that references the 'sections' table.
        year (Column): An integer representing the year the user enrolled with the section. Defaults to the current year.
    """
    __tablename__ = 'user_sections'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), primary_key=True)
    year = db.Column(db.Integer)

    # Junction table relationships: Records transactions linking User and Section
    # Each UserSection row records a User-Section pairing (like a transaction receipt)
    # Overlaps setting silences SQLAlchemy warnings about multiple relationship paths
    user = db.relationship("User", backref=db.backref("user_sections_rel", cascade="all, delete-orphan"), overlaps="sections")
    section = db.relationship("Section", backref=db.backref("section_users_rel", cascade="all, delete-orphan"), overlaps="users")
    
    def __init__(self, user, section):
        self.user = user
        self.section = section
        self.year = default_year()


class Section(db.Model):
    """
    Section Model
    
    The Section class represents a section within the application, such as a class, department or group.
    
    Attributes:
        id (db.Column): The primary key, an integer representing the unique identifier for the section.
        _name (db.Column): A string representing the name of the section. It is not unique and cannot be null.
        _abbreviation (db.Column): A unique string representing the abbreviation of the section's name. It cannot be null.
    """
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column(db.String(255), unique=False, nullable=False)
    _abbreviation = db.Column(db.String(255), unique=True, nullable=False)
  
    # Define many-to-many relationship with User model through UserSection table
    # Overlaps setting silences SQLAlchemy warnings about multiple relationship paths
    # No backref needed as User has its own 'sections' relationship
    users = db.relationship('User', secondary='user_sections', lazy='subquery',
                            overlaps="user_sections_rel,user,sections")    
    
    # Constructor
    def __init__(self, name, abbreviation):
        self._name = name 
        self._abbreviation = abbreviation
        
    @property
    def abbreviation(self):
        return self._abbreviation

    # String representation of the Classes object
    def __repr__(self):
        return f"Class(_id={self.id}, name={self._name}, abbreviation={self._abbreviation})"

    # CRUD create
    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    # CRUD read
    def read(self):
        return {
            "id": self.id,
            "name": self._name,
            "abbreviation": self._abbreviation
        }
        
    # CRUD delete: remove self
    # None
    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return None


class User(db.Model, UserMixin):
    """
    User Model

    This class represents the User model, which is used to manage actions in the 'users' table of the database. It is an
    implementation of Object Relational Mapping (ORM) using SQLAlchemy, allowing for easy interaction with the database
    using Python code. The User model includes various fields and methods to support user management, authentication,
    and profile management functionalities.

    Attributes:
        __tablename__ (str): Specifies the name of the table in the database.
        id (Column): The primary key, an integer representing the unique identifier for the user.
        _name (Column): A string representing the user's name. It is not unique and cannot be null.
        _uid (Column): A unique string identifier for the user, cannot be null.
        _email (Column): A string representing the user's email address. It is not unique and cannot be null.
        _password (Column): A string representing the hashed password of the user. It is not unique and cannot be null.
        _role (Column): A string representing the user's role within the application. Defaults to "User".
        _garden_sprite (Column): A string storing the emoji the user picked for the community garden.
                                 Nullable — users who have not visited the garden yet will have None here.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column(db.String(255), unique=False, nullable=False)
    _uid = db.Column(db.String(255), unique=True, nullable=False)
    _email = db.Column(db.String(255), unique=False, nullable=False)
    _password = db.Column(db.String(255), unique=False, nullable=False)
    _role = db.Column(db.String(20), default="User", nullable=False)
    # Garden sprite: stores the emoji the user chose on the community garden page.
    # Nullable so existing users are unaffected until they visit the garden.
    _garden_sprite = db.Column(db.String(10), unique=False, nullable=True, default=None)

    # Define many-to-many relationship with Section model through UserSection table
    # Overlaps setting silences SQLAlchemy warnings about multiple relationship paths
    # No backref needed as Section has its own 'users' relationship
    sections = db.relationship('Section', secondary='user_sections', lazy='subquery',
                               overlaps="user_sections_rel,section,users")
    
    # Define many-to-many relationship with Persona model through UserPersona table
    # Overlaps setting silences SQLAlchemy warnings about multiple relationship paths
    # No backref needed as Persona has its own 'users' relationship
    personas = db.relationship('Persona', secondary='user_personas', lazy='subquery',
                               overlaps="user_personas_rel,persona,users")
    
    def __init__(self, name, uid, password=app.config["DEFAULT_PASSWORD"], role="User", **kwargs):
        self._name = name
        self._uid = uid
        self._email = kwargs.get('email', '?') or '?'
        self.set_password(password)
        self._role = role
        self._garden_sprite = None  # Not set until the user visits the garden

    # UserMixin/Flask-Login requires a get_id method to return the id as a string
    def get_id(self):
        return str(self.id)

    # UserMixin/Flask-Login requires is_authenticated to be defined
    @property
    def is_authenticated(self):
        return True

    # UserMixin/Flask-Login requires is_active to be defined
    @property
    def is_active(self):
        return True

    # UserMixin/Flask-Login requires is_anonymous to be defined
    @property
    def is_anonymous(self):
        return False
    
    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        self._email = email if email else '?'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, uid):
        self._uid = uid

    def is_uid(self, uid):
        return self._uid == uid

    @property
    def password(self):
        return self._password[0:10] + "..."

    def set_password(self, password):
        """Set password: hash if not already hashed, else set directly."""
        if password and password.startswith("pbkdf2:sha256:"):
            self._password = password
        else:
            self._password = generate_password_hash(password, "pbkdf2:sha256", salt_length=10)            

    def is_password(self, password):
        """Check against hashed password."""
        return check_password_hash(self._password, password)

    def __str__(self):
        return json.dumps(self.read())

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, role):
        self._role = role

    def is_admin(self):
        return self._role == "Admin"

    def is_teacher(self):
        return self._role == "Teacher"

    # Garden sprite getter and setter
    @property
    def garden_sprite(self):
        return self._garden_sprite

    @garden_sprite.setter
    def garden_sprite(self, sprite):
        """Store the emoji string the user chose on the garden page."""
        self._garden_sprite = sprite

    # CRUD create
    def create(self, inputs=None):
        try:
            db.session.add(self)
            db.session.commit()
            if inputs:
                self.update(inputs)
            # Auto-assign a garden sprite if not already set
            if not self._garden_sprite:
                self._auto_assign_sprite()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def _auto_assign_sprite(self):
        """
        Automatically assign the least-used garden sprite to this user.
        Called during create() so every new user gets a sprite immediately.
        """
        from sqlalchemy import func
        used_counts = {sprite: 0 for sprite in GARDEN_SPRITES}
        results = db.session.query(User._garden_sprite, func.count(User._garden_sprite)) \
                            .filter(User._garden_sprite.isnot(None)) \
                            .group_by(User._garden_sprite).all()
        for sprite, count in results:
            if sprite in used_counts:
                used_counts[sprite] = count
        self._garden_sprite = min(used_counts, key=used_counts.get)
        db.session.commit()

    # CRUD read
    def read(self):
        data = {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_admin": self.is_admin(),
            "garden_sprite": self.garden_sprite,  # included so the garden page can fetch it
        }
        return data
        
    # CRUD update
    def update(self, inputs):
        if not isinstance(inputs, dict):
            return self

        if inputs.get("name"):
            self.name = inputs["name"]
        if inputs.get("uid"):
            self.set_uid(inputs["uid"])
        if inputs.get("email"):
            self.email = inputs["email"]
        if inputs.get("password"):
            self.set_password(inputs["password"])
        if inputs.get("role"):
            self._role = inputs["role"]
        # Accept garden_sprite updates — sent by the garden page after the user picks
        if inputs.get("garden_sprite") is not None:
            self.garden_sprite = inputs["garden_sprite"]

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None
        return self
    
    # CRUD delete
    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return None
    
    def save_pfp(self, image_data, filename):
        """For saving profile picture."""
        try:
            user_dir = os.path.join(app.config['UPLOAD_FOLDER'], self.uid)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            file_path = os.path.join(user_dir, filename)
            with open(file_path, 'wb') as img_file:
                img_file.write(image_data)
            self.update({"pfp": filename})
        except Exception as e:
            raise e
        
    def delete_pfp(self):
        """Deletes profile picture from user record."""
        self.pfp = None
        db.session.commit()
        
    def add_section(self, section):
        found = any(s.id == section.id for s in self.sections)
        if not found:
            user_section = UserSection(user=self, section=section)
            db.session.add(user_section)
            db.session.commit()
        else:
            print("Section with abbreviation '{}' exists.".format(section._abbreviation))
        if self.kasm_server_needed:
            KasmUser().post_groups(self.uid, [section.abbreviation])
        return self
    
    def add_sections(self, sections):
        for section in sections:
            section_obj = Section.query.filter_by(_abbreviation=section).first()
            if not section_obj:
                return None
            self.add_section(section_obj)
        return self
        
    def read_sections(self):
        """Reads the sections associated with the user."""
        sections = []
        if self.user_sections_rel:
            for user_section in self.user_sections_rel:
                section_data = user_section.section.read()
                section_data['year'] = user_section.year  
                sections.append(section_data)
        return {"sections": sections} 
    
    def read_personas(self):
        """Reads the personas associated with the user."""
        personas = []
        if hasattr(self, 'user_personas_rel') and self.user_personas_rel:
            for user_persona in self.user_personas_rel:
                personas.append(user_persona.read())
        return {"personas": personas}
    
    def update_section(self, section_data):
        abbreviation = section_data.get("abbreviation", None)
        year = int(section_data.get("year", default_year()))
        section = next(
            (s for s in self.user_sections_rel if s.section.abbreviation == abbreviation),
            None
        )
        if section:
            section.year = year
            db.session.commit()
            return True
        else:
            return False
    
    def remove_sections(self, section_abbreviations):
        try:
            for abbreviation in section_abbreviations:
                section = next((section for section in self.sections if section.abbreviation == abbreviation), None)
                if section:
                    self.sections.remove(section)
                else:
                    raise ValueError(f"Section with abbreviation '{abbreviation}' not found.")
            db.session.commit()
            return True
        except ValueError as e:
            db.session.rollback()
            print(e)
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Unexpected error removing sections: {e}")
            return False
        
    def set_uid(self, new_uid=None):
        old_uid = self._uid
        if new_uid and new_uid != self._uid:
            self._uid = new_uid
            db.session.commit()
        if old_uid != self._uid:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_uid)
            new_path = os.path.join(current_app.config['UPLOAD_FOLDER'], self._uid)
            if os.path.exists(old_path):
                os.rename(old_path, new_path)


""" Database Creation and Testing """

# Full sprite list matching the garden frontend
GARDEN_SPRITES = [
    '🌸','🌺','🌻','🌷','🌼','🦋','🐝','🐞','🐛','🦗',
    '🍀','🌿','🪴','🌱','🍃','🐢','🦔','🐇','🦜','🌙'
]

def initUsers():
    with app.app_context():
        db.create_all()

        # create() auto-assigns a sprite to each user via _auto_assign_sprite()
        u1 = User(name=app.config['ADMIN_USER'], uid=app.config['ADMIN_UID'], password=app.config['ADMIN_PASSWORD'], role="Admin")
        u2 = User(name=app.config['MY_NAME'], uid=app.config['MY_UID'], password=app.config['MY_PASSWORD'], role=app.config['MY_ROLE'])

        for user in [u1, u2]:
            try:
                user.create()
            except IntegrityError:
                db.session.remove()
                print(f"Records exist or duplicate: {user.uid}")

def assign_sprite(uid):
    """
    Assign the next available sprite to a user who does not yet have one.
    Called after a new user signs up and confirms their sprite on the garden page.
    If all sprites are taken, cycles back to the beginning.

    :param uid: The uid of the user to assign a sprite to.
    :return: The assigned sprite emoji string, or None if user not found.
    """
    with app.app_context():
        user = User.query.filter_by(_uid=uid).first()
        if not user:
            return None

        # If user already has a sprite, return it without overwriting
        if user._garden_sprite:
            return user._garden_sprite

        # Count how many users already have each sprite to find the least-used one
        # This distributes sprites evenly rather than always starting from index 0
        from sqlalchemy import func
        used_counts = {sprite: 0 for sprite in GARDEN_SPRITES}
        results = db.session.query(User._garden_sprite, func.count(User._garden_sprite)) \
                            .filter(User._garden_sprite.isnot(None)) \
                            .group_by(User._garden_sprite).all()
        for sprite, count in results:
            if sprite in used_counts:
                used_counts[sprite] = count

        # Pick the sprite with the lowest usage count
        chosen = min(used_counts, key=used_counts.get)
        user._garden_sprite = chosen
        db.session.commit()
        return chosen