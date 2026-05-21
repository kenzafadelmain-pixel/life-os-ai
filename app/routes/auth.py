"""Authentication: register, login, logout."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.core import get_db
from app.models.user import UserRepository

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        errors = []
        if len(name) < 2:
            errors.append("Please enter your name.")
        if "@" not in email or "." not in email:
            errors.append("That doesn't look like a valid email.")
        if len(password) < 8:
            errors.append("Passwords must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords don't match.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", name=name, email=email)

        repo = UserRepository(get_db())
        try:
            user = repo.create(name, email, password)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("auth/register.html", name=name, email=email)

        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(f"Welcome to LIFE OS, {user.name.split()[0]} ✨", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        repo = UserRepository(get_db())
        user = repo.verify_password(email, password)
        if not user:
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", email=email)

        session.permanent = True
        session["user_id"] = user.id
        session["user_name"] = user.name
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Signed out. See you soon.", "info")
    return redirect(url_for("main.landing"))
