"""
database.py - Koneksi aiosqlite, skema tabel, dan seluruh operasi basis data.

Semua fungsi bersifat async (non-blocking): selama menunggu I/O SQLite, event
loop bebas melayani request lain. Setiap operasi membuka koneksi sendiri
sehingga aman dipakai oleh banyak coroutine dan oleh banyak worker Uvicorn
(banyak proses). Mode WAL + busy_timeout dipakai agar penulisan dari beberapa
proses saling menunggu, bukan langsung gagal dengan "database is locked".
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "apotek.db"),
)

# Catatan desain: kolom stok SENGAJA tanpa CHECK (stok >= 0).
# Tahap 1 pada B3 (tanpa lock) wajib memperlihatkan stok akhir NEGATIF
# (overselling); constraint CHECK akan menggagalkan demonstrasi itu.
# Validasi stok tidak negatif dilakukan di lapisan aplikasi (Pydantic ge=0
# untuk input, pemeriksaan stok sebelum pemotongan untuk transaksi).
CREATE_RESOURCE_TABLE = """
CREATE TABLE IF NOT EXISTS obat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    kategori TEXT NOT NULL,
    produsen TEXT NOT NULL,
    harga REAL NOT NULL,
    stok INTEGER NOT NULL          -- Kolom kuantitas wajib
);
"""

CREATE_TRANSACTION_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    total_harga REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    pesan TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@asynccontextmanager
async def get_db():
    """Buka koneksi aiosqlite (async) dengan row_factory dict-like."""
    async with aiosqlite.connect(DB_PATH, timeout=30) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA busy_timeout = 30000")
        yield conn


async def init_db() -> None:
    """Buat tabel bila belum ada. Aman dipanggil oleh setiap worker."""
    async with get_db() as conn:
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute(CREATE_RESOURCE_TABLE)
        await conn.execute(CREATE_TRANSACTION_TABLE)
        await conn.commit()


async def reset_all() -> None:
    """Kosongkan seluruh data (dipakai seed.py --reset)."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM transactions")
        await conn.execute("DELETE FROM obat")
        await conn.execute("DELETE FROM sqlite_sequence")
        await conn.commit()


# ----------------------------------------------------------------- RESOURCE
async def list_obat(skip: int, limit: int) -> list[dict]:
    async with get_db() as conn:
        cur = await conn.execute(
            "SELECT * FROM obat ORDER BY id LIMIT ? OFFSET ?", (limit, skip)
        )
        return [dict(r) for r in await cur.fetchall()]


async def count_obat() -> int:
    async with get_db() as conn:
        cur = await conn.execute("SELECT COUNT(*) AS n FROM obat")
        return (await cur.fetchone())["n"]


async def get_obat(obat_id: int) -> dict | None:
    async with get_db() as conn:
        cur = await conn.execute("SELECT * FROM obat WHERE id = ?", (obat_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def insert_obat(d: dict) -> int:
    async with get_db() as conn:
        cur = await conn.execute(
            "INSERT INTO obat (nama, kategori, produsen, harga, stok) "
            "VALUES (?, ?, ?, ?, ?)",
            (d["nama"], d["kategori"], d["produsen"], d["harga"], d["stok"]),
        )
        await conn.commit()
        return cur.lastrowid


async def update_obat(obat_id: int, d: dict) -> bool:
    async with get_db() as conn:
        cur = await conn.execute(
            "UPDATE obat SET nama=?, kategori=?, produsen=?, harga=?, stok=? "
            "WHERE id=?",
            (d["nama"], d["kategori"], d["produsen"], d["harga"], d["stok"], obat_id),
        )
        await conn.commit()
        return cur.rowcount > 0


async def delete_obat(obat_id: int) -> bool:
    """Hard delete: baris dihapus permanen dari basis data."""
    async with get_db() as conn:
        cur = await conn.execute("DELETE FROM obat WHERE id = ?", (obat_id,))
        await conn.commit()
        return cur.rowcount > 0


# --------------------------------------------------------------------- STOK
async def get_stok(item_id: int) -> int | None:
    async with get_db() as conn:
        cur = await conn.execute("SELECT stok FROM obat WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        return row["stok"] if row else None


async def decrement_stok(item_id: int, qty: int) -> None:
    """Pemotongan stok relatif TANPA pengaman (dipakai versi tanpa lock)."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE obat SET stok = stok - ? WHERE id = ?", (qty, item_id)
        )
        await conn.commit()


async def decrement_stok_atomic(item_id: int, qty: int) -> bool:
    """
    Pemotongan stok atomik di level SQL: hanya berhasil bila stok >= qty.
    Dipakai bersama asyncio.Lock sebagai lapis pengaman kedua, karena
    asyncio.Lock hanya berlaku di dalam SATU proses (lihat laporan, analisis
    multi-worker).
    """
    async with get_db() as conn:
        cur = await conn.execute(
            "UPDATE obat SET stok = stok - ? WHERE id = ? AND stok >= ?",
            (qty, item_id, qty),
        )
        await conn.commit()
        return cur.rowcount == 1


async def increment_stok(item_id: int, qty: int) -> None:
    """Kembalikan stok (dipakai bila transaksi berstatus failed)."""
    async with get_db() as conn:
        await conn.execute(
            "UPDATE obat SET stok = stok + ? WHERE id = ?", (qty, item_id)
        )
        await conn.commit()


# ---------------------------------------------------------------- TRANSAKSI
async def insert_transaction(
    item_id: int, qty: int, total_harga: float, status: str = "pending"
) -> int:
    now = _now()
    async with get_db() as conn:
        cur = await conn.execute(
            "INSERT INTO transactions "
            "(item_id, qty, total_harga, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, qty, total_harga, status, now, now),
        )
        await conn.commit()
        return cur.lastrowid


async def update_trx_status(
    trx_id: int, status: str, pesan: str | None = None
) -> None:
    async with get_db() as conn:
        await conn.execute(
            "UPDATE transactions SET status=?, pesan=COALESCE(?, pesan), "
            "updated_at=? WHERE id=?",
            (status, pesan, _now(), trx_id),
        )
        await conn.commit()


async def get_transaction(trx_id: int) -> dict | None:
    async with get_db() as conn:
        cur = await conn.execute("SELECT * FROM transactions WHERE id = ?", (trx_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_transactions(
    status: str | None, skip: int, limit: int
) -> list[dict]:
    async with get_db() as conn:
        if status:
            cur = await conn.execute(
                "SELECT * FROM transactions WHERE status = ? "
                "ORDER BY id DESC LIMIT ? OFFSET ?",
                (status, limit, skip),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM transactions ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, skip),
            )
        return [dict(r) for r in await cur.fetchall()]
