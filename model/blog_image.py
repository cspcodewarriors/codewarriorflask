"""
Blog Image Helpers — mirrors model/pfp.py pattern.

Images are stored at:
  UPLOAD_FOLDER/blog/<post_id>/<filename>

Each post can hold multiple images.  The filename encodes both the
post-id and a uuid so concurrent uploads never collide.
"""

import base64
import os
import uuid

from werkzeug.utils import secure_filename
from __init__ import app


# ── helpers ────────────────────────────────────────────────────────────────────

def _post_dir(post_id: str) -> str:
    """Return (and create) the upload directory for a given post."""
    folder = os.path.join(app.config['UPLOAD_FOLDER'], 'blog', str(post_id))
    os.makedirs(folder, exist_ok=True)
    return folder


# ── public API ─────────────────────────────────────────────────────────────────

def blog_image_upload(base64_image: str, post_id: str) -> str | None:
    """
    Decode a base64 image string and persist it under the blog post directory.

    Parameters
    ----------
    base64_image : str
        Raw base64 string (no data-URI prefix needed, but tolerates it).
    post_id : str
        The blog post this image belongs to.

    Returns
    -------
    str | None
        The saved filename on success, None on failure.
    """
    try:
        # Strip optional data-URI prefix ("data:image/png;base64,…")
        if ',' in base64_image:
            base64_image = base64_image.split(',', 1)[1]

        image_data = base64.b64decode(base64_image)
        filename   = secure_filename(f'{post_id}_{uuid.uuid4().hex}.png')
        file_path  = os.path.join(_post_dir(post_id), filename)

        with open(file_path, 'wb') as f:
            f.write(image_data)

        return filename
    except Exception as e:
        print(f'blog_image_upload error: {e}')
        return None


def blog_image_decode(post_id: str, filename: str) -> str | None:
    """
    Read an image from disk and return it as a base64 string.

    Parameters
    ----------
    post_id : str
        The blog post the image belongs to.
    filename : str
        The filename previously returned by blog_image_upload.

    Returns
    -------
    str | None
        Base64 encoded image string, or None on failure.
    """
    try:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], 'blog', str(post_id), filename)
        with open(img_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f'blog_image_decode error: {e}')
        return None


def blog_image_delete(post_id: str, filename: str) -> bool:
    """
    Delete a single image file from disk.

    Returns True when the file no longer exists (idempotent), False on error.
    """
    try:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], 'blog', str(post_id), filename)
        if os.path.exists(img_path):
            os.remove(img_path)
        return True
    except Exception as e:
        print(f'blog_image_delete error: {e}')
        return False


def blog_images_delete_all(post_id: str) -> bool:
    """
    Delete every image file for a post (called when the post itself is deleted).

    Returns True on success or if the directory did not exist.
    """
    import shutil
    try:
        post_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'blog', str(post_id))
        if os.path.isdir(post_dir):
            shutil.rmtree(post_dir)
        return True
    except Exception as e:
        print(f'blog_images_delete_all error: {e}')
        return False


def blog_images_list(post_id: str) -> list[str]:
    """
    Return every filename stored for a post, sorted by mtime (oldest first).
    """
    try:
        post_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'blog', str(post_id))
        if not os.path.isdir(post_dir):
            return []
        files = os.listdir(post_dir)
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(post_dir, fn)))
        return files
    except Exception as e:
        print(f'blog_images_list error: {e}')
        return []