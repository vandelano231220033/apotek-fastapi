"""routes/resource.py - Endpoint CRUD resource utama (Obat)."""
from fastapi import APIRouter, HTTPException, Query, status

import database as db
from models import ObatCreate, ObatResponse, ObatUpdate

router = APIRouter(prefix="/obat", tags=["Obat (resource utama)"])


# Handler async: saat menunggu SQLite (await), event loop melayani request lain.
@router.get("", response_model=list[ObatResponse])
async def list_obat(
    skip: int = Query(0, ge=0, description="Jumlah data yang dilewati"),
    limit: int = Query(10, ge=1, le=100, description="Jumlah data maksimum"),
):
    return await db.list_obat(skip, limit)


@router.get("/{obat_id}", response_model=ObatResponse)
async def get_obat(obat_id: int):
    obat = await db.get_obat(obat_id)
    if obat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obat tidak ditemukan")
    return obat


@router.post("", response_model=ObatResponse, status_code=status.HTTP_201_CREATED)
async def create_obat(data: ObatCreate):
    new_id = await db.insert_obat(data.model_dump())
    return await db.get_obat(new_id)


@router.put("/{obat_id}", response_model=ObatResponse)
async def update_obat(obat_id: int, data: ObatUpdate):
    if not await db.update_obat(obat_id, data.model_dump()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obat tidak ditemukan")
    return await db.get_obat(obat_id)  # kembalikan data terbaru


@router.delete("/{obat_id}")
async def delete_obat(obat_id: int):
    if not await db.delete_obat(obat_id):  # hard delete
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Obat tidak ditemukan")
    return {"message": "Obat dihapus permanen", "id": obat_id}
