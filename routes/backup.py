"""
POS SUMBA — Backup & Export Data (Fase 3)
"""
from flask import Blueprint, render_template, request, jsonify, session, Response
from utils.supabase_client import get_supabase, SUPABASE_URL, SUPABASE_KEY
from utils.access import admin_required
import requests as req
import json, csv, io
from datetime import date, datetime, timedelta, timezone

backup_bp = Blueprint("backup", __name__)
WITA = timezone(timedelta(hours=8))

@backup_bp.route("/backup")
@admin_required
def index():
    sb   = get_supabase()
    logs = sb.table("backup_log").select("*").order("created_at", desc=True).limit(20).execute().data or []
    return render_template("backup.html", logs=logs)

@backup_bp.route("/api/backup/transaksi")
@admin_required
def export_transaksi():
    """Export transaksi ke CSV"""
    sb       = get_supabase()
    dari     = request.args.get("dari", date.today().replace(day=1).isoformat())
    sampai   = request.args.get("sampai", date.today().isoformat())
    fmt      = request.args.get("format", "csv")  # csv | json

    try:
        sampai_dt = datetime.strptime(sampai, "%Y-%m-%d") + timedelta(days=1)
        sampai_str = sampai_dt.strftime("%Y-%m-%d")
    except:
        sampai_str = sampai

    txs = sb.table("transactions").select(
        "invoice_number,total,subtotal,discount,tax,payment_method,amount_paid,change_amount,"
        "voucher_code,points_used,points_earned,note,status,created_at,"
        "users(name),customers(name,member_code)"
    ).eq("status", "completed") \
     .gte("created_at", dari) \
     .lte("created_at", sampai_str) \
     .order("created_at").execute().data or []

    if fmt == "json":
        data = json.dumps(txs, ensure_ascii=False, indent=2, default=str)
        filename = f"transaksi-{dari}-{sampai}.json"
        return Response(data, mimetype="application/json",
                        headers={"Content-Disposition": f"attachment; filename={filename}"})

    # CSV
    out    = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Invoice","Tanggal","Kasir","Pelanggan","Kode Member",
                     "Subtotal","Diskon","Pajak","Total","Bayar","Kembalian",
                     "Metode","Voucher","Poin Pakai","Poin Dapat","Catatan"])
    for t in txs:
        writer.writerow([
            t.get("invoice_number",""),
            t.get("created_at",""),
            t["users"]["name"]     if t.get("users")     else "",
            t["customers"]["name"] if t.get("customers") else "",
            t["customers"]["member_code"] if t.get("customers") else "",
            t.get("subtotal",""), t.get("discount",""), t.get("tax",""), t.get("total",""),
            t.get("amount_paid",""), t.get("change_amount",""),
            t.get("payment_method",""), t.get("voucher_code",""),
            t.get("points_used",""), t.get("points_earned",""),
            t.get("note",""),
        ])

    filename = f"transaksi-{dari}-{sampai}.csv"
    _log_backup(sb, filename)
    return Response(out.getvalue(), mimetype="text/csv;charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@backup_bp.route("/api/backup/produk")
@admin_required
def export_produk():
    """Export semua produk ke CSV"""
    sb   = get_supabase()
    data = sb.table("products").select("name,barcode,price,cost_price,stock,min_stock,unit,is_active,categories(name)") \
             .order("name").execute().data or []

    out    = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Nama","Barcode","Kategori","Harga Jual","Harga Beli","Stok","Min Stok","Satuan","Aktif"])
    for p in data:
        writer.writerow([
            p.get("name",""), p.get("barcode",""),
            p["categories"]["name"] if p.get("categories") else "",
            p.get("price",""), p.get("cost_price",""),
            p.get("stock",""), p.get("min_stock",""),
            p.get("unit",""), p.get("is_active",""),
        ])

    filename = f"produk-{date.today()}.csv"
    _log_backup(sb, filename)
    return Response(out.getvalue(), mimetype="text/csv;charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

@backup_bp.route("/api/backup/pelanggan")
@admin_required
def export_pelanggan():
    """Export semua pelanggan ke CSV"""
    sb   = get_supabase()
    data = sb.table("customers").select("name,phone,email,address,member_code,points,total_purchase,created_at") \
             .eq("is_active", True).order("name").execute().data or []

    out    = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Nama","Telepon","Email","Alamat","Kode Member","Poin","Total Pembelian","Bergabung"])
    for c in data:
        writer.writerow([
            c.get("name",""), c.get("phone",""), c.get("email",""), c.get("address",""),
            c.get("member_code",""), c.get("points",""), c.get("total_purchase",""), c.get("created_at",""),
        ])

    filename = f"pelanggan-{date.today()}.csv"
    _log_backup(sb, filename)
    return Response(out.getvalue(), mimetype="text/csv;charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

def _log_backup(sb, filename):
    try:
        headers = {"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}","Content-Type":"application/json"}
        req.post(f"{SUPABASE_URL}/rest/v1/backup_log", headers=headers,
                 json={"filename": filename, "created_by": session.get("user",{}).get("id")})
    except:
        pass
