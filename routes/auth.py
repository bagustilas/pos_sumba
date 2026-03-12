from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils.supabase_client import get_supabase, hash_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
@auth_bp.route("/login", methods=["GET"])
def login():
    if "user" in session:
        # Kasir langsung ke halaman kasir, admin ke dashboard
        role = session["user"].get("role", "kasir")
        if role in ("admin", "manajer"):
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("kasir.index"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Email dan password harus diisi.", "error")
        return render_template("login.html")

    try:
        sb  = get_supabase()
        res = (
            sb.table("users")
            .select("id,name,email,role_id,roles(name)")
            .eq("email", email)
            .eq("password_hash", hash_password(password))
            .eq("is_active", True)
            .single()
            .execute()
        )

        user = res.data
        if not user:
            flash("Email atau password salah.", "error")
            return render_template("login.html")

        sb.table("users").update({"last_login": "now()"}).eq("id", user["id"]).execute()

        role_name = "kasir"
        if isinstance(user.get("roles"), dict):
            role_name = user["roles"].get("name", "kasir")

        session["user"] = {
            "id":    user["id"],
            "name":  user["name"],
            "email": user["email"],
            "role":  role_name,
        }

        # Redirect berdasarkan role
        if role_name in ("admin", "manajer"):
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("kasir.index"))

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        flash("Email atau password salah.", "error")
        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))