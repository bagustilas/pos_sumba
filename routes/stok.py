"""
POS SUMBA — Manajemen Stok (Fase 2 #11)
Stok masuk, opname, riwayat perubahan stok
"""
from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required, login_required
import requests as req

stok_bp = Blueprint("stok", __name__)

@stok_bp.route("/stok")
@admin_required
def index():
    sb        = get_supabase()
    suppliers = sb.table("suppliers").select("id,name").eq("is_active", True).order("name").execute().data or []
    return render_template("stok.html", suppliers=suppliers)

# ── API STOK MASUK ────────────────────────────────────────────
@stok_bp.route("/api/stok/masuk", methods=["POST"])
@admin_required
def stok_masuk():
    data       = request.json
    items      = data.get("items", [])
    supplier_id= data.get("supplier_id")
    note       = data.get("note", "")

    if not items:
        return jsonify({"error": "Tidak ada item"}), 400

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    total = sum(float(i["qty"]) * float(i["cost_price"]) for i in items)

    # Buat record stock_in
    si_res = req.post(f"{SUPABASE_URL}/rest/v1/stock_in", headers=headers, json={
        "supplier_id": int(supplier_id) if supplier_id else None,
        "cashier_id":  session["user"]["id"],
        "total":       total,
        "note":        note,
    })
    if not si_res.ok:
        return jsonify({"error": si_res.text}), 500

    si = si_res.json()[0]

    # Insert items & update stok produk
    for item in items:
        qty = int(item["qty"])
        pid = item["product_id"]

        req.post(f"{SUPABASE_URL}/rest/v1/stock_in_items", headers=headers, json={
            "stock_in_id":  si["id"],
            "product_id":   pid,
            "product_name": item["product_name"],
            "qty":          qty,
            "cost_price":   float(item["cost_price"]),
            "subtotal":     qty * float(item["cost_price"]),
        })

        # Update stok produk
        sb = get_supabase()
        prod = sb.table("products").select("stock").eq("id", pid).execute().data
        if prod:
            new_stock = (prod[0]["stock"] or 0) + qty
            req.patch(
                f"{SUPABASE_URL}/rest/v1/products?id=eq.{pid}",
                headers=headers,
                json={"stock": new_stock, "updated_at": "now()"}
            )
            # Catat di stock_history
            req.post(f"{SUPABASE_URL}/rest/v1/stock_history", headers=headers, json={
                "product_id":   pid,
                "user_id":      session["user"]["id"],
                "type":         "in",
                "quantity":     qty,
                "stock_before": prod[0]["stock"] or 0,
                "stock_after":  new_stock,
                "note":         f"Stok masuk - {note or 'manual'}",
            })

    return jsonify({"success": True, "stock_in_id": si["id"]})

@stok_bp.route("/api/stok/riwayat")
@admin_required
def riwayat():
    sb      = get_supabase()
    page    = int(request.args.get("page", 1))
    per_page= 20
    offset  = (page-1)*per_page
    search  = request.args.get("search","").strip()

    q = sb.table("stock_history").select(
        "id,type,quantity,stock_before,stock_after,note,created_at,products(name,unit),users(name)",
        count="exact"
    ).order("created_at", desc=True)

    if search:
        q = q.ilike("note", f"%{search}%")

    result = q.range(offset, offset+per_page-1).execute()

    rows = []
    for r in (result.data or []):
        rows.append({
            "id":           r["id"],
            "type":         r["type"],
            "quantity":     r["quantity"],
            "stock_before": r["stock_before"],
            "stock_after":  r["stock_after"],
            "note":         r.get("note",""),
            "created_at":   r.get("created_at",""),
            "product":      r["products"]["name"] if r.get("products") else "-",
            "unit":         r["products"]["unit"] if r.get("products") else "",
            "user":         r["users"]["name"]    if r.get("users")    else "-",
        })

    return jsonify({
        "data": rows, "total": result.count or 0,
        "total_page": max(1, -(-( result.count or 0)//per_page))
    })

@stok_bp.route("/api/stok/rendah")
@admin_required
def stok_rendah():
    sb      = get_supabase()
    batas   = int(request.args.get("batas", 10))
    result  = sb.table("products").select(
        "id,name,stock,min_stock,unit,categories(name)"
    ).lt("stock", batas).eq("is_active", True).order("stock").execute()

    rows = []
    for p in (result.data or []):
        rows.append({
            "id":       p["id"],
            "name":     p["name"],
            "stock":    p["stock"],
            "min_stock":p.get("min_stock",5),
            "unit":     p.get("unit",""),
            "category": p["categories"]["name"] if p.get("categories") else "-",
        })
    return jsonify(rows)

# ── API SUPPLIER ─────────────────────────────────────────────
@stok_bp.route("/api/supplier", methods=["GET"])
@admin_required
def list_supplier():
    sb     = get_supabase()
    result = sb.table("suppliers").select("*").order("name").execute()
    return jsonify(result.data or [])

@stok_bp.route("/api/supplier", methods=["POST"])
@admin_required
def add_supplier():
    data    = request.json
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}
    res     = req.post(f"{SUPABASE_URL}/rest/v1/suppliers", headers=headers, json={
        "name":    data.get("name",""),
        "phone":   data.get("phone",""),
        "address": data.get("address",""),
        "email":   data.get("email",""),
    })
    if not res.ok:
        return jsonify({"error": res.text}), 500
    return jsonify({"success": True})
