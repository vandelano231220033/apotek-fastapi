"""
build_report.py - Membuat docs/laporan_uts.pdf (jalankan: python docs/build_report.py)

Masukan (semua opsional; bila belum ada, laporan menampilkan penanda isian):
  docs/laporan_config.json   nama, NIM, tautan repo/video
  docs/benchmark.json        hasil Locust 1 vs 4 worker
  docs/ss_tanpa_lock.png     tangkapan layar Tahap 1 (stok minus)
  docs/ss_dengan_lock.png    tangkapan layar Tahap 2 (satu sukses, satu 409)
"""
import json
import math
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, CondPageBreak)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "laporan_uts.pdf")
NAVY = colors.HexColor("#1F3A68")


def load_json(name, default):
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


CFG = load_json("laporan_config.json", {})
BENCH = load_json("benchmark.json", [])

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                      fontSize=9.5, leading=13, spaceAfter=4, alignment=4)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=14, bulletIndent=3, spaceAfter=2)
H1 = ParagraphStyle("h1", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=12, textColor=NAVY, spaceBefore=8, spaceAfter=4, keepWithNext=1)
H2 = ParagraphStyle("h2", parent=ss["Heading3"], fontName="Helvetica-Bold",
                    fontSize=10, textColor=NAVY, spaceBefore=5, spaceAfter=3, keepWithNext=1)
TITLE = ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=15, textColor=NAVY, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=BODY, alignment=1, fontSize=9.5, spaceAfter=1)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5,
                      alignment=0, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold",
                       textColor=colors.white)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=8.5, alignment=1,
                     textColor=colors.HexColor("#444444"))


def P(t, s=BODY):
    return Paragraph(t, s)


def bullets(items):
    return [Paragraph(t, BUL, bulletText="\u2022") for t in items]


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), CELLB if (header and i == 0) else CELL) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
        st.append(("ROWBACKGROUNDS", (0, 1), (-1, -1),
                   [colors.white, colors.HexColor("#F2F5FA")]))
    t.setStyle(TableStyle(st))
    return t


# ------------------------------------------------------------------ diagram
def arrow(d, x1, y1, x2, y2, dash=None):
    ln = Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#333333"), strokeWidth=1.1)
    if dash:
        ln.strokeDashArray = dash
    d.add(ln)
    a = math.atan2(y2 - y1, x2 - x1)
    s = 5
    pts = [x2, y2,
           x2 - s * math.cos(a - 0.45), y2 - s * math.sin(a - 0.45),
           x2 - s * math.cos(a + 0.45), y2 - s * math.sin(a + 0.45)]
    d.add(Polygon(pts, fillColor=colors.HexColor("#333333"), strokeColor=None))


def box(d, x, y, w, h, lines, fill="#E8EEF9", stroke="#1F3A68", bold_first=True):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=colors.HexColor(fill),
               strokeColor=colors.HexColor(stroke), strokeWidth=1))
    n = len(lines)
    top = y + h / 2 + (n - 1) * 5.5
    for i, t in enumerate(lines):
        d.add(String(x + w / 2, top - i * 11 - 3, t, textAnchor="middle",
                     fontName="Helvetica-Bold" if (i == 0 and bold_first) else "Helvetica",
                     fontSize=8 if i == 0 else 7))


