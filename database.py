"""
Modul database sederhana pakai SQLite (bawaan Python, tidak perlu install apa pun).

Tabel `transaksi`:
- id            : nomor urut otomatis
- user_id       : ID Telegram pengguna yang mencatat transaksi
- jenis         : 'masuk' atau 'keluar'
- jumlah        : nominal (integer, dalam Rupiah)
- keterangan    : catatan bebas
- waktu         : timestamp otomatis saat dicatat
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_PATH = "data.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Buat tabel kalau belum ada. Dipanggil sekali saat bot.py mulai."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                jenis TEXT NOT NULL CHECK (jenis IN ('masuk', 'keluar')),
                jumlah INTEGER NOT NULL,
                keterangan TEXT,
                waktu TEXT NOT NULL
            )
            """
        )


def tambah_transaksi(user_id: int, jenis: str, jumlah: int, keterangan: str) -> int:
    """Menyimpan satu transaksi baru. Mengembalikan id transaksi yang baru dibuat."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO transaksi (user_id, jenis, jumlah, keterangan, waktu) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, jenis, jumlah, keterangan, datetime.now().isoformat(timespec="seconds")),
        )
        return cursor.lastrowid


def get_saldo(user_id: int) -> int:
    """Saldo = total masuk - total keluar, khusus milik user_id ini."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN jenis = 'masuk' THEN jumlah ELSE 0 END), 0) AS total_masuk,
                COALESCE(SUM(CASE WHEN jenis = 'keluar' THEN jumlah ELSE 0 END), 0) AS total_keluar
            FROM transaksi
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return row["total_masuk"] - row["total_keluar"]


def get_ringkasan_laporan(user_id: int, hari: int = 30) -> dict:
    """Ringkasan transaksi dalam N hari terakhir (default 30 hari / sebulan)."""
    batas_waktu = (datetime.now() - timedelta(days=hari)).isoformat(timespec="seconds")
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN jenis = 'masuk' THEN jumlah ELSE 0 END), 0) AS total_masuk,
                COALESCE(SUM(CASE WHEN jenis = 'keluar' THEN jumlah ELSE 0 END), 0) AS total_keluar,
                COUNT(*) AS jumlah_transaksi
            FROM transaksi
            WHERE user_id = ? AND waktu >= ?
            """,
            (user_id, batas_waktu),
        ).fetchone()
        return {
            "total_masuk": row["total_masuk"],
            "total_keluar": row["total_keluar"],
            "jumlah_transaksi": row["jumlah_transaksi"],
            "hari": hari,
        }


def get_transaksi_terakhir(user_id: int, limit: int = 5) -> list:
    """Ambil N transaksi terbaru milik user_id, urut dari yang paling baru."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT jenis, jumlah, keterangan, waktu FROM transaksi "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_jumlah_data(user_id: int) -> int:
    """Total jumlah baris transaksi milik user_id (untuk menu Data)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM transaksi WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["total"]


def hapus_semua_data(user_id: int) -> int:
    """Hapus semua transaksi milik user_id. Mengembalikan jumlah baris yang dihapus."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM transaksi WHERE user_id = ?", (user_id,))
        return cursor.rowcount
