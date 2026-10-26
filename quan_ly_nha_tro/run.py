"""Chạy: python run.py  → mở http://127.0.0.1:5000"""
import os

from nhatro.app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("NHATRO_HOST", "127.0.0.1")   # đặt 0.0.0.0 để truy cập từ điện thoại trong LAN
    app.run(host=host, port=int(os.environ.get("NHATRO_PORT", "5000")), debug=False)
