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
    data         = request.json
    items        = data.get("items", [])
    method       = data.get("payment_method", "cash")
    paid         = float(data.get("amount_paid", 0))
    disc_pct     = float(data.get("discount_pct", 0))
    disc_nominal = float(data.get("discount_nominal", 0))
    shift_id     = data.get("shift_id")
    customer_id  = data.get("customer_id")
    note         = data.get("note", "")
    voucher_code = data.get("voucher_code", "")
    voucher_disc = float(data.get("voucher_discount", 0))
    points_used  = int(data.get("points_used", 0))

    if not items:
        return jsonify({"error": "Keranjang kosong"}), 400

    # Hitung subtotal
    subtotal = sum((float(i["price"]) * int(i["qty"])) - float(i.get("discount", 0)) for i in items)

    # Diskon manual + voucher
    disc_amount  = disc_nominal + (subtotal * disc_pct / 100) + voucher_disc
    disc_amount  = min(disc_amount, subtotal)

    # Redeem poin → diskon tambahan
    sb           = get_supabase()
    settings_raw = sb.table("settings").select("key,value").execute().data or []
    settings     = {s["key"]: s["value"] for s in settings_raw}
    redeem_rate  = float(settings.get("loyalty_redeem_rate", 100))   # Rp per poin
    points_rate  = float(settings.get("loyalty_points_rate", 1000))  # Rp per poin earned
    tax_pct      = float(settings.get("tax_percentage", 0))
    loyalty_on   = settings.get("loyalty_active", "1") == "1"

    points_disc  = points_used * redeem_rate if points_used > 0 else 0
    disc_amount  = min(disc_amount + points_disc, subtotal)

    after_disc   = subtotal - disc_amount
    tax_amount   = after_disc * tax_pct / 100
    total        = after_disc + tax_amount
    change       = max(paid - total, 0)

    # Hitung poin yang akan didapat
    points_earned = int(total / points_rate) if loyalty_on and customer_id else 0

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    try:
        tx_payload = {
            "cashier_id":    session["user"]["id"],
            "subtotal":      subtotal,
            "discount":      disc_amount,
            "tax":           tax_amount,
            "total":         total,
            "payment_method":method,
            "amount_paid":   paid,
            "change_amount": change,
            "status":        "completed",
            "note":          note,
            "points_used":   points_used,
            "points_earned": points_earned,
        }
        if customer_id:  tx_payload["customer_id"] = customer_id
        if shift_id:     tx_payload["shift_id"]    = int(shift_id)
        if voucher_code: tx_payload["voucher_code"] = voucher_code.upper()

        tx_res = req.post(f"{SUPABASE_URL}/rest/v1/transactions", headers=headers, json=tx_payload)
        tx_res.raise_for_status()
        tx = tx_res.json()
        tx = tx[0] if isinstance(tx, list) else tx

        # Insert items & kurangi stok
        tx_items = []
        for i in items:
            item_price    = float(i["price"])
            item_qty      = int(i["qty"])
            item_disc     = float(i.get("discount", 0))
            tx_items.append({
                "transaction_id": tx["id"],
                "product_id":     i["id"],
                "product_name":   i["name"],
                "price":          item_price,
                "quantity":       item_qty,
                "discount":       item_disc,
                "subtotal":       (item_price * item_qty) - item_disc,
            })
            prod = sb.table("products").select("stock").eq("id", i["id"]).execute().data
            if prod:
                old_stock = prod[0]["stock"] or 0
                new_stock = max(0, old_stock - item_qty)
                req.patch(f"{SUPABASE_URL}/rest/v1/products?id=eq.{i['id']}", headers=headers,
                          json={"stock": new_stock, "updated_at": "now()"})
                req.post(f"{SUPABASE_URL}/rest/v1/stock_history", headers=headers, json={
                    "product_id":   i["id"],
                    "user_id":      session["user"]["id"],
                    "type":         "out",
                    "quantity":     item_qty,
                    "stock_before": old_stock,
                    "stock_after":  new_stock,
                    "note":         f"Penjualan {tx['invoice_number']}",
                })

        req.post(f"{SUPABASE_URL}/rest/v1/transaction_items", headers=headers, json=tx_items).raise_for_status()

        # ── LOYALTY POINTS ───────────────────────────────────
        if customer_id and loyalty_on:
            cust = sb.table("customers").select("points,points_total,total_purchase").eq("id", customer_id).execute().data
            if cust:
                cur_pts    = cust[0]["points"] or 0
                total_pts  = cust[0]["points_total"] or 0
                cur_purchase = float(cust[0]["total_purchase"] or 0)
                net_pts    = cur_pts - points_used + points_earned
                new_pts    = max(0, net_pts)

                req.patch(f"{SUPABASE_URL}/rest/v1/customers?id=eq.{customer_id}", headers=headers, json={
                    "points":         new_pts,
                    "points_total":   total_pts + points_earned,
                    "total_purchase": cur_purchase + total,
                    "updated_at":     "now()",
                })
                if points_used > 0:
                    req.post(f"{SUPABASE_URL}/rest/v1/point_history", headers=headers, json={
                        "customer_id":  customer_id,
                        "transaction_id": tx["id"],
                        "type":         "redeem",
                        "points":       -points_used,
                        "balance_after":max(0, cur_pts - points_used),
                        "note":         f"Redeem poin — {tx['invoice_number']}",
                    })
                if points_earned > 0:
                    req.post(f"{SUPABASE_URL}/rest/v1/point_history", headers=headers, json={
                        "customer_id":  customer_id,
                        "transaction_id": tx["id"],
                        "type":         "earn",
                        "points":       points_earned,
                        "balance_after":new_pts,
                        "note":         f"Poin dari {tx['invoice_number']}",
                    })

        # ── INCREMENT VOUCHER USED COUNT ─────────────────────
        if voucher_code:
            v = sb.table("vouchers").select("used_count").eq("code", voucher_code.upper()).execute().data
            if v:
                req.patch(f"{SUPABASE_URL}/rest/v1/vouchers?code=eq.{voucher_code.upper()}", headers=headers,
                          json={"used_count": (v[0]["used_count"] or 0) + 1})

        return jsonify({
            "success":       True,
            "invoice":       tx.get("invoice_number", "-"),
            "subtotal":      subtotal,
            "discount":      disc_amount,
            "tax":           tax_amount,
            "total":         total,
            "change":        change,
            "points_earned": points_earned,
            "points_used":   points_used,
            "items":         items,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@kasir_bp.route("/api/produk/barcode/<barcode>")
@login_required
def cari_barcode(barcode):
    """Cari produk berdasarkan barcode untuk scanner"""
    sb     = get_supabase()
    result = sb.table("products").select(
        "id,name,price,stock,unit,barcode"
    ).eq("barcode", barcode).eq("is_active", True).execute()

    if not result.data:
        return jsonify({"error": "Produk tidak ditemukan"}), 404
    return jsonify(result.data[0])
