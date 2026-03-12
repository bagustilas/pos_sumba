"""
Helper untuk role-based access control (RBAC)
POS SUMBA V.1
"""
from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Hanya admin yang boleh akses"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        if session["user"].get("role") not in ("admin", "manajer"):
            flash("Akses ditolak. Halaman ini hanya untuk Administrator.", "error")
            return redirect(url_for("kasir.index"))
        return f(*args, **kwargs)
    return decorated


def is_admin():
    """Cek apakah user yang login adalah admin/manajer"""
    return session.get("user", {}).get("role") in ("admin", "manajer")


def get_role():
    return session.get("user", {}).get("role", "kasir")