from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from utils.supabase_client import get_supabase
from utils.access import admin_required
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__)

def _get_stats():
    sb    = get_supabase()
    today = date.today()
    # Awal bulan ini
    bulan_ini = today.replace(day=1).isoformat()

    total_produk    = sb.table("products").select("id", count="exact").eq("is_active", True).range(0,0).execute().count or 0
    total_transaksi = sb.table("transactions").select("id", count="exact").eq("status","completed").range(0,0).execute().count or 0
    total_pelanggan = sb.table("customers").select("id", count="exact").range(0,0).execute().count or 0

    # Pendapatan bulan ini (sejak tanggal 1 bulan berjalan)
    tx_bulan = sb.table("transactions").select("total") \
        .eq("status", "completed") \
        .gte("created_at", bulan_ini) \
        .execute().data or []
    pendapatan_bulan_ini = sum(float(t["total"]) for t in tx_bulan)

    transaksi_terbaru = sb.table("transactions").select(
        "invoice_number,total,payment_method,created_at,customers(name)"
    ).eq("status","completed").order("created_at", desc=True).limit(5).execute().data or []

    stok_rendah = sb.table("products").select(
        "name,stock,min_stock,unit"
    ).lt("stock", 10).eq("is_active", True).limit(5).execute().data or []

    return dict(
        total_produk=total_produk,
        total_transaksi=total_transaksi,
        total_pelanggan=total_pelanggan,
        pendapatan_bulan_ini=pendapatan_bulan_ini,
        transaksi_terbaru=transaksi_terbaru,
        stok_rendah=stok_rendah,
        bulan_label=today.strftime('%B %Y'),
    )

@dashboard_bp.route("/dashboard")
@admin_required
def index():
    try:
        stats = _get_stats()
    except Exception as e:
        print(f"Dashboard error: {e}")
        stats = dict(total_produk=0, total_transaksi=0, total_pelanggan=0,
                     pendapatan_bulan_ini=0, transaksi_terbaru=[], stok_rendah=[],
                     bulan_label='')
    return render_template("dashboard.html", **stats)

@dashboard_bp.route("/api/dashboard/stats")
@admin_required
def api_stats():
    try:
        stats = _get_stats()
        txs = []
        for tx in stats["transaksi_terbaru"]:
            txs.append({
                "invoice_number": tx.get("invoice_number", "-"),
                "customer":       tx["customers"]["name"] if tx.get("customers") else "—",
                "payment_method": tx.get("payment_method", "-"),
                "total":          float(tx.get("total", 0)),
            })
        stok = []
        for p in stats["stok_rendah"]:
            stok.append({
                "name":  p["name"],
                "stock": p["stock"],
                "unit":  p.get("unit", ""),
            })
        return jsonify({
            "pendapatan_bulan_ini": stats["pendapatan_bulan_ini"],
            "bulan_label":          stats["bulan_label"],
            "total_transaksi":      stats["total_transaksi"],
            "total_produk":         stats["total_produk"],
            "total_pelanggan":      stats["total_pelanggan"],
            "transaksi_terbaru":    txs,
            "stok_rendah":          stok,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500