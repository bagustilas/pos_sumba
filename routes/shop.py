"""
POS SUMBA — Halaman Toko Pelanggan (Customer-facing)
Berisi: video promo, katalog produk, keranjang belanja, total pembayaran
"""
from flask import Blueprint, render_template, request, jsonify
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY

shop_bp = Blueprint("shop", __name__)

@shop_bp.route("/shop")
def index():
    """Halaman toko publik — bisa diakses siapa saja (pelanggan)"""
    sb       = get_supabase()
    raw      = sb.table("settings").select("key,value").execute().data or []
    settings = {s["key"]: s["value"] for s in raw}

    # Ambil kategori
    cats = sb.table("categories").select("id,name").order("name").execute().data or []

    return render_template("shop.html", settings=settings, categories=cats,
                           supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

@shop_bp.route("/api/shop/produk")
def api_produk():
    """API produk untuk halaman toko pelanggan"""
    sb       = get_supabase()
    search   = request.args.get("search", "").strip()
    cat_id   = request.args.get("category", "")
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 24))
    offset   = (page - 1) * per_page

    q = sb.table("products").select(
        "id,name,price,stock,barcode,categories(name)",
        count="exact"
    ).eq("is_active", True).gt("stock", 0).gt("price", 0)

    if search:
        q = q.ilike("name", f"%{search}%")
    if cat_id:
        q = q.eq("category_id", cat_id)

    result = q.order("name").range(offset, offset + per_page - 1).execute()

    rows = []
    for p in (result.data or []):
        rows.append({
            "id":       p["id"],
            "name":     p["name"],
            "price":    float(p["price"]),
            "stock":    p["stock"],
            "barcode":  p.get("barcode", ""),
            "category": p["categories"]["name"] if p.get("categories") else "Umum",
        })

    return jsonify({
        "data":       rows,
        "total":      result.count or 0,
        "total_page": max(1, -(-( result.count or 0) // per_page)),
    })