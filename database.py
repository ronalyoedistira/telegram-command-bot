"""
Modul database sederhana pakai SQLite (bawaan Python, tidak perlu install apa pun).

Tabel `transaksi`:
- id            : nomor urut otomatis
- user_id       : ID Telegram pengguna yang mencatat transaksi
- jenis         : 'masuk' atau 'keluar'
- jumlah        : nominal (integer, dalam Rupiah)
- kategori      : label kategori bebas, contoh 'Makanan', 'Transport', 'Gaji' (default 'Umum')
- keterangan    : catatan bebas
- waktu         : timestamp otomatis saat dicatat

DB_PATH bisa diatur lewat environment variable DB_PATH — berguna untuk Railway Volume
(supaya data tidak hilang saat redeploy). Kalau tidak diatur, default ke file lokal 'data.db'.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "data.db")

KATEGORI_DEFAULT = "Umum"


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
    """Buat tabel kalau belum ada, dan migrasi otomatis kalau tabel lama belum punya kolom kategori.
    Aman dipanggil berkali-kali (idempotent)."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                jenis TEXT NOT NULL CHECK (jenis IN ('masuk', 'keluar')),
                jumlah INTEGER NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'Umum',
                keterangan TEXT,
                waktu TEXT NOT NULL
            )
            """
        )

        # --- Migrasi untuk database LAMA (v4 ke bawah) yang belum punya kolom kategori ---
        kolom_sekarang = [row["name"] for row in conn.execute("PRAGMA table_info(transaksi)")]
        if "kategori" not in kolom_sekarang:
            conn.execute(
                f"ALTER TABLE transaksi ADD COLUMN kategori TEXT NOT NULL DEFAULT '{KATEGORI_DEFAULT}'"
            )


def tambah_transaksi(
    user_id: int, jenis: str, jumlah: int, keterangan: str, kategori: str = KATEGORI_DEFAULT
) -> int:
    """Menyimpan satu transaksi baru. Mengembalikan id transaksi yang baru dibuat."""
    kategori = kategori.strip() if kategori and kategori.strip() else KATEGORI_DEFAULT
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO transaksi (user_id, jenis, jumlah, kategori, keterangan, waktu) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, jenis, jumlah, kategori, keterangan, datetime.now().isoformat(timespec="seconds")),
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


def get_laporan_per_kategori(user_id: int, hari: int = 30) -> list:
    """Ringkasan pengeluaran & pemasukan per kategori dalam N hari terakhir.
    Diurutkan dari total transaksi (masuk+keluar) terbesar."""
    batas_waktu = (datetime.now() - timedelta(days=hari)).isoformat(timespec="seconds")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                kategori,
                COALESCE(SUM(CASE WHEN jenis = 'masuk' THEN jumlah ELSE 0 END), 0) AS total_masuk,
                COALESCE(SUM(CASE WHEN jenis = 'keluar' THEN jumlah ELSE 0 END), 0) AS total_keluar,
                COUNT(*) AS jumlah_transaksi
            FROM transaksi
            WHERE user_id = ? AND waktu >= ?
            GROUP BY kategori
            ORDER BY (total_masuk + total_keluar) DESC
            """,
            (user_id, batas_waktu),
        ).fetchall()
        return [dict(r) for r in rows]


def get_transaksi_terakhir(user_id: int, limit: int = 5) -> list:
    """Ambil N transaksi terbaru milik user_id, urut dari yang paling baru."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, jenis, jumlah, kategori, keterangan, waktu FROM transaksi "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_semua_transaksi(user_id: int) -> list:
    """Ambil SEMUA transaksi milik user_id (untuk /daftar dan /export), urut dari yang paling baru."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, jenis, jumlah, kategori, keterangan, waktu FROM transaksi "
            "WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_transaksi_by_id(transaksi_id: int, user_id: int) -> Optional[dict]:
    """Ambil satu transaksi spesifik berdasarkan id, HANYA kalau milik user_id ini.
    Mengembalikan None kalau tidak ditemukan atau bukan milik user tersebut."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, jenis, jumlah, kategori, keterangan, waktu FROM transaksi "
            "WHERE id = ? AND user_id = ?",
            (transaksi_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def update_transaksi(
    transaksi_id: int,
    user_id: int,
    jumlah: Optional[int] = None,
    keterangan: Optional[str] = None,
    kategori: Optional[str] = None,
) -> bool:
    """Ubah jumlah, keterangan, dan/atau kategori sebuah transaksi. Hanya bisa untuk transaksi milik user_id ini.
    Mengembalikan True kalau berhasil (baris ditemukan & diubah), False kalau tidak ditemukan."""
    existing = get_transaksi_by_id(transaksi_id, user_id)
    if existing is None:
        return False

    jumlah_baru = jumlah if jumlah is not None else existing["jumlah"]
    keterangan_baru = keterangan if keterangan is not None else existing["keterangan"]
    kategori_baru = kategori if kategori is not None else existing["kategori"]

    with get_connection() as conn:
        conn.execute(
            "UPDATE transaksi SET jumlah = ?, keterangan = ?, kategori = ? WHERE id = ? AND user_id = ?",
            (jumlah_baru, keterangan_baru, kategori_baru, transaksi_id, user_id),
        )
    return True


def hapus_transaksi_by_id(transaksi_id: int, user_id: int) -> bool:
    """Hapus satu transaksi spesifik. Hanya bisa untuk transaksi milik user_id ini.
    Mengembalikan True kalau berhasil dihapus, False kalau tidak ditemukan."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM transaksi WHERE id = ? AND user_id = ?",
            (transaksi_id, user_id),
        )
        return cursor.rowcount > 0


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
