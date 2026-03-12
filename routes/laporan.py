"""
POS SUMBA — Laporan & Riwayat Transaksi (Fitur #6)
"""
from flask import Blueprint, render_template, request, jsonify
from utils.supabase_client import get_supabase
from utils.access import admin_required
from datetime import date, datetime, timedelta

laporan_bp = Blueprint("laporan", __name__)

@laporan_bp.route("/laporan")
@admin_required
def index():
    return render_template("laporan.html")

@laporan_bp.route("/api/laporan/transaksi")
@admin_required
def api_transaksi():
    sb       = get_supabase()
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    tgl_dari = request.args.get("dari", "")
    tgl_sampai = request.args.get("sampai", "")
    metode   = request.args.get("metode", "")
    search   = request.args.get("search", "").strip()

    offset = (page - 1) * per_page

    q = sb.table("transactions").select(
        "id,invoice_number,total,payment_method,status,note,created_at,cashier_id,users(name)",
        count="exact"
    ).eq("status", "completed")

    if tgl_dari:
        q = q.gte("created_at", tgl_dari)
    if tgl_sampai:
        # Tambah 1 hari agar inklusif
        try:
            sampai_dt = datetime.strptime(tgl_sampai, "%Y-%m-%d") + timedelta(days=1)
            q = q.lte("created_at", sampai_dt.strftime("%Y-%m-%d"))
        except:
            q = q.lte("created_at", tgl_sampai)
    if metode:
        q = q.eq("payment_method", metode)
    if search:
        q = q.ilike("invoice_number", f"%{search}%")

    result = q.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

    rows = []
    for tx in (result.data or []):
        rows.append({
            "id":             tx["id"],
            "invoice_number": tx.get("invoice_number", "-"),
            "total":          float(tx.get("total", 0)),
            "payment_method": tx.get("payment_method", "-"),
            "kasir":          tx["users"]["name"] if tx.get("users") else "-",
            "note":           tx.get("note", ""),
            "created_at":     tx.get("created_at", ""),
        })

    return jsonify({
        "data":       rows,
        "total":      result.count or 0,
        "page":       page,
        "total_page": max(1, -(-( result.count or 0) // per_page)),
    })

@laporan_bp.route("/api/laporan/transaksi/<tx_id>/items")
@admin_required
def api_items(tx_id):
    sb     = get_supabase()
    result = sb.table("transaction_items").select(
        "product_name,price,quantity,subtotal"
    ).eq("transaction_id", tx_id).execute()
    return jsonify(result.data or [])

@laporan_bp.route("/api/laporan/rekap")
@admin_required
def api_rekap():
    sb       = get_supabase()
    tgl_dari = request.args.get("dari", date.today().replace(day=1).isoformat())
    tgl_sampai = request.args.get("sampai", date.today().isoformat())

    try:
        sampai_dt = datetime.strptime(tgl_sampai, "%Y-%m-%d") + timedelta(days=1)
        sampai_str = sampai_dt.strftime("%Y-%m-%d")
    except:
        sampai_str = tgl_sampai

    tx = sb.table("transactions").select("total,payment_method") \
        .eq("status", "completed") \
        .gte("created_at", tgl_dari) \
        .lte("created_at", sampai_str) \
        .execute().data or []

    total_pendapatan = sum(float(t["total"]) for t in tx)
    total_transaksi  = len(tx)

    by_metode = {}
    for t in tx:
        m = t.get("payment_method", "lain")
        by_metode[m] = by_metode.get(m, 0) + float(t["total"])

    return jsonify({
        "total_pendapatan": total_pendapatan,
        "total_transaksi":  total_transaksi,
        "by_metode":        by_metode,
        "dari":             tgl_dari,
        "sampai":           tgl_sampai,
    })

@laporan_bp.route("/api/laporan/export/csv")
@admin_required
def export_csv():
    """Export laporan ke CSV langsung dari server"""
    from flask import Response
    import csv, io

    sb       = get_supabase()
    tgl_dari = request.args.get("dari", date.today().replace(day=1).isoformat())
    tgl_sampai = request.args.get("sampai", date.today().isoformat())

    try:
        sampai_dt = datetime.strptime(tgl_sampai, "%Y-%m-%d") + timedelta(days=1)
        sampai_str = sampai_dt.strftime("%Y-%m-%d")
    except:
        sampai_str = tgl_sampai

    txs = sb.table("transactions").select(
        "invoice_number,total,payment_method,status,note,created_at,users(name)"
    ).eq("status","completed").gte("created_at", tgl_dari).lte("created_at", sampai_str) \
     .order("created_at", desc=True).execute().data or []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice","Tanggal","Kasir","Metode","Total","Catatan"])
    for tx in txs:
        writer.writerow([
            tx.get("invoice_number",""),
            tx.get("created_at",""),
            tx["users"]["name"] if tx.get("users") else "",
            tx.get("payment_method",""),
            tx.get("total",""),
            tx.get("note",""),
        ])

    filename = f"laporan-{tgl_dari}-{tgl_sampai}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
