# imports from flask
from urllib.parse import urljoin, urlparse
from flask import abort, redirect, render_template, request, send_from_directory, url_for, jsonify, current_app, g
from flask_login import current_user, login_user, logout_user
from flask.cli import AppGroup
from flask_login import current_user, login_required
from flask import current_app
from flask_socketio import SocketIO, send # I'm trying to implement websockets myself, wish me luck - West
from dotenv import load_dotenv

# import "objects" from "this" project
from __init__ import app, db, login_manager  # Key Flask objects
socketio = SocketIO(app, cors_allowed_origins="*") # Putting this in here, hopefully GitHub doesn't explode
# API endpoints
from api.user import user_api 
from api.python_exec_api import python_exec_api
from api.javascript_exec_api import javascript_exec_api
from api.section import section_api
from api.persona_api import persona_api
from api.pfp import pfp_api
from api.analytics import analytics_api
from api.student import student_api
from api.groq_api import groq_api
from api.gemini_api import gemini_api
from api.microblog_api import microblog_api
from api.classroom_api import classroom_api
from api.data_export_import_api import data_export_import_api
from hacks.joke import joke_api
from api.post import post_api
from api.sip_events_api import sip_events_api
from api.blog import blog_api
from api.blog_image import blog_image_api
from api.contact import sip_contact_api
from api.sip_contact_approval import sip_approval_api
#from api.announcement import announcement_api ##temporary revert

# database Initialization functions
from model.user import User, initUsers
from model.user import Section
from model.kasm import KasmUtils
from model.github import GitHubUser
from model.feedback import Feedback
from api.analytics import get_date_range
from api.study import study_api
from api.feedback_api import feedback_api
from model.study import Study, initStudies
from model.classroom import Classroom
from model.persona import Persona, initPersonas, initPersonaUsers
from model.post import Post, init_posts
from model.microblog import MicroBlog, Topic, initMicroblogs
from model.sip_event import SipEvent, initSipEvents
from hacks.jokes import initJokes

import os

# Load environment variables
load_dotenv()

# register URIs for api endpoints
app.register_blueprint(blog_api)
app.register_blueprint(python_exec_api)
app.register_blueprint(javascript_exec_api)
app.register_blueprint(user_api)
app.register_blueprint(section_api)
app.register_blueprint(persona_api)
app.register_blueprint(pfp_api) 
app.register_blueprint(groq_api)
app.register_blueprint(gemini_api)
app.register_blueprint(microblog_api)
app.register_blueprint(analytics_api)
app.register_blueprint(student_api)
app.register_blueprint(study_api)
app.register_blueprint(classroom_api)
app.register_blueprint(feedback_api)
app.register_blueprint(data_export_import_api)  # Register the data export/import API
app.register_blueprint(joke_api)  # Register the joke API blueprint
app.register_blueprint(post_api)  # Register the social media post API
app.register_blueprint(sip_events_api)  # Register the SIP calendar events API
app.register_blueprint(blog_image_api)
app.register_blueprint(sip_contact_api)  # Register the SIP contact form API
app.register_blueprint(sip_approval_api)
# app.register_blueprint(announcement_api) ##temporary revert

# Jokes file initialization
with app.app_context():
    initJokes()
    initSipEvents()

# Tell Flask-Login the view function name of your login route
login_manager.login_view = "login"

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect(url_for('login', next=request.path))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Helper function to check if the URL is safe for redirects
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next', '') or request.form.get('next', '')
    if request.method == 'POST':
        user = User.query.filter_by(_uid=request.form['username']).first()
        if user and user.is_password(request.form['password']):
            login_user(user)
            if not is_safe_url(next_page):
                return abort(400)
            return redirect(next_page or url_for('index'))
        else:
            error = 'Invalid username or password.'
    return render_template("login.html", error=error, next=next_page)

@app.route('/studytracker')
def studytracker():
    return render_template("studytracker.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    print("Home:", current_user)
    return render_template("index.html")

@app.route('/blog/table')
@login_required
def blog_table():
    if current_user.role != 'Admin':
        return redirect(url_for('index'))
    return render_template("blog_table.html")

@app.route('/users/table2')
@login_required
def u2table():
    users = User.query.all()
    return render_template("u2table.html", user_data=users)

@app.route('/sections/')
@login_required
def sections():
    sections = Section.query.all()
    return render_template("sections.html", sections=sections)

@app.route('/persona/')
@login_required
def persona():
    personas = Persona.query.all()
    return render_template("persona.html", personas=personas)

@app.route('/kasm/users')
@login_required
def kasm_users():
    config, error = KasmUtils.get_authenticated_config()
    if error:
        users = []
    else:
        users, error = KasmUtils.get_users(config)
        if error:
            users = []
        else:
            users = users or []
    return render_template("kasm_users.html", users=users)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.delete()
        return jsonify({'message': 'User deleted successfully'}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.update({"password": app.config['DEFAULT_PASSWORD']}):
        return jsonify({'message': 'Password reset successfully'}), 200
    return jsonify({'error': 'Password reset failed'}), 500

@app.route('/update_user/<string:uid>', methods=['PUT'])
def update_user(uid):
    if current_user.role != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    print(f"Request Data: {data}")

    user = User.query.filter_by(_uid=uid).first()
    if user:
        print(f"Found user: {user.uid}")
        user.update(data)
        return jsonify({"message": "User updated successfully."}), 200
    else:
        print("User not found.")
        return jsonify({"message": "User not found."}), 404

# Create an AppGroup for custom commands
custom_cli = AppGroup('custom', help='Custom commands')

@custom_cli.command('generate_data')
def generate_data():
    initUsers()
    initMicroblogs()
    initPersonas()
    initPersonaUsers()

app.cli.add_command(custom_cli)

@socketio.on('message') # websocket event handler for 'message' events
def handle_message(msg):
    print("Message:", msg)
    send(msg, broadcast=True)  # send to all clients

# this runs the flask application on the development server
if __name__ == "__main__":
    host = "0.0.0.0"
    port = app.config['FLASK_PORT']
    print(f"** Server running: http://localhost:{port}")
    socketio.run(app, debug=True, host=host, port=port, use_reloader=False)