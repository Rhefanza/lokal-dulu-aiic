"""SIMAK — aplikasi web tiga lapis (Lampiran E).

Jalankan:  python -m uvicorn app:app --port 8000
Titik akhir mengikuti rancangan: POST /api/unggah, GET /api/pekerjaan/{id},
POST /api/tinjau/{id}/{el}, GET /keluaran/{id}/simak.html|simak.pdf.
Dokumen diproses per sesi di work/ dan dihapus melalui tindakan Hapus sesi; tidak ada cleanup berkala.
"""
import json
import logging
import shutil
import threading
import time
import uuid
from pathlib import Path

import fitz

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from simak import materi, pipeline, vlm
from simak.config import DATA, ROOT, WORK

app = FastAPI(title="SIMAK")
WEB = ROOT / "web"
JOBS: dict[str, dict] = {}
SYN = DATA / "synth"
MAX_UPLOAD = 20 * 1024 * 1024
MAX_PAGES = 200
_ACTIVE = threading.BoundedSemaphore(1)


def _job_dir(jid: str) -> Path:
    if not jid.isalnum():
        raise HTTPException(400)
    return WORK / f"job_{jid}"


def _start(pdf: Path, name: str, katalog: bool = False) -> str:
    if not _ACTIVE.acquire(blocking=False):
        raise HTTPException(409, "Satu dokumen sedang diproses. Tunggu selesai sebelum memulai dokumen lain.")
    jid = uuid.uuid4().hex[:10]
    job = _job_dir(jid)
    try:
        job.mkdir(parents=True)
        shutil.copy(pdf, job / "asli.pdf")
        JOBS[jid] = {"tahap": "antre", "pesan": "Menunggu", "nama": name, "mulai": time.time(), "katalog": katalog}
    except Exception:
        _ACTIVE.release()
        raise

    def work():
        try:
            with pipeline.job_lock(job):
                state = pipeline.run(job / "asli.pdf", job, lambda t, m: JOBS[jid].update(tahap=t, pesan=m))
                state["file"] = name
                if katalog:  # langsung terbit untuk tunanetra; ULD memeriksa sesudahnya
                    state["katalog"], state["dibuat"] = True, JOBS[jid]["mulai"]
                pipeline.save(job, state)
            if katalog:
                _antre_audio(jid)
        except Exception:
            logging.exception("Pemrosesan SIMAK gagal: %s", jid)
            JOBS[jid].update(tahap="gagal", pesan="Dokumen gagal diproses. Periksa format PDF, lalu coba dokumen lain.")
        finally:
            _ACTIVE.release()
    threading.Thread(target=work, daemon=True).start()
    return jid


# ------------------------------------------------------------------ dokumen
@app.get("/api/sampel")
def sampel():
    meta = json.loads((SYN / "docs.json").read_text(encoding="utf-8"))
    out = [{"file": m["file"], "set": m["set"]} for m in meta]
    cc = DATA / "cc" / "cc.json"
    if cc.exists():
        out += [{"file": m["file"], "set": "nyata"} for m in json.loads(cc.read_text(encoding="utf-8"))["sampel"]
                if (DATA / "cc" / m["file"]).exists()]  # PDF nyata tidak ikut repo (fetch_cc.py)
    return out


def _sampel_path(name: str) -> Path:
    f = SYN / "docs" / Path(name).name
    if not f.exists():
        f = DATA / "cc" / Path(name).name
    if not f.exists():
        raise HTTPException(404)
    return f


@app.post("/api/sampel/{name}")
def proses_sampel(name: str):
    f = _sampel_path(name)
    return {"id": _start(f, f.name)}


@app.post("/api/unggah")
async def unggah(file: UploadFile = File(...)):
    return {"id": await _terima_pdf(file, katalog=False)}


