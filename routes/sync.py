"""
POS SUMBA — Sync Route
Menerima transaksi offline dari browser IndexedDB
"""
from flask import Blueprint, request, jsonify, session, make_response, current_app
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import login_required
import requests as req
import os

sync_bp = Blueprint("sync", __name__)

# ── SERVICE WORKER ────────────────────────────────────────────
# Harus dari root '/' bukan '/static/' agar bisa kontrol semua halaman
@sync_bp.route('/sw.js')
def service_worker():
    sw_path = os.path.join(current_app.root_path, 'static', 'sw.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    resp = make_response(content)
    resp.headers['Content-Type']           = 'application/javascript'
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control']          = 'no-cache, no-store, must-revalidate'
    return resp

@sync_bp.route("/api/sync", methods=["POST"])
@login_required
def sync_transaction():
    data     = request.json
    items    = data.get("items", [])
    method   = data.get("payment_method", "cash")
    paid     = float(data.get("amount_paid", 0))
    local_id = data.get("local_id")

    if not items:
        return jsonify({"error": "Tidak ada item"}), 400

    subtotal = sum(float(i["price"]) * int(i["qty"]) for i in items)
    total    = subtotal
    change   = max(paid - total, 0)

    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }

    try:
        # Tidak kirim invoice_number — biarkan trigger DB yang generate otomatis
        # Gunakan field "note" (bukan "notes") sesuai skema tabel
        tx_payload = {
            "cashier_id":     session["user"]["id"],
            "subtotal":       subtotal,
            "total":          total,
            "payment_method": method,
            "amount_paid":    paid,
            "change_amount":  change,
            "status":         "completed",
            "note":           f"[OFFLINE] local_id:{local_id}",
        }

        tx_res = req.post(
            f"{SUPABASE_URL}/rest/v1/transactions",
            headers=headers,
            json=tx_payload,
        )

        # Jika gagal, kembalikan error detail untuk debugging
        if not tx_res.ok:
            return jsonify({
                "error": f"DB error {tx_res.status_code}: {tx_res.text}"
            }), 500

        tx = tx_res.json()
        tx = tx[0] if isinstance(tx, list) else tx

        # Insert transaction items
        tx_items = [{
            "transaction_id": tx["id"],
            "product_id":     i["id"],
            "product_name":   i["name"],
            "price":          float(i["price"]),
            "quantity":       int(i["qty"]),
            "subtotal":       float(i["price"]) * int(i["qty"]),
        } for i in items]

        items_res = req.post(
            f"{SUPABASE_URL}/rest/v1/transaction_items",
            headers=headers,
            json=tx_items,
        )

        if not items_res.ok:
            return jsonify({
                "error": f"Items error {items_res.status_code}: {items_res.text}"
            }), 500

        return jsonify({
            "success":  True,
            "local_id": local_id,
            "invoice":  tx.get("invoice_number", "-"),
            "total":    total,
            "change":   change,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@sync_bp.route("/api/sync/status")
@login_required
def sync_status():
    sb = get_supabase()
    try:
        result = sb.table("transactions").select(
            "id,invoice_number,total,note,created_at", count="exact"
        ).like("note", "%OFFLINE%").execute()
        return jsonify({
            "total_offline_synced": result.count or 0,
            "records": result.data or []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500