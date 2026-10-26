"""Kết nối SQLite và các truy vấn dùng chung."""
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def get_cau_hinh(conn, khoa: str) -> int:
    row = conn.execute("SELECT gia_tri FROM cau_hinh WHERE khoa = ?", (khoa,)).fetchone()
    return int(row["gia_tri"]) if row else 0


def set_cau_hinh(conn, khoa: str, gia_tri: int) -> None:
    conn.execute(
        "INSERT INTO cau_hinh (khoa, gia_tri) VALUES (?, ?) "
        "ON CONFLICT(khoa) DO UPDATE SET gia_tri = excluded.gia_tri",
        (khoa, str(gia_tri)),
    )
    conn.commit()


def danh_sach_phong(conn):
    """Danh sách phòng kèm số người đang ở và trạng thái."""
    return conn.execute(
        """
        SELECT p.*,
               (SELECT COUNT(*) FROM nguoi_thue n
                 WHERE n.phong_id = p.id AND n.ngay_ra IS NULL) AS so_nguoi_o
        FROM phong p ORDER BY p.so_phong
        """
    ).fetchall()


def chi_so_truoc(conn, phong_id: int, truoc_ngay: str):
    """Chỉ số gần nhất có ngày ghi <= truoc_ngay (dùng làm chỉ số cũ)."""
    return conn.execute(
        "SELECT * FROM chi_so WHERE phong_id = ? AND ngay_ghi <= ? "
        "ORDER BY ngay_ghi DESC LIMIT 1",
        (phong_id, truoc_ngay),
    ).fetchone()