def arch_diagram():
    d = Drawing(480, 245)
    # kontainer FastAPI
    d.add(Rect(268, 105, 205, 135, rx=6, ry=6, fillColor=colors.HexColor("#F7F9FC"),
               strokeColor=colors.HexColor("#1F3A68"), strokeWidth=1.2,
               strokeDashArray=[4, 2]))
    d.add(String(370, 228, "Aplikasi FastAPI (event loop)", textAnchor="middle",
                 fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    box(d, 10, 170, 95, 50, ["Klien", "Swagger UI, Locust,", "test_race.py"], "#FFF4D6", "#9A7B00")
    box(d, 135, 170, 100, 50, ["Uvicorn", "1..N worker (proses)", "tiap proses: 1 event loop"], "#E6F4EA", "#2E7D32")
    box(d, 280, 175, 180, 38, ["routes/resource.py", "CRUD /obat"])
    box(d, 280, 125, 180, 40, ["routes/transaction.py", "POST/GET /transactions"])
    box(d, 270, 40, 95, 45, ["asyncio.Lock", "stok_lock", "(critical section)"], "#FDECEA", "#B3261E")
    box(d, 378, 40, 95, 45, ["BackgroundTasks", "proses_transaksi_", "background"], "#F3E8FD", "#6A1B9A")
    box(d, 130, 25, 110, 70, ["SQLite", "apotek.db (WAL)", "akses via aiosqlite", "tabel: obat, transactions"], "#E3F2FD", "#1565C0")
    arrow(d, 105, 195, 135, 195)
    arrow(d, 235, 195, 268, 195)
    arrow(d, 320, 125, 318, 85)     # transaksi -> lock
    arrow(d, 430, 125, 428, 85)     # transaksi -> background
    arrow(d, 270, 62, 240, 62)      # lock -> sqlite
    arrow(d, 300, 175, 235, 90, dash=[3, 2])  # resource -> sqlite
    arrow(d, 425, 40, 425, 14)
    arrow(d, 425, 14, 185, 14)
    arrow(d, 185, 14, 185, 25)
    d.add(String(327, 92, "(1) potong stok", fontName="Helvetica", fontSize=6.5))
    d.add(String(434, 92, "(2) jadwalkan", fontName="Helvetica", fontSize=6.5))
    d.add(String(205, 17, "(3) update status: processing -> completed/failed", fontName="Helvetica", fontSize=6.5))
    return d


# ---------------------------------------------------------------- screenshot
def screenshot(fname, caption):
    path = os.path.join(HERE, fname)
    if os.path.exists(path):
        iw, ih = ImageReader(path).getSize()
        w = 15.5 * cm
        h = min(ih * w / iw, 5.2 * cm)
        w = iw * h / ih
        img = Image(path, width=w, height=h)
    else:
        img = Table([[P(f"[Tempel tangkapan layar terminal di sini: <b>docs/{fname}</b>]", CAP)]],
                    colWidths=[15.5 * cm], rowHeights=[2.6 * cm])
        img.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.grey),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return KeepTogether([img, P(caption, CAP)])


# ----------------------------------------------------------------- benchmark
def bench_rows():
    def f(v, fmt):
        return "-" if v is None else fmt.format(v)
    rows = [["Skenario", "Worker", "Total Waktu (s)", "Throughput (req/s)", "Rata-rata Latensi (ms)"]]
    if not BENCH:
        BENCH_DEFAULT = [("GET /obat", 1), ("GET /obat", 4),
                         ("POST /transactions", 1), ("POST /transactions", 4)]
        for s, w in BENCH_DEFAULT:
            rows.append([s, w, "-", "-", "-"])
        return rows
    for r in BENCH:
        rows.append([r["skenario"], r["worker"], f(r["total_waktu_s"], "{:.2f}"),
                     f(r["throughput_rps"], "{:.2f}"), f(r["latensi_ms"], "{:.2f}")])
    return rows


def bench_sentences():
    out = []
    for sk in ("GET /obat", "POST /transactions"):
        a = next((r for r in BENCH if r["skenario"] == sk and r["worker"] == 1), None)
        b = next((r for r in BENCH if r["skenario"] == sk and r["worker"] == 4), None)
        if a and b and all(a.get(k) and b.get(k) for k in ("throughput_rps", "latensi_ms")):
            ratio = b["throughput_rps"] / a["throughput_rps"]
            out.append(
                f"<b>{sk}</b>: throughput berubah dari {a['throughput_rps']:.2f} menjadi "
                f"{b['throughput_rps']:.2f} req/detik ({ratio:.2f}x) dan rata-rata latensi dari "
                f"{a['latensi_ms']:.2f} ms menjadi {b['latensi_ms']:.2f} ms.")
        else:
            out.append(f"<b>{sk}</b>: [isi setelah benchmark dijalankan: bandingkan throughput dan latensi 1 vs 4 worker].")
    return out


# ------------------------------------------------------------------- dokumen
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, "UTS Komputasi Paralel dan Terdistribusi - Ganjil 2026/2027")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Halaman {doc.page}")
    canvas.restoreState()


