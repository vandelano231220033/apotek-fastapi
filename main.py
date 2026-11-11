"""main.py - Inisialisasi aplikasi FastAPI dan registrasi router."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import database as db
from routes import resource, transaction


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dijalankan sekali per worker saat start: pastikan tabel tersedia.
    await db.init_db()
    yield


app = FastAPI(
    title="API Apotek - UTS Komputasi Paralel dan Terdistribusi",
    description="CRUD obat + transaksi asinkron (BackgroundTasks) + asyncio.Lock.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(resource.router)
app.include_router(transaction.router)


@app.get("/", tags=["Root"])
async def root():
    return {"app": "API Apotek", "docs": "/docs", "lock_aktif": transaction.USE_LOCK}