async def _terima_pdf(file: UploadFile, katalog: bool) -> str:
    data = bytearray()
    while chunk := await file.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Berkas melebihi batas 20 MiB. Pilih PDF yang lebih kecil.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Berkas bukan PDF")
    try:
        with fitz.open(stream=bytes(data), filetype="pdf") as doc:
            if doc.needs_pass:
                raise HTTPException(400, "PDF terkunci. Unggah salinan tanpa kata sandi.")
            if not 1 <= doc.page_count <= MAX_PAGES:
                raise HTTPException(400, "PDF harus memuat 1 hingga 200 halaman.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "PDF tidak dapat dibuka. Simpan ulang sebagai PDF yang valid.")
    tmp = WORK / f"up_{uuid.uuid4().hex}.pdf"
    tmp.write_bytes(data)
    try:
        return _start(tmp, Path(file.filename or "dokumen.pdf").name, katalog)
    finally:
        tmp.unlink(missing_ok=True)


@app.get("/api/pekerjaan/{jid}")
def pekerjaan(jid: str):
    job = _job_dir(jid)
    info = JOBS.get(jid, {})
    if (job / "state.json").exists() and info.get("tahap") in (None, "selesai"):
        st = pipeline.load(job)
        st.pop("_job", None)
        return {"tahap": "selesai", "nama": info.get("nama", st.get("file")), "state": st}
    if not job.exists():
        raise HTTPException(404)
    return {"tahap": info.get("tahap"), "pesan": info.get("pesan"), "nama": info.get("nama")}


@app.get("/api/pekerjaan/{jid}/img/{el}")
def gambar(jid: str, el: str):
    f = _job_dir(jid) / "img" / f"{Path(el).name}.png"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


class Tinjau(BaseModel):
    aksi: str
    alt: str = ""


@app.post("/api/tinjau/{jid}/{el}")
def tinjau(jid: str, el: str, body: Tinjau):
    if body.aksi not in ("setujui", "ubah", "tolak", "dekoratif"):
        raise HTTPException(400)
    if body.aksi == "ubah" and not body.alt.strip():
        raise HTTPException(400, "Teks alternatif tidak boleh kosong")
    try:
        return pipeline.review(_job_dir(jid), el, body.aksi, body.alt.strip())
    except (FileNotFoundError, LookupError):
        raise HTTPException(404, "Sesi atau elemen tinjauan tidak ditemukan")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/keluaran/{jid}/{name}")
def keluaran(jid: str, name: str):
    if name not in ("simak.html", "simak.pdf", "asli.pdf"):
        raise HTTPException(404)
    job = _job_dir(jid)
    with pipeline.job_lock(job):
        f = pipeline.output_path(job, name)
        if not f.is_file():
            raise HTTPException(404, "Keluaran belum tersedia atau sesi telah dihapus")
        headers = {} if name.endswith("html") else {"Content-Disposition": f'attachment; filename="{name}"'}
        return Response(f.read_bytes(), media_type="text/html" if name.endswith("html") else "application/pdf", headers=headers)


@app.delete("/api/pekerjaan/{jid}")
def hapus(jid: str):
    job = _job_dir(jid)
    if JOBS.get(jid, {}).get("tahap") not in (None, "selesai", "gagal"):
        raise HTTPException(409, "Dokumen masih diproses. Tunggu selesai sebelum menghapus sesi.")
    with pipeline.job_lock(job):
        if not job.exists():
            raise HTTPException(404, "Sesi tidak ditemukan")
        shutil.rmtree(job)
        JOBS.pop(jid, None)
    return {"dihapus": True}



# ------------------------------------------------------------------ evaluasi
# ------------------------------------------------------------------ suara
SUARA = {"eleven": "Suara manusia (ElevenLabs)"}  # suara server opsional; bawaan Web Speech API di peramban
_voice_lock = threading.Lock()
_prep_q: list[tuple] = []
_prep_cv = threading.Condition()


class Suara(BaseModel):
    teks: str
    suara: str = "eleven"
    kecepatan: int = 0   # persen, mis. -10 atau 15
    nada: int = 0        # Hz, mis. -20 atau 10


_interactive = [0]  # permintaan pengguna yang sedang menunggu; pra-pembuatan mengalah padanya


def _synth(teks: str, suara: str, kecepatan: int, nada: int, prioritas: bool = True):
    from simak import voice
    if prioritas:
        _interactive[0] += 1
    try:
        with _voice_lock:  # serialisasi penulisan cache audio
            return voice.synthesize(teks, speaker=suara, rate=f"{kecepatan:+d}%", pitch=f"{nada:+d}Hz")
    finally:
        if prioritas:
            _interactive[0] -= 1


def _prep_worker():
    while True:
        with _prep_cv:
            while not _prep_q:
                _prep_cv.wait()
            job = _prep_q.pop(0)
        while _interactive[0] > 0:  # beri jalan untuk suara yang sedang ditunggu pengguna
            time.sleep(0.1)
        try:
            _synth(*job, prioritas=False)
        except Exception as e:  # pembuatan awal hanya mempercepat; kegagalan tidak menghentikan server
            print("siapkan suara gagal:", e)


threading.Thread(target=_prep_worker, daemon=True).start()


@app.get("/api/suara/daftar")
def suara_daftar():
    from simak import voice
    return [{"id": k, "nama": v} for k, v in SUARA.items() if k not in voice.PAID_SPEAKERS or voice.eleven_ready()]


@app.post("/api/suara")
def suara(body: Suara):
    from simak import voice
    if body.suara not in SUARA or not body.teks.strip() or len(body.teks) > 4000:
        raise HTTPException(400, "Teks atau suara tidak valid")
    try:
        f = _synth(body.teks, body.suara, max(-50, min(50, body.kecepatan)), max(-50, min(50, body.nada)))
    except voice.VoiceError as e:
        raise HTTPException(503, str(e))
    except Exception:
        logging.exception("Pembuatan audio gagal")
        raise HTTPException(503, "Suara tidak dapat dibuat. Coba lagi atau pilih suara peramban.")
    return FileResponse(f, media_type="audio/mpeg")


class Siapkan(BaseModel):
    teks: list[str]
    suara: str = "eleven"
    kecepatan: int = 0
    nada: int = 0


@app.post("/api/suara/siapkan")
def suara_siapkan(body: Siapkan):
    """Membuat audio lebih dulu di latar belakang agar pemutaran tidak menunggu."""
    from simak import voice
    if body.suara not in SUARA:
        raise HTTPException(400)
    if body.suara in voice.PAID_SPEAKERS:  # berbayar per karakter: hanya dibuat saat benar-benar diputar
        return {"diantrekan": 0}
    with _prep_cv:
        for t in body.teks[:300]:
            if t.strip():
                _prep_q.append((t, body.suara, body.kecepatan, body.nada))
        _prep_cv.notify()
    return {"diantrekan": len(body.teks[:300])}


class Perintah(BaseModel):
    ucapan: str
    tombol: list[str]


@app.post("/api/perintah")
def perintah(body: Perintah):
    """Perintah suara yang tidak cocok persis dengan nama tombol: biarkan LLM menebak tombol yang dimaksud."""
    ucapan, tombol = body.ucapan.strip()[:200], [t.strip()[:80] for t in body.tombol[:60]]
    if not ucapan or not tombol:
        raise HTTPException(400)
    return {"pilihan": vlm.pilih_tombol(ucapan, tombol)}


# ------------------------------------------------------------------ materi: ULD dan tunanetra
_audio_q: list[str] = []
_audio_cv = threading.Condition()
AUDIO_GAGAL: dict[str, str] = {}
RINGKASAN_GAGAL: dict[str, str] = {}


def _antre_audio(jid: str):
    """Audio seluruh materi dibuat sekali saat terbit (dan setelah ULD memperbaiki) agar pemutaran tidak menunggu."""
    with _audio_cv:
        if jid not in _audio_q:
            _audio_q.append(jid)
        _audio_cv.notify()


def _ringkasan(jid: str, ulang: bool = False):
    """Ringkasan dibuat sekali setelah terbit; kegagalan LLM tidak menghentikan audio materi."""
    try:
        materi.buat_ringkasan(_job_dir(jid), ulang)
        RINGKASAN_GAGAL.pop(jid, None)
    except FileNotFoundError:
        pass
    except vlm.QuotaHabis as e:
        RINGKASAN_GAGAL[jid] = f"Ringkasan belum bisa dibuat: {e}"
    except Exception:
        logging.exception("Ringkasan materi gagal: %s", jid)
        RINGKASAN_GAGAL[jid] = "Ringkasan gagal dibuat. Coba Buat ulang ringkasan."


def _audio_worker():
    from simak import voice
    for jid, _ in materi.daftar():  # materi yang ringkasan atau audionya belum lengkap saat server terakhir berhenti
        _antre_audio(jid)
    while True:
        with _audio_cv:
            while not _audio_q:
                _audio_cv.wait()
            jid = _audio_q.pop(0)
        _ringkasan(jid)
        if not voice.eleven_ready():
            continue
        try:
            state = pipeline.load(_job_dir(jid))
            for p in materi.putar(state) + materi.putar(state, materi.RINGKASAN):
                if voice.cached(p["teks"]):
                    continue
                while _interactive[0] > 0:
                    time.sleep(0.1)
                _synth(p["teks"], "eleven", 0, 0, prioritas=False)
            AUDIO_GAGAL.pop(jid, None)
        except voice.VoiceError as e:
            AUDIO_GAGAL[jid] = str(e)
        except FileNotFoundError:
            pass  # materi dihapus selagi antre
        except Exception:
            logging.exception("Pembuatan audio materi gagal: %s", jid)
            AUDIO_GAGAL[jid] = "Audio sebagian bagian gagal dibuat; bagian itu dibuat saat diputar."


threading.Thread(target=_audio_worker, daemon=True).start()


def _materi(jid: str) -> tuple[Path, dict]:
    job = _job_dir(jid)
    if not (job / "state.json").exists():
        raise HTTPException(404, "Materi tidak ditemukan")
    state = pipeline.load(job)
    if not state.get("katalog"):
        raise HTTPException(404, "Materi tidak ditemukan")
    return job, state


@app.get("/api/materi")
def materi_daftar():
    from simak import voice
    out = []
    for jid, state in materi.daftar():
        r = materi.ringkas(jid, state, voice.cached)
        r["audio"]["gagal"] = AUDIO_GAGAL.get(jid)
        r["ringkasan_gagal"] = RINGKASAN_GAGAL.get(jid)
        out.append(r)
    diproses = [{"id": jid, "berkas": j["nama"], "tahap": j["tahap"], "pesan": j["pesan"]}
                for jid, j in JOBS.items() if j.get("katalog") and j["tahap"] != "selesai"]
    return {"materi": out, "diproses": diproses, "suara": voice.eleven_ready()}


@app.post("/api/materi")
async def materi_unggah(file: UploadFile = File(...)):
    return {"id": await _terima_pdf(file, katalog=True)}


@app.post("/api/materi/sampel/{name}")
def materi_sampel(name: str):
    f = _sampel_path(name)
    return {"id": _start(f, f.name, katalog=True)}


@app.get("/api/materi/{jid}")
def materi_isi(jid: str):
    _, state = _materi(jid)
    return {"id": jid, "judul": materi.judul(state), "berkas": state.get("file"), "bagian": materi.bagian(state),
            "ringkasan": materi.ringkasan(state), "ringkasan_gagal": RINGKASAN_GAGAL.get(jid)}


class Judul(BaseModel):
    judul: str


@app.put("/api/materi/{jid}/judul")
def materi_judul(jid: str, body: Judul):
    job, _ = _materi(jid)
    try:
        materi.ganti_judul(job, body.judul)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"judul": materi.judul(pipeline.load(job))}


