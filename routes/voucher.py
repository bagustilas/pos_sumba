"""
POS SUMBA — Voucher & Promo (Fase 3)
"""
from flask import Blueprint, render_template, request, jsonify
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required, login_required
import requests as req
from datetime import date

voucher_bp = Blueprint("voucher", __name__)

@voucher_bp.route("/voucher")
@admin_required
def index():
    return render_template("voucher.html")

@voucher_bp.route("/api/voucher")
@admin_required
def api_list():
    sb     = get_supabase()
    result = sb.table("vouchers").select("*").order("created_at", desc=True).execute()
    today  = date.today().isoformat()
    rows   = []
    for v in (result.data or []):
        status = "active"
        if not v.get("is_active"):
            status = "inactive"
        elif v.get("valid_until") and v["valid_until"] < today:
            status = "expired"
        elif v.get("max_use") and v["max_use"] > 0 and v.get("used_count", 0) >= v["max_use"]:
            status = "habis"
        v["status"] = status
        rows.append(v)
    return jsonify(rows)

@voucher_bp.route("/api/voucher/cek", methods=["POST"])
@login_required
def api_cek():
    """Validasi kode voucher dari kasir"""
    data      = request.json
    code      = data.get("code", "").strip().upper()
    subtotal  = float(data.get("subtotal", 0))
    today     = date.today().isoformat()

    if not code:
        return jsonify({"error": "Kode voucher kosong"}), 400

    sb     = get_supabase()
    result = sb.table("vouchers").select("*").eq("code", code).eq("is_active", True).execute().data
    if not result:
        return jsonify({"error": "Kode voucher tidak valid"}), 404

    v = result[0]
    if v.get("valid_from") and v["valid_from"] > today:
        return jsonify({"error": "Voucher belum berlaku"}), 400
    if v.get("valid_until") and v["valid_until"] < today:
        return jsonify({"error": "Voucher sudah kadaluarsa"}), 400
    if v.get("max_use") and v["max_use"] > 0 and v.get("used_count", 0) >= v["max_use"]:
        return jsonify({"error": "Voucher sudah habis digunakan"}), 400
    if v.get("min_purchase") and subtotal < float(v["min_purchase"]):
        return jsonify({"error": f"Minimal pembelian Rp {int(v['min_purchase']):,} untuk voucher ini"}), 400

    # Hitung diskon
    disc = float(v["value"]) if v["type"] == "nominal" else subtotal * float(v["value"]) / 100
    disc = min(disc, subtotal)

    return jsonify({
        "valid":    True,
        "voucher":  v,
        "discount": disc,
    })

@voucher_bp.route("/api/voucher", methods=["POST"])
@admin_required
def api_create():
    data    = request.json
    code    = data.get("code", "").strip().upper()
    name    = data.get("name", "").strip()
    if not code or not name:
        return jsonify({"error": "Kode dan nama wajib diisi"}), 400

    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    res = req.post(f"{SUPABASE_URL}/rest/v1/vouchers", headers=headers, json={
        "code":         code,
        "name":         name,
        "type":         data.get("type", "pct"),
        "value":        float(data.get("value", 0)),
        "min_purchase": float(data.get("min_purchase", 0)),
        "max_use":      int(data.get("max_use", 0)),
        "valid_from":   data.get("valid_from") or None,
        "valid_until":  data.get("valid_until") or None,
        "is_active":    True,
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

@voucher_bp.route("/api/voucher/<int:vid>", methods=["PATCH"])
@admin_required
def api_update(vid):
    data    = request.json
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    allowed = ["name","type","value","min_purchase","max_use","valid_from","valid_until","is_active"]
    payload = {k: v for k, v in data.items() if k in allowed}
    res     = req.patch(f"{SUPABASE_URL}/rest/v1/vouchers?id=eq.{vid}", headers=headers, json=payload)
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

@voucher_bp.route("/api/voucher/<int:vid>", methods=["DELETE"])
@admin_required
def api_delete(vid):
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    res = req.patch(f"{SUPABASE_URL}/rest/v1/vouchers?id=eq.{vid}", headers=headers, json={"is_active": False})
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})
