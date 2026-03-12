"""
POS SUMBA — Shift Kasir (Fase 2 #15)
"""
from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import login_required
import requests as req
from datetime import datetime, timezone, timedelta

shift_bp = Blueprint("shift", __name__)
WITA = timezone(timedelta(hours=8))

@shift_bp.route("/api/shift/status")
@login_required
def status():
    sb      = get_supabase()
    cashier = session["user"]["id"]
    result  = sb.table("shifts").select("*").eq("cashier_id", cashier).eq("status", "open").order("opened_at", desc=True).execute()
    shift   = result.data[0] if result.data else None
    return jsonify({"shift": shift})

@shift_bp.route("/api/shift/buka", methods=["POST"])
@login_required
def buka_shift():
    data         = request.json
    opening_cash = float(data.get("opening_cash", 0))
    cashier      = session["user"]["id"]
    sb           = get_supabase()

    # Cek apakah sudah ada shift open
    existing = sb.table("shifts").select("id").eq("cashier_id", cashier).eq("status", "open").execute().data
    if existing:
        return jsonify({"error": "Shift sudah terbuka"}), 400

    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    res = req.post(f"{SUPABASE_URL}/rest/v1/shifts", headers=headers, json={
        "cashier_id":   cashier,
        "opening_cash": opening_cash,
        "status":       "open",
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True, "shift": res.json()[0]})

@shift_bp.route("/api/shift/tutup", methods=["POST"])
@login_required
def tutup_shift():
    data         = request.json
    shift_id     = data.get("shift_id")
    closing_cash = float(data.get("closing_cash", 0))
    note         = data.get("note", "")

    # Hitung total penjualan di shift ini
    sb     = get_supabase()
    txs    = sb.table("transactions").select("total").eq("shift_id", shift_id).eq("status","completed").execute().data or []
    total_sales = sum(float(t["total"]) for t in txs)

    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    res = req.patch(f"{SUPABASE_URL}/rest/v1/shifts?id=eq.{shift_id}", headers=headers, json={
        "status":       "closed",
        "closed_at":    datetime.now(WITA).isoformat(),
        "closing_cash": closing_cash,
        "total_sales":  total_sales,
        "total_tx":     len(txs),
        "note":         note,
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True, "total_sales": total_sales, "total_tx": len(txs)})

@shift_bp.route("/api/shift/riwayat")
@login_required
def riwayat():
    sb     = get_supabase()
    result = sb.table("shifts").select(
        "id,opening_cash,closing_cash,total_sales,total_tx,status,opened_at,closed_at,note,users(name)"
    ).order("opened_at", desc=True).limit(30).execute()

    rows = []
    for s in (result.data or []):
        rows.append({
            "id":           s["id"],
            "kasir":        s["users"]["name"] if s.get("users") else "-",
            "opening_cash": float(s.get("opening_cash",0)),
            "closing_cash": float(s.get("closing_cash",0)),
            "total_sales":  float(s.get("total_sales",0)),
            "total_tx":     s.get("total_tx",0),
            "status":       s.get("status",""),
            "opened_at":    s.get("opened_at",""),
            "closed_at":    s.get("closed_at",""),
            "note":         s.get("note",""),
        })
    return jsonify(rows)

@shift_bp.route("/shift")
@login_required
def index():
    return render_template("shift.html")
