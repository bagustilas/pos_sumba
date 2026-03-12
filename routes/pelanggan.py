"""
POS SUMBA — Pelanggan & Loyalty Points (Fase 3)
"""
from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required, login_required
import requests as req
import uuid

pelanggan_bp = Blueprint("pelanggan", __name__)

# ── HALAMAN ────────────────────────────────────────────────────
@pelanggan_bp.route("/pelanggan")
@admin_required
def index():
    return render_template("pelanggan.html")

# ── LIST PELANGGAN ─────────────────────────────────────────────
@pelanggan_bp.route("/api/pelanggan")
@login_required
def api_list():
    sb       = get_supabase()
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    search   = request.args.get("search", "").strip()
    offset   = (page - 1) * per_page

    q = sb.table("customers").select(
        "id,name,phone,email,points,points_total,member_code,total_purchase,is_active,created_at",
        count="exact"
    ).eq("is_active", True)

    if search:
        q = q.ilike("name", f"%{search}%")

    result = q.order("total_purchase", desc=True).range(offset, offset + per_page - 1).execute()

    return jsonify({
        "data":       result.data or [],
        "total":      result.count or 0,
        "total_page": max(1, -(-( result.count or 0) // per_page)),
    })

@pelanggan_bp.route("/api/pelanggan/cari")
@login_required
def api_cari():
    """Cari pelanggan untuk kasir (by name/phone/member_code)"""
    sb     = get_supabase()
    q      = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    # Cari by nama
    by_name   = sb.table("customers").select("id,name,phone,points,member_code").ilike("name", f"%{q}%").limit(5).execute().data or []
    # Cari by phone
    by_phone  = sb.table("customers").select("id,name,phone,points,member_code").ilike("phone", f"%{q}%").limit(5).execute().data or []
    # Cari by member_code
    by_member = sb.table("customers").select("id,name,phone,points,member_code").ilike("member_code", f"%{q}%").limit(5).execute().data or []

    seen = {}
    for c in by_name + by_phone + by_member:
        seen[c["id"]] = c
    return jsonify(list(seen.values())[:10])

# ── CRUD PELANGGAN ─────────────────────────────────────────────
@pelanggan_bp.route("/api/pelanggan", methods=["POST"])
@login_required
def api_create():
    data    = request.json
    name    = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Nama pelanggan wajib diisi"}), 400

    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    # Auto generate member_code
    sb      = get_supabase()
    count   = sb.table("customers").select("id", count="exact").execute().count or 0
    member_code = f"MBR-{str(count + 1).zfill(5)}"

    res = req.post(f"{SUPABASE_URL}/rest/v1/customers", headers=headers, json={
        "name":        name,
        "phone":       data.get("phone", ""),
        "email":       data.get("email", ""),
        "address":     data.get("address", ""),
        "notes":       data.get("notes", ""),
        "member_code": member_code,
        "points":      0,
        "points_total":0,
        "is_active":   True,
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True, "data": res.json()[0]})

@pelanggan_bp.route("/api/pelanggan/<uid>", methods=["PATCH"])
@admin_required
def api_update(uid):
    data    = request.json
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    allowed = ["name","phone","email","address","notes","is_active"]
    payload = {k: v for k, v in data.items() if k in allowed}
    if not payload:
        return jsonify({"error": "Tidak ada data"}), 400
    res = req.patch(f"{SUPABASE_URL}/rest/v1/customers?id=eq.{uid}", headers=headers, json=payload)
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

@pelanggan_bp.route("/api/pelanggan/<uid>", methods=["DELETE"])
@admin_required
def api_delete(uid):
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
    res = req.patch(f"{SUPABASE_URL}/rest/v1/customers?id=eq.{uid}",
                    headers={**headers,"Content-Type":"application/json","Prefer":"return=representation"},
                    json={"is_active": False})
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})

# ── POIN HISTORY ───────────────────────────────────────────────
@pelanggan_bp.route("/api/pelanggan/<uid>/poin")
@login_required
def api_poin(uid):
    sb     = get_supabase()
    result = sb.table("point_history").select("*").eq("customer_id", uid).order("created_at", desc=True).limit(30).execute()
    return jsonify(result.data or [])

@pelanggan_bp.route("/api/pelanggan/<uid>/poin/adjust", methods=["POST"])
@admin_required
def api_adjust_poin(uid):
    data   = request.json
    pts    = int(data.get("points", 0))
    note   = data.get("note", "Penyesuaian manual")
    sb     = get_supabase()

    cust = sb.table("customers").select("points").eq("id", uid).execute().data
    if not cust:
        return jsonify({"error": "Pelanggan tidak ditemukan"}), 404

    old_pts    = cust[0]["points"] or 0
    new_pts    = max(0, old_pts + pts)
    headers    = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}

    req.patch(f"{SUPABASE_URL}/rest/v1/customers?id=eq.{uid}", headers=headers,
              json={"points": new_pts, "updated_at": "now()"})
    req.post(f"{SUPABASE_URL}/rest/v1/point_history", headers=headers, json={
        "customer_id":  uid,
        "type":         "adjust",
        "points":       pts,
        "balance_after":new_pts,
        "note":         note,
    })
    return jsonify({"success": True, "new_points": new_pts})
