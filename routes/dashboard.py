from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from utils.supabase_client import get_supabase
from utils.access import admin_required
from datetime import date

dashboard_bp = Blueprint("dashboard", __name__)

def _get_stats():
    sb    = get_supabase()
    today = date.today().isoformat()

    total_produk    = sb.table("products").select("id", count="exact").eq("is_active", True).range(0,0).execute().count or 0
    total_transaksi = sb.table("transactions").select("id", count="exact").eq("status","completed").range(0,0).execute().count or 0
    total_pelanggan = sb.table("customers").select("id", count="exact").range(0,0).execute().count or 0

    tx_today = sb.table("transactions").select("total").eq("status","completed").gte("created_at", today).execute().data or []
    pendapatan_hari_ini = sum(float(t["total"]) for t in tx_today)

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
        pendapatan_hari_ini=pendapatan_hari_ini,
        transaksi_terbaru=transaksi_terbaru,
        stok_rendah=stok_rendah,
    )

@dashboard_bp.route("/dashboard")
@admin_required
def index():
    try:
        stats = _get_stats()
    except Exception as e:
        print(f"Dashboard error: {e}")
        stats = dict(total_produk=0, total_transaksi=0, total_pelanggan=0,
                     pendapatan_hari_ini=0, transaksi_terbaru=[], stok_rendah=[])
    return render_template("dashboard.html", **stats)

@dashboard_bp.route("/api/dashboard/stats")
@admin_required
def api_stats():
    """Endpoint untuk polling realtime dari browser"""
    try:
        stats = _get_stats()
        # Serialisasi transaksi_terbaru untuk JSON
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
            "pendapatan_hari_ini": stats["pendapatan_hari_ini"],
            "total_transaksi":     stats["total_transaksi"],
            "total_produk":        stats["total_produk"],
            "total_pelanggan":     stats["total_pelanggan"],
            "transaksi_terbaru":   txs,
            "stok_rendah":         stok,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500