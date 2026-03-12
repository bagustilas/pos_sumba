"""
POS SUMBA — Pengaturan Toko (Fitur #8)
"""
from flask import Blueprint, render_template, request, jsonify
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required
import requests as req

pengaturan_bp = Blueprint("pengaturan", __name__)

@pengaturan_bp.route("/pengaturan")
@admin_required
def index():
    sb       = get_supabase()
    raw      = sb.table("settings").select("key,value").execute().data or []
    settings = {s["key"]: s["value"] for s in raw}
    return render_template("pengaturan.html", settings=settings)

@pengaturan_bp.route("/api/pengaturan", methods=["POST"])
@admin_required
def api_save():
    data    = request.json
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    rows = [{"key": k, "value": v} for k, v in data.items()]
    res  = req.post(
        f"{SUPABASE_URL}/rest/v1/settings",
        headers=headers,
        json=rows
    )
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})
