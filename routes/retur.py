"""
POS SUMBA — Retur Transaksi (Fase 3)
"""
from flask import Blueprint, render_template, request, jsonify, session
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required, login_required
import requests as req

retur_bp = Blueprint("retur", __name__)

@retur_bp.route("/retur")
@admin_required
def index():
    return render_template("retur.html")

@retur_bp.route("/api/retur")
@admin_required
def api_list():
    sb     = get_supabase()
    page   = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    result = sb.table("returns").select(
        "id,total_refund,reason,status,created_at,transactions(invoice_number),users(name)",
        count="exact"
    ).order("created_at", desc=True).range(offset, offset+per_page-1).execute()

    rows = []
    for r in (result.data or []):
        rows.append({
            "id":           r["id"],
            "invoice":      r["transactions"]["invoice_number"] if r.get("transactions") else "-",
            "kasir":        r["users"]["name"] if r.get("users") else "-",
            "total_refund": float(r.get("total_refund", 0)),
            "reason":       r.get("reason", ""),
            "status":       r.get("status", ""),
            "created_at":   r.get("created_at", ""),
        })
    return jsonify({
        "data": rows, "total": result.count or 0,
        "total_page": max(1, -(-( result.count or 0) // per_page))
    })

@retur_bp.route("/api/retur/cek/<invoice>")
@admin_required
def cek_invoice(invoice):
    """Ambil detail transaksi untuk proses retur"""
    sb     = get_supabase()
    txs    = sb.table("transactions").select("id,invoice_number,total,payment_method,created_at") \
               .eq("invoice_number", invoice).eq("status", "completed").execute().data
    if not txs:
        return jsonify({"error": "Invoice tidak ditemukan"}), 404

    tx     = txs[0]
    items  = sb.table("transaction_items").select("product_id,product_name,price,quantity,subtotal") \
               .eq("transaction_id", tx["id"]).execute().data or []

    # Cek apakah sudah pernah diretur
    existing = sb.table("returns").select("id").eq("transaction_id", tx["id"]).execute().data
    if existing:
        return jsonify({"error": "Transaksi ini sudah pernah diretur"}), 400

    return jsonify({"transaction": tx, "items": items})

@retur_bp.route("/api/retur", methods=["POST"])
@admin_required
def api_create():
    data    = request.json
    tx_id   = data.get("transaction_id")
    items   = data.get("items", [])  # [{product_id, product_name, price, qty}]
    reason  = data.get("reason", "")

    if not tx_id or not items:
        return jsonify({"error": "Data retur tidak lengkap"}), 400

    total_refund = sum(float(i["price"]) * int(i["qty"]) for i in items)
    headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json","Prefer":"return=representation"}

    # Buat retur header
    ret_res = req.post(f"{SUPABASE_URL}/rest/v1/returns", headers=headers, json={
        "transaction_id": tx_id,
        "cashier_id":     session["user"]["id"],
        "total_refund":   total_refund,
        "reason":         reason,
        "status":         "approved",
    })
    if not ret_res.ok:
        return jsonify({"error": ret_res.text}), 500
    ret = ret_res.json()[0]

    # Insert retur items & kembalikan stok
    sb = get_supabase()
    for item in items:
        req.post(f"{SUPABASE_URL}/rest/v1/return_items", headers=headers, json={
            "return_id":    ret["id"],
            "product_id":   item.get("product_id"),
            "product_name": item["product_name"],
            "qty":          int(item["qty"]),
            "price":        float(item["price"]),
            "subtotal":     float(item["price"]) * int(item["qty"]),
        })
        # Kembalikan stok
        if item.get("product_id"):
            prod = sb.table("products").select("stock").eq("id", item["product_id"]).execute().data
            if prod:
                old_stock = prod[0]["stock"] or 0
                new_stock = old_stock + int(item["qty"])
                req.patch(f"{SUPABASE_URL}/rest/v1/products?id=eq.{item['product_id']}", headers=headers,
                          json={"stock": new_stock, "updated_at": "now()"})
                req.post(f"{SUPABASE_URL}/rest/v1/stock_history", headers=headers, json={
                    "product_id":   item["product_id"],
                    "user_id":      session["user"]["id"],
                    "type":         "in",
                    "quantity":     int(item["qty"]),
                    "stock_before": old_stock,
                    "stock_after":  new_stock,
                    "note":         f"Retur #{ret['id']} — {reason}",
                })

    return jsonify({"success": True, "retur_id": ret["id"], "total_refund": total_refund})
