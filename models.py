"""models.py - Skema Pydantic untuk validasi request dan serialisasi response."""
from typing import Literal

from pydantic import BaseModel, Field

StatusTransaksi = Literal["pending", "processing", "completed", "failed"]


class ObatBase(BaseModel):
    nama: str = Field(..., min_length=1, max_length=100, examples=["Paracetamol 500 mg"])
    kategori: str = Field(..., min_length=1, max_length=50, examples=["Analgesik"])
    produsen: str = Field(..., min_length=1, max_length=100, examples=["Kimia Farma"])
    harga: float = Field(..., gt=0, examples=[5000])
    stok: int = Field(..., ge=0, examples=[100])


class ObatCreate(ObatBase):
    """Body untuk POST /obat."""


class ObatUpdate(ObatBase):
    """Body untuk PUT /obat/{id} (pembaruan penuh)."""


class ObatResponse(ObatBase):
    id: int


class TransactionCreate(BaseModel):
    item_id: int = Field(..., gt=0, examples=[1])
    qty: int = Field(..., gt=0, examples=[1])


class TransactionAccepted(BaseModel):
    """Respon instan POST /transactions."""
    id: int
    status: StatusTransaksi
    message: str


class TransactionResponse(BaseModel):
    id: int
    item_id: int
    qty: int
    total_harga: float
    status: StatusTransaksi
    pesan: str | None = None
    created_at: str
    updated_at: str
