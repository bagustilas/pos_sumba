# POS SUMBA V.1 — Web App (Flask + Supabase)

Aplikasi Point of Sale berbasis web untuk toko di Sumba, NTT.
Dibangun dengan **Python Flask** + **Supabase** (PostgreSQL cloud) + **Vanilla JS**.

---

## 📁 Struktur Folder

```
pos_web_requests/
├── app.py                        # Entry point Flask + registrasi blueprint
├── .env                          # SUPABASE_URL, SUPABASE_KEY, SECRET (jangan di-commit!)
├── requirements.txt
├── Procfile                      # web: python app.py (untuk Railway)
├── routes/
│   ├── auth.py                   # Login & logout
│   ├── dashboard.py              # Dashboard + polling API
│   ├── kasir.py                  # Kasir, transaksi, barcode, loyalty, voucher
│   ├── produk.py                 # Manajemen produk & kategori
│   ├── laporan.py                # Riwayat transaksi, rekap, export CSV
│   ├── stok.py                   # Stok masuk, riwayat, stok rendah, supplier
│   ├── shift.py                  # Buka/tutup shift kasir
│   ├── grafik.py                 # API grafik Chart.js
│   ├── pengguna.py               # Manajemen user kasir
│   ├── pengaturan.py             # Pengaturan toko
│   ├── pelanggan.py              # Pelanggan & loyalty points  ← Fase 3
│   ├── voucher.py                # Voucher & promo             ← Fase 3
│   ├── retur.py                  # Retur transaksi             ← Fase 3
│   ├── backup.py                 # Backup & export data        ← Fase 3
│   └── sync.py                   # Offline sync + service worker
├── utils/
│   ├── supabase_client.py        # Custom query builder REST API
│   └── access.py                 # login_required, admin_required
├── templates/
│   ├── base.html                 # Layout utama + sidebar navigasi
│   ├── login.html
│   ├── dashboard.html            # Statistik + grafik Chart.js
│   ├── kasir.html                # POS interaktif (barcode, diskon, loyalty, voucher)
│   ├── produk.html
│   ├── laporan.html              # Riwayat + rekap + export
│   ├── stok.html                 # Stok masuk + riwayat + supplier
│   ├── shift.html                # Buka/tutup shift + riwayat
│   ├── pelanggan.html            # Member + poin loyalty       ← Fase 3
│   ├── voucher.html              # Kelola voucher              ← Fase 3
│   ├── retur.html                # Proses retur                ← Fase 3
│   ├── backup.html               # Export & backup             ← Fase 3
│   ├── pengguna.html
│   └── pengaturan.html
└── static/
    ├── css/style.css             # Dark theme stylesheet
    ├── js/
    │   ├── main.js
    │   ├── db.js                 # IndexedDB manager (offline)
    │   ├── sync.js               # Auto-sync offline → Supabase
    │   └── printer.js            # ESC/POS 58mm thermal via Web Serial API
    └── sw.js                     # Service Worker
```

---

## 🚀 Cara Menjalankan

```bash
# 1. Install dependensi
pip install flask requests python-dotenv

# 2. Buat file .env
SUPABASE_URL=https://qhdbnvdaopwczrezfkeu.supabase.co
SUPABASE_KEY=your_anon_key_here
FLASK_SECRET_KEY=your_secret_key_here

# 3. Jalankan aplikasi
python app.py

# 4. Buka browser
# http://localhost:5000
```

---

## 🔐 Akun Login

| Email | Password | Role |
|-------|----------|------|
| admin@possumba.com | admin123 | Admin — akses penuh |
| kasir@possumba.com | kasir123 | Kasir — transaksi & shift |

---

## 📦 Database (Supabase)

| Tabel | Fungsi |
|-------|--------|
| `roles` | Master role (admin, kasir) |
| `users` | Data pengguna & autentikasi |
| `categories` | Kategori produk |
| `products` | Produk: harga, stok, barcode |
| `customers` | Pelanggan + poin loyalty + kode member |
| `transactions` | Transaksi + voucher + poin |
| `transaction_items` | Item per transaksi |
| `stock_history` | Riwayat perubahan stok |
| `stock_in` / `stock_in_items` | Penerimaan stok masuk |
| `suppliers` | Data supplier |
| `shifts` | Shift kasir + kas |
| `vouchers` | Kode voucher & promo |
| `point_history` | Riwayat earn/redeem poin |
| `returns` / `return_items` | Retur transaksi |
| `settings` | Konfigurasi toko (key-value) |
| `backup_log` | Log export/backup |

> Invoice auto-generated via PostgreSQL trigger: `INV-YYYYMMDD-NNNNN`

---

## 🗺️ Halaman & API

### Halaman Utama

| URL | Halaman | Akses |
|-----|---------|-------|
| `/` atau `/login` | Login | Publik |
| `/dashboard` | Dashboard statistik + grafik | Admin |
| `/kasir` | Kasir POS | Semua |
| `/produk` | Manajemen produk | Semua |
| `/laporan` | Riwayat & rekap transaksi | Admin |
| `/stok` | Stok masuk + supplier | Admin |
| `/shift` | Shift kasir | Semua |
| `/pelanggan` | Member & loyalty points | Admin |
| `/voucher` | Voucher & promo | Admin |
| `/retur` | Retur transaksi | Admin |
| `/pengguna` | Manajemen user kasir | Admin |
| `/pengaturan` | Pengaturan toko | Admin |
| `/backup` | Export & backup data | Admin |

