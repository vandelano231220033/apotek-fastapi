"""
seed.py - Inisialisasi data awal (12 obat).

  python seed.py            # isi data bila tabel masih kosong
  python seed.py --reset    # kosongkan semua data lalu isi ulang

ID 1 (Paracetamol)  : stok 100    -> dipakai demo race condition (diset 1)
ID 2 (Vitamin C)    : stok 100000 -> dipakai pengujian beban POST /transactions
"""
import asyncio
import sys

import database as db

DATA = [
    ("Paracetamol 500 mg", "Analgesik", "Kimia Farma", 5000, 100),
    ("Vitamin C 500 mg", "Suplemen", "Kalbe Farma", 12000, 100000),
    ("Amoxicillin 500 mg", "Antibiotik", "Sanbe Farma", 15000, 80),
    ("Ibuprofen 400 mg", "Analgesik", "Dexa Medica", 9000, 120),
    ("Cetirizine 10 mg", "Antihistamin", "Hexpharm", 7000, 90),
    ("Antasida Doen", "Antasida", "Indofarma", 3500, 200),
    ("Oralit", "Rehidrasi", "Indofarma", 2500, 300),
    ("Loperamide 2 mg", "Antidiare", "Kimia Farma", 4500, 60),
    ("OBH Combi 100 ml", "Batuk", "Combiphar", 18000, 45),
    ("Betadine 30 ml", "Antiseptik", "Mundipharma", 14000, 70),
    ("Salbutamol 2 mg", "Bronkodilator", "Kalbe Farma", 6000, 50),
    ("Multivitamin Anak", "Suplemen", "Sanbe Farma", 22000, 40),
]


async def main() -> None:
    await db.init_db()
    if "--reset" in sys.argv:
        await db.reset_all()
        print("Data lama dihapus.")
    if await db.count_obat() > 0:
        print("Tabel obat sudah berisi data; lewati (pakai --reset untuk mengulang).")
        return
    for nama, kategori, produsen, harga, stok in DATA:
        await db.insert_obat(
            {"nama": nama, "kategori": kategori, "produsen": produsen,
             "harga": harga, "stok": stok}
        )
    print(f"Berhasil menambahkan {len(DATA)} data obat.")


if __name__ == "__main__":
    asyncio.run(main())
