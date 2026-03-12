"""
POS SUMBA V.1 - Web Application
Framework: Flask | Database: Supabase
"""

from flask import Flask
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.kasir import kasir_bp
from routes.produk import produk_bp
from routes.sync import sync_bp
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "pos-sumba-secret-2024")

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(kasir_bp)
app.register_blueprint(produk_bp)
app.register_blueprint(sync_bp)  # sudah include route /sw.js

if __name__ == "__main__":
    app.run(debug=True, port=5000)