class Perbaikan(BaseModel):
    teks: str


def _ubah_bagian(jid: str, el: str, fn):
    job, _ = _materi(jid)
    try:
        fn(job)
    except LookupError:
        raise HTTPException(404, "Bagian tidak ditemukan")
    except ValueError as e:
        raise HTTPException(400, str(e))
    _antre_audio(jid)
    state = pipeline.load(job)
    if el == materi.RINGKASAN:
        return materi.ringkasan(state)
    return next(b for b in materi.bagian(state) if b["el"] == el)


@app.put("/api/materi/{jid}/bagian/{el}")
def materi_perbaiki(jid: str, el: str, body: Perbaikan):
    return _ubah_bagian(jid, el, lambda job: materi.perbaiki(job, el, body.teks[:6000]))


@app.post("/api/materi/{jid}/bagian/{el}/benar")
def materi_benar(jid: str, el: str):
    return _ubah_bagian(jid, el, lambda job: materi.benarkan(job, el))


@app.post("/api/materi/{jid}/ringkasan")
def materi_ringkasan_ulang(jid: str):
    """Buat ulang ringkasan dari isi terbaru (termasuk perbaikan ULD); menggantikan ringkasan lama."""
    _materi(jid)
    _ringkasan(jid, ulang=True)
    if jid in RINGKASAN_GAGAL:
        raise HTTPException(503, RINGKASAN_GAGAL[jid])
    _antre_audio(jid)
    return materi.ringkasan(pipeline.load(_job_dir(jid)))


