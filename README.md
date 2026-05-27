# Soroptimist International of Poway — Flask Backend

This is the Flask backend server for the [Soroptimist International of Poway (SIP)](https://sipoway.opencodingsociety.com/) website, built and maintained by the CSP Code Warriors student team.

- **GitHub:** [cspcodewarriors/codewarriorflask](https://github.com/cspcodewarriors/codewarriorflask)
- **Live site:** [https://sipoway.opencodingsociety.com/](https://sipoway.opencodingsociety.com/)

## What This Project Does

- Serves REST APIs consumed by the SIP frontend (see the `api/` folder for all endpoints).
- Manages calendar events, volunteer/contact form submissions, and the SIP event blog.
- Handles user authentication with JWT cookies and role-based access control.
- Stores persistent data in SQLite (local) or a remote DB (production) via SQLAlchemy — see `model/` and `instance/volumes/`.
- Provides a minimal admin UI using Flask templates and Jinja2.
- Deployable via Docker, docker-compose, and Nginx as a WSGI server.

---

## API Reference

### Authentication & Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/authenticate` | Log in and receive a JWT cookie |
| GET | `/api/id` | Get the currently logged-in user |
| POST | `/api/user` | Create a new user account |
| PUT | `/api/user` | Update a user |
| DELETE | `/api/user` | Delete a user |

### SIP Events (Calendar)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/sip/events` | Public | List all calendar events |
| GET | `/api/sip/events/<id>` | Public | Get a single event |
| POST | `/api/sip/events` | Admin | Create a new event |
| PUT | `/api/sip/events/<id>` | Admin | Update an event |
| DELETE | `/api/sip/events/<id>` | Admin | Delete an event |

### SIP Contact & Volunteer Forms
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/sip/contact/involved` | Login | Submit a Get Involved form |
| POST | `/api/sip/contact/help` | Login | Submit a Get Help form |
| GET | `/api/sip/contact/pending` | Admin | List pending volunteer requests |
| GET | `/api/sip/contact` | Admin | List all submissions |
| GET | `/api/sip/contact/<id>` | Admin | Get a single submission |
| PATCH | `/api/sip/contact/<id>` | Admin | Update submission status |
| PATCH | `/api/sip/contact/<id>/approve` | Admin | Approve a volunteer request |
| PATCH | `/api/sip/contact/<id>/decline` | Admin | Decline a volunteer request |
| DELETE | `/api/sip/contact/<id>` | Admin | Hard-delete a submission |

### SIP Blog
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/blog` | Admin | Create a blog post (saved as draft by default) |
| GET | `/api/blog` | Public/Admin | Published posts (public); all posts including drafts (Admin) |
| PUT | `/api/blog` | Admin | Update an existing post |
| DELETE | `/api/blog` | Admin | Delete a post |
| POST | `/api/blog/image` | Admin | Upload an image for a blog post |


### AI & Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/gemini` | Chat with Gemini AI assistant |
| POST | `/api/groq` | Chat with Groq AI assistant |
| GET | `/api/jokes/` | Get a random joke |

---

## WebSocket — Real-time Garden

A separate Socket.IO server (`socket/socket_server.py`) runs on port **8500** and powers real-time community presence in the garden — broadcasting when users join so their sprites appear live for all visitors.

### Run the socket server

```bash
cd socket
python socket_server.py
```

### Events

**Client → Server**
| Event | Payload | Description |
|-------|---------|-------------|
| `player_join` | `{ name }` | Register a user entering the garden |

**Server → Client (broadcast)**
| Event | Payload | Description |
|-------|---------|-------------|
| `player_joined` | `{ name }` | Fires when a user joins — all connected clients update the garden |

### Allowed origins (CORS)
- `http://localhost:8000`
- `https://pages.opencodingsociety.com`

---

## Database Management Workflow

Follow this procedure when you need to update the schema or sync data between local and production. Steps 1, 2, 3, and 5 run on your **local** machine. Step 4 runs on the **production server** (via Cockpit).

> Before starting, make sure `ADMIN_PASSWORD` is set in your `.env` and your `venv` is active.

### Full Workflow

**1. Initialize your local DB** with clean seed data (good for testing schema changes):
```bash
python scripts/db_init.py
```

**2. Pull production data to local** so you can test with real data:
```bash
python scripts/db_migrate-prod2sqlite.py
```

**3. Test your changes locally.** Make sure everything works before touching production.

**4. On the production server** (in Cockpit, inside the `flask` directory):
```bash
# Back up the current DB
cp instance/volumes/sqlite.db instance/volumes/backups/sqlite_YYYY-MM-DD.db

# Pull latest code
git pull

# Update schema to match latest code
python scripts/db_init.py
```

**5. Push your local DB to production** (update `.env` with the production `ADMIN_PASSWORD` first):
```bash
python scripts/db_restore-sqlite2prod.py
```

### Quick Reference
| Step | Command | Where |
|------|---------|--------|
| Init local DB | `python scripts/db_init.py` | Local |
| Pull prod → local | `python scripts/db_migrate-prod2sqlite.py` | Local |
| Test | — | Local |
| Backup + pull + init | see above | Production (Cockpit) |
| Push local → prod | `python scripts/db_restore-sqlite2prod.py` | Local |



## Implementation History

> Soroptimist International of Poway features added by CSP Code Warriors.

- SIP calendar events API (`/api/sip/events`) with Admin-only create/update/delete
- SIP contact and volunteer form APIs (`/api/sip/contact`) with Admin approval workflow
- SIP event blog API (`/api/blog`) with draft/publish support and image uploads
- Notification system for volunteer approval status updates

## DO NOT FORK THIS REPOSITORY!

To future students picking this project up, please make a *new* repository by using this repo as a template. Do not make a fork.
