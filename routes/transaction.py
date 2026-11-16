"""routes/transaction.py - Endpoint transaksi: BackgroundTasks + asyncio.Lock."""
import asyncio
import os
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

import database as db
from models import TransactionAccepted, TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transaksi"])

# Saklar untuk demonstrasi B3:
#   USE_LOCK=0 -> Tahap 1 (tanpa lock, race condition terlihat)
#   USE_LOCK=1 -> Tahap 2 (dengan asyncio.Lock) -- default
USE_LOCK = os.getenv("USE_LOCK", "1") != "0"

# Durasi simulasi pekerjaan I/O di latar belakang (detik).
PROCESS_DELAY = 3

# asyncio.Lock di tingkat modul: SATU gembok bersama untuk seluruh coroutine di
# dalam proses ini. Hanya mengunci antar-coroutine pada event loop yang sama,
# bukan antar-proses (setiap worker Uvicorn punya gembok sendiri).
stok_lock = asyncio.Lock()


# ----------------------------------------------------------- B3: pemotongan stok
async def potong_stok_tanpa_lock(item_id: int, qty: int) -> bool:
    """VERSI 1 (rentan race condition): read -> jeda -> check -> write."""
    stok_terkini = await db.get_stok(item_id)
    if stok_terkini is None:
        return False

    # Jeda buatan: event loop berpindah ke request lain di sini, sehingga
    # request kedua membaca stok LAMA yang sama sebelum sempat diperbarui.
    await asyncio.sleep(0.01)

    if stok_terkini < qty:
        return False

    await db.decrement_stok(item_id, qty)  # kedua request lolos -> stok minus
    return True


async def potong_stok_dengan_lock(item_id: int, qty: int) -> bool:
    """VERSI 2 (aman): seluruh critical section dilindungi asyncio.Lock."""
    # Hanya satu coroutine pada satu waktu yang boleh berada di blok ini.
    # Coroutine lain menunggu (await) di baris 'async with' tanpa memblokir
    # event loop, lalu membaca stok yang sudah diperbarui.
    async with stok_lock:
        stok_terkini = await db.get_stok(item_id)
        if stok_terkini is None:
            return False

        await asyncio.sleep(0.01)  # jeda yang sama dengan versi 1

        if stok_terkini < qty:
            return False

        # Pengaman kedua di level SQL (UPDATE ... WHERE stok >= qty): menjaga
        # konsistensi walau ada beberapa worker (proses) yang tidak berbagi lock.
        return await db.decrement_stok_atomic(item_id, qty)


async def potong_stok(item_id: int, qty: int) -> bool:
    if USE_LOCK:
        return await potong_stok_dengan_lock(item_id, qty)
    return await potong_stok_tanpa_lock(item_id, qty)


# ------------------------------------------------------ pekerja latar belakang
# Fungsi internal Python (BUKAN endpoint HTTP). Dijalankan FastAPI SETELAH
# respon dikirim ke klien, sehingga POST /transactions tidak menunggu 3 detik.
async def proses_transaksi_background(trx_id: int, item_id: int, qty: int) -> None:
    try:
        # 1. pending -> processing
        await db.update_trx_status(trx_id, "processing")

        # 2. Simulasi pekerjaan I/O intensif; await melepas kendali ke event loop.
        await asyncio.sleep(PROCESS_DELAY)

        # 3. processing -> completed
        await db.update_trx_status(trx_id, "completed", "Transaksi selesai")
    except Exception as exc:  # noqa: BLE001
        # Gagal: kembalikan stok yang sudah dipotong, tandai failed.
        await db.increment_stok(item_id, qty)
        await db.update_trx_status(trx_id, "failed", f"Gagal diproses: {exc}")


# ------------------------------------------------------------------ endpoint
@router.post(
    "", response_model=TransactionAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def create_transaction(data: TransactionCreate, bg: BackgroundTasks):
    # Validasi: resource harus terdaftar.
    obat = await db.get_obat(data.item_id)
    if obat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obat tidak terdaftar")

    # Validasi: stok mencukupi + potong stok (critical section, lihat di atas).
    if not await potong_stok(data.item_id, data.qty):
        raise HTTPException(status.HTTP_409_CONFLICT, "Stok habis atau tidak mencukupi")

    try:
        trx_id = await db.insert_transaction(
            data.item_id, data.qty, obat["harga"] * data.qty, status="pending"
        )
    except Exception:
        await db.increment_stok(data.item_id, data.qty)  # batalkan pemotongan
        raise

    # Jadwalkan pekerja latar belakang; respon langsung dikembalikan (pending).
    bg.add_task(proses_transaksi_background, trx_id, data.item_id, data.qty)
    return {"id": trx_id, "status": "pending", "message": "Transaksi diproses"}


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    status_filter: Literal["pending", "processing", "completed", "failed"] | None = Query(
        None, alias="status", description="Filter status transaksi"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await db.list_transactions(status_filter, skip, limit)


@router.get("/{trx_id}", response_model=TransactionResponse)
async def get_transaction(trx_id: int):
    trx = await db.get_transaction(trx_id)
    if trx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaksi tidak ditemukan")
    return trx