def _jenis(jenis: str) -> str:
    if jenis not in ("materi", materi.RINGKASAN):
        raise HTTPException(400)
    return jenis


@app.get("/api/materi/{jid}/putar")
def materi_putar(jid: str, jenis: str = "materi"):
    _, state = _materi(jid)
    return {"id": jid, "judul": materi.judul(state), "jenis": jenis, "bagian": materi.putar(state, _jenis(jenis))}


@app.get("/api/materi/{jid}/audio/{i}")
def materi_audio(jid: str, i: int, jenis: str = "materi"):
    from simak import voice
    _, state = _materi(jid)
    daftar_putar = materi.putar(state, _jenis(jenis))
    if not 0 <= i < len(daftar_putar):
        raise HTTPException(404)
    try:
        f = _synth(daftar_putar[i]["teks"], "eleven", 0, 0)
    except voice.VoiceError as e:
        raise HTTPException(503, str(e))
    return FileResponse(f, media_type="audio/mpeg")


@app.get("/api/agen")
def agen():
    from simak import voice
    return {"aktif": voice.agent_ready()}


@app.get("/api/agen/sesi")
def agen_sesi():
    from simak import voice
    try:
        return {"signed_url": voice.agent_signed_url()}
    except voice.VoiceError as e:
        raise HTTPException(503, str(e))


@app.get("/api/evaluasi")
def evaluasi():
    f = ROOT / "eval" / "results.json"
    if not f.exists():
        return JSONResponse({"ada": False})
    return json.loads(f.read_text(encoding="utf-8"))


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
