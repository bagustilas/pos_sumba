"""
POS SUMBA — Manajemen User Kasir (Fitur #7)
"""
from flask import Blueprint, render_template, request, jsonify
from utils.supabase_client import get_supabase, hash_password, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required
import requests as req
import uuid

pengguna_bp = Blueprint("pengguna", __name__)

@pengguna_bp.route("/pengguna")
@admin_required
def index():
    sb    = get_supabase()
    roles = sb.table("roles").select("id,name").execute().data or []
    return render_template("pengguna.html", roles=roles)

@pengguna_bp.route("/api/pengguna")
@admin_required
def api_list():
    sb     = get_supabase()
    result = sb.table("users").select(
        "id,name,email,is_active,last_login,created_at,roles(name)"
    ).order("created_at", desc=True).execute()

    rows = []
    for u in (result.data or []):
        rows.append({
            "id":         u["id"],
            "name":       u["name"],
            "email":      u["email"],
            "role":       u["roles"]["name"] if u.get("roles") else "-",
            "is_active":  u.get("is_active", True),
            "last_login": u.get("last_login", ""),
            "created_at": u.get("created_at", ""),
        })
    return jsonify(rows)

@pengguna_bp.route("/api/pengguna", methods=["POST"])
@admin_required
def api_create():
    data  = request.json
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    pw    = data.get("password", "").strip()
    role_id = data.get("role_id")

    if not all([name, email, pw, role_id]):
        return jsonify({"error": "Semua field wajib diisi"}), 400

    sb = get_supabase()
    # Cek email sudah ada
    existing = sb.table("users").select("id").eq("email", email).execute().data
    if existing:
        return jsonify({"error": "Email sudah terdaftar"}), 400

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    res = req.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json={
        "name":          name,
        "email":         email,
        "password_hash": hash_password(pw),
        "role_id":       int(role_id),
        "is_active":     True,
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

@pengguna_bp.route("/api/pengguna/<uid>", methods=["PATCH"])
@admin_required
def api_update(uid):
    data    = request.json
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    payload = {}
    if "name"      in data: payload["name"]      = data["name"]
    if "role_id"   in data: payload["role_id"]   = int(data["role_id"])
    if "is_active" in data: payload["is_active"] = data["is_active"]
    if "password"  in data and data["password"]:
        payload["password_hash"] = hash_password(data["password"])

    if not payload:
        return jsonify({"error": "Tidak ada perubahan"}), 400

    res = req.patch(
        f"{SUPABASE_URL}/rest/v1/users?id=eq.{uid}",
        headers=headers, json=payload
    )
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

@pengguna_bp.route("/api/pengguna/<uid>", methods=["DELETE"])
@admin_required
def api_delete(uid):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    res = req.delete(
        f"{SUPABASE_URL}/rest/v1/users?id=eq.{uid}",
        headers=headers
    )
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})
