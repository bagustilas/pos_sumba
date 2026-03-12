from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from utils.supabase_client import get_supabase
from utils.access import login_required, admin_required

produk_bp = Blueprint("produk", __name__)

@produk_bp.route("/produk")
@login_required
def index():
    sb       = get_supabase()
    kategori = sb.table("categories").select("id,name").order("name").execute().data or []
    return render_template("produk.html", kategori=kategori)

@produk_bp.route("/api/produk")
@login_required
def api_produk():
    sb       = get_supabase()
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search   = request.args.get("search", "").strip()
    kat_id   = request.args.get("category_id", "").strip()
    offset   = (page - 1) * per_page

    q = sb.table("products").select(
        "id,name,price,cost_price,stock,min_stock,unit,barcode,category_id,is_active,categories(name)",
        count="exact"
    ).eq("is_active", True)

    if search:
        q = q.ilike("name", f"%{search}%")
    if kat_id:
        q = q.eq("category_id", kat_id)

    result     = q.order("name").range(offset, offset + per_page - 1).execute()
    total      = result.count or 0
    total_page = (total + per_page - 1) // per_page

    return jsonify({
        "data":       result.data or [],
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "total_page": total_page,
    })

@produk_bp.route("/produk/tambah", methods=["POST"])
@admin_required
def tambah():
    sb = get_supabase()
    try:
        cat_id = request.form.get("category_id")
        sb.table("products").insert({
            "name":        request.form["name"],
            "price":       float(request.form["price"]),
            "cost_price":  float(request.form.get("cost_price") or 0),
            "stock":       int(request.form.get("stock") or 0),
            "min_stock":   int(request.form.get("min_stock") or 5),
            "unit":        request.form.get("unit", "PCs"),
            "barcode":     request.form.get("barcode") or None,
            "category_id": int(cat_id) if cat_id else None,
            "is_active":   True,
        }).execute()
        flash("Produk berhasil ditambahkan!", "success")
    except Exception as e:
        flash(f"Gagal menambahkan produk: {e}", "error")
    return redirect(url_for("produk.index"))

@produk_bp.route("/produk/edit/<id>", methods=["POST"])
@admin_required
def edit(id):
    sb = get_supabase()
    try:
        sb.table("products").update({
            "name":  request.form["name"],
            "price": float(request.form["price"]),
            "stock": int(request.form.get("stock") or 0),
            "unit":  request.form.get("unit", "PCs"),
        }).eq("id", id).execute()
        flash("Produk berhasil diupdate!", "success")
    except Exception as e:
        flash(f"Gagal update: {e}", "error")
    return redirect(url_for("produk.index"))

@produk_bp.route("/produk/hapus/<id>", methods=["POST"])
@admin_required
def hapus(id):
    sb = get_supabase()
    sb.table("products").update({"is_active": False}).eq("id", id).execute()
    flash("Produk dihapus.", "success")
    return redirect(url_for("produk.index"))

@produk_bp.route("/kategori/tambah", methods=["POST"])
@admin_required
def tambah_kategori():
    sb = get_supabase()
    try:
        sb.table("categories").insert({"name": request.form["name"]}).execute()
        flash("Kategori ditambahkan!", "success")
    except Exception as e:
        flash(f"Gagal: {e}", "error")
    return redirect(url_for("produk.index"))