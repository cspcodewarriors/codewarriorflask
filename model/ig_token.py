import os, requests, logging
from __init__ import app, db

TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'ig_token.txt')
REFRESH_URL = 'https://graph.instagram.com/refresh_access_token'


def read_token():
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ''


def write_token(token: str):
    with open(TOKEN_FILE, 'w') as f:
        f.write(token.strip())


def refresh_token():
    current = read_token()
    if not current:
        raise ValueError('No token stored — set one first via POST /api/ig/token')

    r = requests.get(REFRESH_URL, params={
        'grant_type': 'ig_refresh_token',
        'access_token': current,
    }, timeout=10)

    data = r.json()
    new_token = data.get('access_token')
    if not new_token:
        raise RuntimeError(f"Instagram refresh failed: {data}")

    write_token(new_token)
    logging.info('Instagram token refreshed. Expires in %s seconds.', data.get('expires_in'))
    return new_token, data.get('expires_in')


def initIgToken():
    """No table needed — token lives in a flat file. Called from main init for consistency."""
    if not os.path.exists(TOKEN_FILE):
        open(TOKEN_FILE, 'w').close()
        print("ig_token.txt created (empty — set token via POST /api/ig/token)")
    else:
        print("ig_token.txt ready.")

