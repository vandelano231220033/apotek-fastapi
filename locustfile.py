"""
locustfile.py - Pengujian beban sesuai soal C1.

  Skenario Read : GET /obat          100 request, konkurensi 20
  Skenario Write: POST /transactions  50 request, konkurensi 10

Setiap skenario dijalankan sebagai kelas terpisah dan BERHENTI OTOMATIS setelah
jumlah request tercapai, lalu mencetak ringkasan (total waktu, throughput,
rata-rata latensi) siap dimasukkan ke tabel laporan.

  locust -f locustfile.py ReadUser  --headless -u 20 -r 20 --host http://127.0.0.1:8000
  locust -f locustfile.py WriteUser --headless -u 10 -r 10 --host http://127.0.0.1:8000
"""
import os

import gevent
from locust import HttpUser, constant, events, task

READ_TOTAL = int(os.getenv("READ_TOTAL", "100"))
WRITE_TOTAL = int(os.getenv("WRITE_TOTAL", "50"))
LOAD_ITEM_ID = int(os.getenv("LOAD_ITEM_ID", "2"))  # item ber-stok besar (seed.py)

_env = None
_sent = {"read": 0, "write": 0}
_done = {"read": 0, "write": 0}
_limit = {"read": READ_TOTAL, "write": WRITE_TOTAL}
_label = {"GET /obat": "read", "POST /transactions": "write"}


@events.init.add_listener
def _on_init(environment, **kwargs):
    global _env
    _env = environment


def _claim(kind: str) -> bool:
    """Ambil 'jatah' request; False bila kuota skenario sudah habis."""
    if _sent[kind] >= _limit[kind]:
        return False
    _sent[kind] += 1
    return True


@events.request.add_listener
def _on_request(name, **kwargs):
    kind = _label.get(name)
    if kind is None:
        return
    _done[kind] += 1
    if _done[kind] >= _limit[kind] and _env and _env.runner:
        gevent.spawn(_env.runner.quit)  # semua request selesai -> hentikan tes


class ReadUser(HttpUser):
    wait_time = constant(0)

    @task
    def get_obat(self):
        if not _claim("read"):
            gevent.sleep(0.05)
            return
        self.client.get("/obat?skip=0&limit=10", name="GET /obat")


class WriteUser(HttpUser):
    wait_time = constant(0)

    @task
    def post_transaksi(self):
        if not _claim("write"):
            gevent.sleep(0.05)
            return
        self.client.post(
            "/transactions",
            json={"item_id": LOAD_ITEM_ID, "qty": 1},
            name="POST /transactions",
        )


@events.quitting.add_listener
def _summary(environment, **kwargs):
    t = environment.stats.total
    if not t.num_requests:
        return
    durasi = max(t.last_request_timestamp - t.start_time, 1e-9)
    print("\n===== RINGKASAN (salin ke tabel laporan) =====")
    print(f"Total request     : {t.num_requests} (gagal: {t.num_failures})")
    print(f"Total waktu       : {durasi:.2f} detik")
    print(f"Throughput        : {t.num_requests / durasi:.2f} req/detik")
    print(f"Rata-rata latensi : {t.avg_response_time:.2f} ms")
    print("==============================================")