def build():
    nama, nim = CFG.get("nama", "[Nama]"), CFG.get("nim", "[NIM]")
    s = []
    s += [P("LAPORAN UJIAN TENGAH SEMESTER", TITLE),
          P("Komputasi Paralel dan Terdistribusi - Program Studi Teknik Informatika", SUB),
          P("Universitas Muhammadiyah Pontianak - Semester Ganjil 2026/2027", SUB),
          P(f"<b>{nama}</b> (NIM {nim})", SUB),
          P(f"Repositori: {CFG.get('repo', '-')} &nbsp;|&nbsp; Video: {CFG.get('video', '-')}", SUB),
          Spacer(1, 6)]

    # ---- C3.1 deskripsi
    s += [P("1. Deskripsi Aplikasi", H1),
          P("<b>Tema:</b> manajemen apotek. Resource utama adalah <b>obat</b> (nama, kategori, "
            "produsen, harga, stok) dan resource transaksi adalah <b>penjualan</b> obat. "
            "Aplikasi dibangun dengan FastAPI (Python 3.10+) dan SQLite yang diakses secara "
            "asinkron melalui aiosqlite.")]
    s += bullets([
        "<b>Fitur utama:</b> CRUD obat dengan paginasi dan validasi Pydantic; pembuatan transaksi "
        "dengan respon instan <i>pending</i>; pemrosesan latar belakang dengan alur "
        "<i>pending -> processing -> completed/failed</i>; pencegahan overselling dengan asyncio.Lock.",
        "<b>Batasan:</b> asyncio.Lock hanya melindungi satu proses (tiap worker punya lock sendiri), "
        "sehingga konsistensi antar-worker dijaga tambahan oleh <i>UPDATE ... WHERE stok &gt;= qty</i> "
        "yang atomik di SQLite; SQLite hanya mengizinkan satu penulis pada satu waktu; pemrosesan "
        "latar belakang disimulasikan (asyncio.sleep 3 detik) dan tidak persisten bila server mati "
        "di tengah proses; tanpa autentikasi; kolom stok tanpa CHECK agar demonstrasi race condition "
        "terlihat (validasi dilakukan di aplikasi).",
    ])

    # ---- A1
    s += [P("2. Bagian A1 - Concurrency vs. Paralelisme", H1)]
    s += [P("a. Bagian yang bersifat concurrent (I/O-bound)", H2),
          P("Hampir seluruh sistem bersifat I/O-bound: (1) menerima dan menjawab request HTTP, "
            "(2) setiap query SQLite melalui aiosqlite (SELECT, INSERT, UPDATE), dan (3) fungsi "
            "<i>proses_transaksi_background</i> yang sebagian besar waktunya menunggu "
            "<i>asyncio.sleep(3)</i> sebagai simulasi pekerjaan I/O. Saat sebuah coroutine "
            "berada pada <i>await</i>, event loop menyerahkan eksekusi ke coroutine lain, sehingga "
            "ratusan request dan background task dapat <i>berjalan bergantian</i> (concurrent) pada "
            "satu thread tanpa saling memblokir. Inilah alasan POST /transactions dapat membalas "
            "<i>pending</i> seketika sementara tiga detik pemrosesan berjalan di belakang.")]
    s += [P("b. Bagian yang berpotensi membutuhkan paralelisme (CPU-bound)", H2),
          P("Pada versi saat ini beban CPU sangat kecil (validasi Pydantic, serialisasi JSON, "
            "perhitungan total harga), sehingga belum ada bagian yang benar-benar CPU-bound. Potensi "
            "CPU-bound muncul bila ditambahkan fitur seperti laporan penjualan dengan agregasi data "
            "besar, pembuatan struk/faktur PDF, hashing/enkripsi, atau peramalan kebutuhan stok. "
            "Pekerjaan semacam itu bila dijalankan langsung di dalam <i>async def</i> akan "
            "memblokir event loop dan menahan seluruh request lain, sehingga perlu dipindahkan ke "
            "proses terpisah (multiprocessing / ProcessPoolExecutor) agar berjalan paralel pada core lain.")]
    s += [P("c. GIL, threading, dan multi-worker Uvicorn", H2),
          P("<b>GIL</b> (Global Interpreter Lock) memastikan hanya satu thread yang mengeksekusi "
            "bytecode Python pada satu waktu dalam satu proses. Akibatnya, threading tidak mempercepat "
            "kode CPU-bound karena thread-thread itu bergantian memegang GIL; threading baru "
            "bermanfaat untuk I/O karena GIL dilepas saat thread menunggu I/O. Event loop asyncio "
            "bahkan lebih ringan dari threading untuk beban I/O karena memakai satu thread dan "
            "perpindahan tugas hanya terjadi pada titik <i>await</i> (cooperative), tetapi tetap "
            "terbatas pada satu core. <b>Uvicorn --workers N</b> mengatasinya dengan menjalankan "
            "N <i>proses</i> OS terpisah (multiprocessing). Tiap proses memiliki interpreter, GIL, "
            "dan event loop sendiri sehingga dapat berjalan paralel sungguhan di beberapa core. "
            "Konsekuensinya memori tidak dibagi: asyncio.Lock di satu worker tidak terlihat oleh "
            "worker lain, sehingga konsistensi lintas-proses harus dijaga di basis data "
            "(UPDATE atomik bersyarat), yang diterapkan pada aplikasi ini.")]

    # ---- A2
    s += [P("3. Bagian A2 - Arsitektur dan Alur Data", H1),
          arch_diagram(),
          P("Gambar 1. Diagram arsitektur. Panah putus-putus: router /obat langsung membaca/menulis "
            "SQLite melalui aiosqlite.", CAP)]
    s += [P("Alur satu siklus transaksi lengkap", H2)]
    s += bullets([
        "<b>1.</b> Klien mengirim <i>POST /transactions</i> {item_id, qty}. Uvicorn meneruskan ke salah satu worker; "
        "Pydantic memvalidasi body (gagal -> 422).",
        "<b>2.</b> Handler memeriksa obat di SQLite (tidak ada -> 404), lalu masuk ke <i>potong_stok</i>: "
        "<i>async with stok_lock</i> -> baca stok -> cek kecukupan -> kurangi stok. Stok kurang -> 409 Conflict.",
        "<b>3.</b> Transaksi disimpan dengan status <b>pending</b>; <i>BackgroundTasks.add_task</i> menjadwalkan "
        "<i>proses_transaksi_background</i>.",
        "<b>4.</b> Respon <b>202 Accepted</b> {id, status: pending} dikirim langsung ke klien.",
        "<b>5.</b> Setelah respon terkirim, pekerja latar belakang mengubah status menjadi <b>processing</b>, "
        "menunggu <i>asyncio.sleep(3)</i> (event loop tetap melayani request lain), lalu mengubah status menjadi "
        "<b>completed</b>. Bila terjadi galat: stok dikembalikan dan status menjadi <b>failed</b>.",
        "<b>6.</b> Klien memantau lewat <i>GET /transactions/{id}</i> sampai status <b>completed</b>.",
    ])

    # ---- C3.3 endpoint
    s += [P("4. Tabel Endpoint", H1)]
    rows = [["Method", "Path", "Deskripsi", "Status"],
            ["GET", "/obat?skip=0&amp;limit=10", "Daftar obat dengan paginasi", "200"],
            ["GET", "/obat/{id}", "Detail satu obat", "200 / 404"],
            ["POST", "/obat", "Tambah obat (validasi Pydantic)", "201 / 422"],
            ["PUT", "/obat/{id}", "Perbarui obat, kembalikan data terbaru", "200 / 404 / 422"],
            ["DELETE", "/obat/{id}", "Hapus permanen (hard delete)", "200 / 404"],
            ["POST", "/transactions", "Buat transaksi; potong stok; respon pending instan; proses di BackgroundTasks", "202 / 404 / 409 / 422"],
            ["GET", "/transactions?status=", "Daftar transaksi, filter status", "200 / 422"],
            ["GET", "/transactions/{id}", "Detail transaksi dan status terkini", "200 / 404"]]
    s += [table(rows, [1.6 * cm, 4.6 * cm, 8 * cm, 2.9 * cm])]

    # ---- B3 dokumentasi
    s += [CondPageBreak(9 * cm), P("5. Dokumentasi B3 - Race Condition dan asyncio.Lock", H1),
          screenshot("ss_tanpa_lock.png",
                     "Gambar 2. Tahap 1 (tanpa lock): kedua transaksi berhasil, stok akhir minus (overselling)."),
          Spacer(1, 4),
          screenshot("ss_dengan_lock.png",
                     "Gambar 3. Tahap 2 (dengan asyncio.Lock): satu sukses (202), satu ditolak 409 Conflict."),
          P("<b>Analisis.</b> Tanpa lock, pola <i>read -> check -> write</i> tidak atomik. Pada baris "
            "<i>await asyncio.sleep(0.01)</i>, event loop berpindah ke request kedua yang membaca stok "
            "yang sama (1) sebelum request pertama sempat menguranginya; keduanya lolos pemeriksaan "
            "dan menulis, sehingga stok menjadi -1. Dengan <i>async with stok_lock</i>, seluruh "
            "critical section hanya boleh dimasuki satu coroutine pada satu waktu. Request kedua "
            "menunggu (tanpa memblokir event loop), kemudian membaca stok yang sudah menjadi 0 dan "
            "ditolak dengan 409. Dengan demikian invarian <i>stok &gt;= 0</i> terjaga.")]

    # ---- C1/C3.4 benchmark
    s += [P("6. Hasil Benchmark (1 Worker vs 4 Worker)", H1),
          P("Pengujian memakai Locust: GET /obat 100 request (konkurensi 20) dan POST /transactions "
            "50 request (konkurensi 10). " + CFG.get("catatan_mesin", "")),
          table(bench_rows(), [4 * cm, 1.8 * cm, 3.2 * cm, 3.6 * cm, 4.5 * cm]),
          Spacer(1, 4)]

    # ---- C3.5 analisis
    s += [P("7. Analisis Performa", H1)]
    s += bullets(bench_sentences())
    s += [Spacer(1, 3)]
    s += bullets([
        "<b>GET /obat (read):</b> tiap worker memiliki event loop dan GIL sendiri, dan mode WAL "
        "memungkinkan banyak pembaca bersamaan, sehingga 4 worker dapat memproses pembacaan paralel "
        "di beberapa core. Peningkatan terbatas karena pekerjaan per request sangat kecil dan "
        "jumlah request hanya 100; biaya koordinasi antar-proses dan keterbatasan klien Locust ikut "
        "memengaruhi hasil.",
        "<b>POST /transactions (write):</b> dipengaruhi (a) lock: di 1 worker semua pemotongan stok "
        "berbaris pada satu lock (minimal sekitar 10 ms per request akibat jeda di critical section), "
        "sedangkan pada 4 worker ada 4 lock sehingga antrean terbagi; dan (b) SQLite hanya mengizinkan "
        "satu penulis pada satu waktu, sehingga skala tulis tidak linear dan penulisan antar-proses "
        "saling menunggu (busy_timeout). Karena itu konsistensi antar-worker bertumpu pada UPDATE "
        "atomik, bukan pada asyncio.Lock.",
        "<b>Proses latar belakang 3 detik</b> tidak memengaruhi latensi POST karena respon dikirim "
        "sebelum background task berjalan; yang diukur Locust adalah waktu respon <i>pending</i>.",
    ])

    # ---- referensi
    s += [P("8. Referensi", H1)]
    refs = ["FastAPI Documentation - https://fastapi.tiangolo.com",
            "Python asyncio - https://docs.python.org/3/library/asyncio.html",
            "aiosqlite - https://aiosqlite.omnilib.dev",
            "Uvicorn - https://www.uvicorn.org",
            "Locust - https://locust.io",
            "Modul praktikum dan materi perkuliahan Komputasi Paralel dan Terdistribusi."]
    refs += CFG.get("referensi_tambahan", [])
    s += bullets(refs)

    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.9 * cm,
                            title="Laporan UTS Komputasi Paralel dan Terdistribusi",
                            author=nama)
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print("Dibuat:", OUT)


if __name__ == "__main__":
    build()
