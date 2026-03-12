from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from functools import wraps
import requests as req

kasir_bp = Blueprint("kasir", __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

@kasir_bp.route("/kasir")
@login_required
def index():
    sb       = get_supabase()
    kategori = sb.table("categories").select("id,name").eq("is_active", True).order("name").execute().data or []
    # Ambil settings toko untuk struk
    raw_settings = sb.table("settings").select("key,value").execute().data or []
    settings = {s["key"]: s["value"] for s in raw_settings}
    return render_template("kasir.html", kategori=kategori, settings=settings)

@kasir_bp.route("/api/kasir/produk")
@login_required
def api_produk():
    sb       = get_supabase()
    search   = request.args.get("search", "").strip()
    kat_id   = request.args.get("category_id", "").strip()
    page     = int(request.args.get("page", 1))
    per_page = 60

    offset = (page - 1) * per_page

    q = sb.table("products").select(
        "id,name,price,stock,unit,category_id",
        count="exact"
    ).eq("is_active", True)

    if search:
        q = q.ilike("name", f"%{search}%")
    if kat_id:
        q = q.eq("category_id", kat_id)

    result = q.order("name").range(offset, offset + per_page - 1).execute()

    return jsonify({
        "data":       result.data or [],
        "total":      result.count or 0,
        "page":       page,
        "total_page": ((result.count or 0) + per_page - 1) // per_page,
    })

@kasir_bp.route("/api/transaksi", methods=["POST"])
@login_required
def buat_transaksi():
    data    = request.json
    items   = data.get("items", [])
    method  = data.get("payment_method", "cash")
    paid    = float(data.get("amount_paid", 0))

    if not items:
        return jsonify({"error": "Keranjang kosong"}), 400

    subtotal = sum(float(i["price"]) * int(i["qty"]) for i in items)
    total    = subtotal
    change   = max(paid - total, 0)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    try:
        tx_res = req.post(
            f"{SUPABASE_URL}/rest/v1/transactions",
            headers=headers,
            json={
                "cashier_id": session["user"]["id"],
                "customer_id": data.get("customer_id"),
                "subtotal": subtotal,
                "total": total,
                "payment_method": method,
                "amount_paid": paid,
                "change_amount": change,
                "status": "completed",
            }
        )
        tx_res.raise_for_status()
        tx = tx_res.json()
        tx = tx[0] if isinstance(tx, list) else tx

        tx_items = [{
            "transaction_id": tx["id"],
            "product_id": i["id"],
            "product_name": i["name"],
            "price": float(i["price"]),
            "quantity": int(i["qty"]),
            "subtotal": float(i["price"]) * int(i["qty"]),
        } for i in items]

        req.post(f"{SUPABASE_URL}/rest/v1/transaction_items", headers=headers, json=tx_items).raise_for_status()

        return jsonify({
            "success": True,
            "invoice": tx.get("invoice_number", "-"),
            "total": total,
            "change": change,
            "items": items,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500