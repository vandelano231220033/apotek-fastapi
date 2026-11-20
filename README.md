Video Presentasi : https://youtu.be/1B6ocw4n5RI

# API Apotek - UTS Komputasi Paralel dan Terdistribusi (Ganjil 2026/2027)

REST API manajemen apotek berbasis **FastAPI + SQLite (aiosqlite)**.
Resource utama: **obat** (`/obat`). Resource transaksi: **penjualan** (`/transactions`).
Mendemonstrasikan `async/await`, `BackgroundTasks`, `asyncio.Lock`, dan multi-worker Uvicorn.

- Nama / NIM : Vandelano Agissa Kalevi / 231220033
- Dosen      : Yulrio Brianorman, S.Si., M.T.

## Struktur

```
main.py            inisialisasi FastAPI + registrasi router
database.py        koneksi aiosqlite, skema, operasi DB
models.py          skema Pydantic
routes/resource.py     CRUD obat
routes/transaction.py  transaksi async + pemotongan stok (lock / tanpa lock)
seed.py            12 data awal
test_race.py       uji race condition (2 request serentak)
locustfile.py      uji beban (ReadUser, WriteUser)
docs/              laporan_uts.pdf + build_report.py
```

## Instalasi

Python 3.10+.

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate        Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python seed.py            # isi 12 data awal (python seed.py --reset untuk mengulang)
```

## Menjalankan

```bash
uvicorn main:app --port 8000
```
Swagger UI: http://127.0.0.1:8000/docs

## Endpoint

| Method | Path | Keterangan |
|---|---|---|
| GET | `/obat?skip=0&limit=10` | Daftar obat (paginasi) |
| GET | `/obat/{id}` | Detail obat (404 bila tidak ada) |
| POST | `/obat` | Tambah obat (201; 422 bila tidak valid) |
| PUT | `/obat/{id}` | Perbarui obat, mengembalikan data terbaru |
| DELETE | `/obat/{id}` | Hapus permanen (hard delete) |
| POST | `/transactions` | Buat transaksi, respon `pending` instan (202); 404 obat tidak ada; 409 stok habis |
| GET | `/transactions?status=pending` | Daftar transaksi, filter status |
| GET | `/transactions/{id}` | Detail + status terkini |

Alur status: `pending -> processing -> completed / failed` (diproses `BackgroundTasks`, `asyncio.sleep(3)`).

## B3 - Uji race condition

Saklar lewat variabel lingkungan `USE_LOCK`.

**Tahap 1 - tanpa lock** (harapan: kedua 202, stok akhir -1):

```bash
# Linux/macOS
USE_LOCK=0 uvicorn main:app --port 8000
# Windows PowerShell
$env:USE_LOCK="0"; uvicorn main:app --port 8000
# Windows CMD
set USE_LOCK=0 && uvicorn main:app --port 8000
```
Terminal 2: `python test_race.py` -> tangkap layar, simpan sebagai `docs/ss_tanpa_lock.png`.

**Tahap 2 - dengan lock** (harapan: satu 202, satu 409, stok akhir 0):

```bash
uvicorn main:app --port 8000        # USE_LOCK default = 1
python test_race.py
```
Simpan tangkapan layar sebagai `docs/ss_dengan_lock.png`.

`test_race.py` otomatis mengatur stok item 1 menjadi 1 sebelum menguji.

## C1 - Benchmark 1 vs 4 worker

Untuk setiap jumlah worker (1 lalu 4), jalankan server:

```bash
uvicorn main:app --workers 1 --port 8000     # lalu --workers 4
```
Lalu pada terminal lain:

```bash
python seed.py --reset    # stok item 2 = 100000 (cukup untuk 50 transaksi)
locust -f locustfile.py ReadUser  --headless -u 20 -r 20 --host http://127.0.0.1:8000
locust -f locustfile.py WriteUser --headless -u 10 -r 10 --host http://127.0.0.1:8000
```
Locust berhenti otomatis setelah 100 (read) / 50 (write) request dan mencetak
**RINGKASAN** (total waktu, throughput, rata-rata latensi). Catat ke `docs/benchmark.json`.

## Laporan PDF

```bash
# 1. isi docs/laporan_config.json (nama, NIM, link) dan docs/benchmark.json
# 2. taruh docs/ss_tanpa_lock.png dan docs/ss_dengan_lock.png
python docs/build_report.py      # -> docs/laporan_uts.pdf
```

## Catatan desain

- Kolom `stok` sengaja tanpa `CHECK (stok >= 0)` agar overselling pada Tahap 1 terlihat; validasi dilakukan di aplikasi.
- Pemotongan stok dilakukan **saat POST** (sebelum respon) sehingga penolakan 409 bisa dikembalikan langsung. Background task hanya menangani `processing -> completed/failed` (stok dikembalikan bila failed).
- `asyncio.Lock` hanya berlaku dalam satu proses. Agar tetap benar pada multi-worker, versi berlock memakai juga `UPDATE ... WHERE stok >= qty` (atomik di SQLite).
