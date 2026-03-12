# POS SUMBA V.1 — Web App (Flask)

Aplikasi Point of Sale berbasis web menggunakan Python Flask + Supabase.

## 📁 Struktur Folder

```
pos_web/
├── app.py                   # Entry point Flask
├── .env                     # Konfigurasi Supabase (jangan di-commit!)
├── requirements.txt
├── routes/
│   ├── auth.py              # Login & logout
│   ├── dashboard.py         # Halaman dashboard
│   ├── kasir.py             # Halaman kasir + API transaksi
│   └── produk.py            # Manajemen produk & kategori
├── utils/
│   └── supabase_client.py   # Koneksi Supabase
├── templates/
│   ├── base.html            # Layout utama + sidebar
│   ├── login.html           # Halaman login
│   ├── dashboard.html       # Dashboard statistik
│   ├── kasir.html           # Kasir interaktif
│   └── produk.html          # Manajemen produk
└── static/
    ├── css/style.css        # Stylesheet dark theme
    └── js/main.js           # JavaScript utama
```

## 🚀 Cara Menjalankan

```bash
# 1. Install dependensi (ringan, tanpa C++ Build Tools!)
pip install flask requests python-dotenv

# 2. Jalankan aplikasi
python app.py

# 3. Buka browser
# http://localhost:5000
```

## 🔐 Akun Login

| Email | Password | Role |
|-------|----------|------|
| admin@possumba.com | admin123 | Admin |
| kasir@possumba.com | kasir123 | Kasir |

## 📄 Halaman

| URL | Halaman |
|-----|---------|
| `/` atau `/login` | Login |
| `/dashboard` | Dashboard & statistik |
| `/kasir` | Kasir & transaksi |
| `/produk` | Manajemen produk |

## 🎨 Desain

Dark theme sesuai desain Figma POS Sumba:
- Background: `#232323` / `#353535`
- Aksen Biru: `#1F69A4`
- Font: Montserrat + JetBrains Mono