### API Utama

| Endpoint | Fungsi |
|----------|--------|
| `POST /api/transaksi` | Buat transaksi (+ loyalty + voucher) |
| `GET /api/kasir/produk` | List produk untuk kasir |
| `GET /api/produk/barcode/<barcode>` | Cari produk by barcode |
| `GET /api/pelanggan/cari?q=` | Cari pelanggan dari kasir |
| `POST /api/voucher/cek` | Validasi kode voucher |
| `POST /api/retur` | Proses retur + kembalikan stok |
| `GET /api/backup/transaksi` | Export CSV/JSON transaksi |
| `GET /api/grafik/penjualan` | Data tren penjualan (Chart.js) |
| `POST /api/shift/buka` | Buka shift dengan modal kas |
| `POST /api/shift/tutup` | Tutup shift + hitung selisih |
| `POST /api/sync` | Terima transaksi offline |

---

## ✅ Rekap Fitur (3 Fase)

### Fase 1 — Inti
| # | Fitur |
|---|-------|
| 1 | **Dashboard** — statistik real-time, polling 30 detik |
| 2 | **Kasir POS** — katalog, keranjang, kembalian, struk thermal 58mm |
| 3 | **Manajemen Produk** — CRUD, filter kategori, badge stok rendah |
| 4 | **Offline Mode** — IndexedDB + Service Worker + auto-sync |
| 5 | **Auth RBAC** — login session, role Admin / Kasir |
| 6 | **Laporan Transaksi** — filter, rekap, detail item per transaksi |
| 7 | **Manajemen User** — tambah/edit/nonaktifkan kasir, last login |
| 8 | **Pengaturan Toko** — nama, alamat, pajak, printer, preview struk |

### Fase 2 — Lanjutan
| # | Fitur |
|---|-------|
| 9  | **Scan Barcode** — USB/Bluetooth scanner, buffer 120ms, lookup produk |
| 10 | **Diskon** — panel % + nominal, quick buttons 5/10/15/20% |
| 11 | **Manajemen Stok** — penerimaan stok, riwayat, stok rendah, supplier CRUD |
| 12 | **Grafik Dashboard** — Chart.js: tren, metode bayar, top 10 produk |
| 13 | **Export CSV** — client-side & server-side dengan filter tanggal |
| 14 | **Multi-kasir** — cashier_id per transaksi, session terpisah |
| 15 | **Shift Kasir** — buka/tutup shift, selisih kas otomatis, riwayat |

### Fase 3 — Premium
| # | Fitur |
|---|-------|
| 16 | **Pelanggan & Member** — CRUD, auto kode MBR-00001, cari dari kasir |
| 17 | **Loyalty Points** — earn/redeem poin per transaksi, riwayat, adjust manual |
| 18 | **Voucher & Promo** — kode unik, % atau Rp, batas pakai, masa berlaku |
| 19 | **Retur Transaksi** — cari by invoice, pilih item, stok kembali otomatis |
| 20 | **Backup & Export** — transaksi CSV/JSON, produk CSV, pelanggan CSV |

---

## ⚙️ Pengaturan (Tabel `settings`)

| Key | Default | Keterangan |
|-----|---------|------------|
| `store_name` | POS SUMBA | Nama toko |
| `store_address` | Sumba, NTT | Alamat toko |
| `tax_percentage` | 0 | Pajak % |
| `receipt_footer` | Terima kasih... | Footer struk |
| `printer_width` | 58 | Lebar kertas mm |
| `low_stock_alert` | 10 | Batas stok rendah |
| `discount_max_pct` | 100 | Maks diskon % |
| `loyalty_active` | 1 | Aktifkan loyalty |
| `loyalty_points_rate` | 1000 | Rp per 1 poin |
| `loyalty_redeem_rate` | 100 | Nilai 1 poin (Rp) |
| `voucher_active` | 1 | Aktifkan voucher |
| `grafik_hari` | 7 | Hari tampil di grafik |

---

## 🌐 Deployment (Railway.app)

```bash
# Procfile (wajib ada)
web: python app.py
```

```python
# app.py — pastikan ini ada
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)
```

Tambahkan semua variabel `.env` ke **Variables** di dashboard Railway.

---

## 🎨 Desain

Dark theme — warna utama:

| Token | Nilai | Digunakan untuk |
|-------|-------|-----------------|
| `--bg` | `#232323` | Background utama |
| `--card-bg` | `#2D2D2D` | Card & sidebar |
| `--hover` | `#353535` | Hover state |
| `--accent` | `#1F69A4` | Tombol, link, aktif |
| `--success` | `#27AE60` | Status berhasil |
| `--danger` | `#E74C3C` | Error, hapus |
| Font | Montserrat | UI umum |
| Mono | JetBrains Mono | Angka, kode, harga |