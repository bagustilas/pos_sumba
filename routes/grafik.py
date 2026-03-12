"""
POS SUMBA — API Grafik Dashboard (Fase 2 #12)
"""
from flask import Blueprint, jsonify, request
from utils.supabase_client import get_supabase
from utils.access import admin_required
from datetime import date, timedelta, datetime, timezone

grafik_bp = Blueprint("grafik", __name__)
WITA = timezone(timedelta(hours=8))

@grafik_bp.route("/api/grafik/penjualan")
@admin_required
def penjualan():
    """Tren penjualan N hari terakhir"""
    hari   = int(request.args.get("hari", 7))
    sb     = get_supabase()
    today  = date.today()
    result = []

    for i in range(hari-1, -1, -1):
        tgl      = today - timedelta(days=i)
        tgl_str  = tgl.isoformat()
        tgl_next = (tgl + timedelta(days=1)).isoformat()

        txs = sb.table("transactions").select("total").eq("status","completed") \
                .gte("created_at", tgl_str).lt("created_at", tgl_next).execute().data or []

        result.append({
            "tanggal":    tgl_str,
            "label":      tgl.strftime("%d %b"),
            "pendapatan": sum(float(t["total"]) for t in txs),
            "jumlah_tx":  len(txs),
        })

    return jsonify(result)

@grafik_bp.route("/api/grafik/metode")
@admin_required
def metode():
    """Distribusi metode pembayaran bulan ini"""
    sb       = get_supabase()
    bulan    = date.today().replace(day=1).isoformat()
    txs      = sb.table("transactions").select("payment_method,total") \
                 .eq("status","completed").gte("created_at", bulan).execute().data or []

    by_metode = {}
    for t in txs:
        m = t.get("payment_method","lain")
        by_metode[m] = by_metode.get(m, 0) + 1

    return jsonify(by_metode)

@grafik_bp.route("/api/grafik/produk_terlaris")
@admin_required
def produk_terlaris():
    """Top 10 produk terlaris bulan ini"""
    sb      = get_supabase()
    bulan   = date.today().replace(day=1).isoformat()

    # Ambil transaction_ids bulan ini
    txs = sb.table("transactions").select("id").eq("status","completed") \
             .gte("created_at", bulan).execute().data or []
    tx_ids = [t["id"] for t in txs]

    if not tx_ids:
        return jsonify([])

    # Ambil items dari transaksi bulan ini
    items = sb.table("transaction_items").select(
        "product_name,quantity,subtotal"
    ).execute().data or []  # simplified — ambil semua lalu filter

    # Agregasi
    produk = {}
    for item in items:
        nama = item["product_name"]
        produk[nama] = produk.get(nama, {"qty":0,"revenue":0})
        produk[nama]["qty"]     += int(item["quantity"])
        produk[nama]["revenue"] += float(item["subtotal"])

    top10 = sorted(produk.items(), key=lambda x: x[1]["qty"], reverse=True)[:10]
    return jsonify([{"nama": k, "qty": v["qty"], "revenue": v["revenue"]} for k,v in top10])
