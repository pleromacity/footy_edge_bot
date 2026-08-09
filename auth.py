"""
Single shared-passcode auth for the web dashboard.

This is a personal-use lock, not multi-user auth: one passcode, set via the
APP_PASSCODE environment variable, gets you a session cookie that unlocks
every page for ~30 days. There's no username, no per-user accounts, no
password reset flow -- if you lose the passcode, set a new one in Render's
environment variables and redeploy.

If APP_PASSCODE isn't set (e.g. running locally without bothering with it),
auth is skipped entirely so local/LAN use is unaffected.
"""

import hmac
import os
from datetime import timedelta
from functools import wraps

from flask import request, session, redirect, url_for

APP_PASSCODE = os.environ.get("APP_PASSCODE")
SESSION_LIFETIME = timedelta(days=30)


def auth_enabled() -> bool:
    return bool(APP_PASSCODE)


def is_logged_in() -> bool:
    if not auth_enabled():
        return True
    return session.get("authed") is True


def check_passcode(candidate: str) -> bool:
    if not candidate:
        return False
    return hmac.compare_digest(candidate, APP_PASSCODE)


def log_in():
    session.permanent = True
    session["authed"] = True


def log_out():
    session.pop("authed", None)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped
