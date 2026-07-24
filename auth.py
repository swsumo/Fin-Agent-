from functools import wraps

from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

import database


def signup(email, password):
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, "Enter a valid email address."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."
    if database.get_user_by_email(email):
        return None, "An account with this email already exists."

    user_id = database.create_user(email, generate_password_hash(password))
    session["user_id"] = user_id
    return user_id, None


def login(email, password):
    email = email.strip().lower()
    user = database.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return None, "Invalid email or password."

    session["user_id"] = user["id"]
    return user["id"], None


def logout():
    session.pop("user_id", None)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return database.get_user_by_id(user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return view_func(*args, **kwargs)
    return wrapped
