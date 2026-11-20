"""
test_race.py - Uji race condition: 2 request POST /transactions serentak.

Skrip mengatur stok item menjadi 1 (lewat API), mengirim 2 request bersamaan,
lalu menampilkan stok akhir.

  Tahap 1 (USE_LOCK=0): kedua respon 202, stok akhir -1  -> overselling
  Tahap 2 (USE_LOCK=1): satu respon 202, satu respon 409, stok akhir 0
"""
import asyncio
import os
import sys

import httpx

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
ITEM_ID = int(os.getenv("ITEM_ID", "1"))


async def siapkan_item(client: httpx.AsyncClient) -> int:
    """Pastikan ada item ber-stok 1; bila item tidak ada, buat obat uji baru."""
    r = await client.get(f"{BASE}/obat/{ITEM_ID}")
    if r.status_code == 404:
        baru = {"nama": "Obat Uji Race", "kategori": "Uji", "produsen": "Uji",
                "harga": 1000, "stok": 1}
        r = await client.post(f"{BASE}/obat", json=baru)
        r.raise_for_status()
        item_id = r.json()["id"]
        print(f"Obat ID {ITEM_ID} tidak ada; dibuat obat uji baru dengan ID {item_id}.")
        return item_id
    r.raise_for_status()
    obat = r.json()
    obat.pop("id")
    obat["stok"] = 1
    (await client.put(f"{BASE}/obat/{ITEM_ID}", json=obat)).raise_for_status()
    return ITEM_ID


async def main() -> None:
    url = f"{BASE}/transactions"

    async with httpx.AsyncClient(timeout=30) as client:
        item_id = await siapkan_item(client)
        payload = {"item_id": item_id, "qty": 1}
        print(f"Stok item {item_id} diatur menjadi 1.")

        # Kirim dua request secara serentak (dalam milidetik yang sama).
        req1 = client.post(url, json=payload)
        req2 = client.post(url, json=payload)
        res1, res2 = await asyncio.gather(req1, req2)

        print("Respon Request 1:", res1.status_code, res1.json())
        print("Respon Request 2:", res2.status_code, res2.json())

        stok_akhir = (await client.get(f"{BASE}/obat/{item_id}")).json()["stok"]
        print("Stok akhir:", stok_akhir)

    if stok_akhir < 0:
        print("HASIL: RACE CONDITION - terjadi overselling (stok negatif).")
    elif {res1.status_code, res2.status_code} == {202, 409}:
        print("HASIL: AMAN - satu sukses, satu ditolak 409 Conflict.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        sys.exit("Server belum berjalan. Jalankan: uvicorn main:app --port 8000")
