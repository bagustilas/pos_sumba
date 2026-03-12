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
        "Prefer": "return=representation",
    }

    errors = []
    for k, v in data.items():
        # PATCH per key — paling aman karena row sudah pasti ada
        res = req.patch(
            f"{SUPABASE_URL}/rest/v1/settings?key=eq.{k}",
            headers=headers,
            json={"value": str(v), "updated_at": "now()"},
        )
        if not res.ok:
            # Jika row belum ada, INSERT
            res2 = req.post(
                f"{SUPABASE_URL}/rest/v1/settings",
                headers={**headers, "Prefer": "return=representation"},
                json={"key": k, "value": str(v)},
            )
            if not res2.ok:
                errors.append(f"{k}: {res2.text}")

    if errors:
        return jsonify({"error": "; ".join(errors)}), 500
    return jsonify({"success": True})