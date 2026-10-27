"""Katalog materi untuk dua peran: ULD memeriksa dan memperbaiki, tunanetra mendengarkan.

Materi adalah sesi work/job_<id> yang diunggah dari halaman ULD (state["katalog"]). LLM memproses
semuanya dan materi langsung terbit. Deskripsi gambar yang gagal verifikasi tidak ditahan, tetapi
dibacakan dengan penanda "belum diperiksa" sampai ULD membenarkan atau memperbaikinya. Teks asli
dari LLM tetap tersimpan di elemen; perbaikan ULD disimpan terpisah beserta lognya.

Ringkasan materi (state["ringkasan"]) mengikuti aturan yang sama: dibuat LLM sekali setelah terbit,
langsung bisa didengar dengan penanda, lalu dibenarkan atau diperbaiki ULD.
"""
import re
import time
from pathlib import Path

from . import listen, pipeline, vlm
from .config import WORK

CATATAN = "Catatan: deskripsi gambar ini belum diperiksa. "
CATATAN_RINGKASAN = "Catatan: ringkasan ini dibuat otomatis dan belum diperiksa. "
TANPA_DESKRIPSI = "Deskripsi gambar ini belum tersedia."
SUMBER_MAKS = 60000  # karakter isi materi yang dikirim ke peringkas
BATAS = 2400  # karakter per potongan audio, sama dengan pemutar peramban (speech.js)


def judul(state: dict) -> str:
    return state.get("judul_uld") or state["title"]


def _ucapan_draf(draft: str) -> str:
    """Draf rumus memuat baris 'LaTeX:' dan 'Ucapan:'; yang dibacakan hanya bagian ucapan."""
    if "Ucapan:" in draft:
        return draft.split("Ucapan:", 1)[1].strip()
    return "\n".join(b for b in draft.splitlines() if not b.strip().startswith("LaTeX:")).strip()


def _deskripsi(el: dict) -> tuple[str, str]:
    st = el.get("status")
    if st == "terbit_otomatis":
        return el["alt_auto"], "terverifikasi"
    if st in ("disetujui", "diubah"):
        return el["alt_final"], "diperiksa" if st == "disetujui" else "diperbaiki"
    if st == "ditolak":
        return "", "tanpa_deskripsi"
    teks = el.get("alt_auto") or _ucapan_draf(el.get("draft") or "")
    return teks, "ditandai" if teks else "tanpa_deskripsi"


def bagian(state: dict) -> list[dict]:
    """Urutan baca materi. 'teks' adalah isi yang bisa diperbaiki ULD, 'ucapan' adalah yang dibacakan."""
    labels = listen.figure_labels(state["elements"])
    out, tab_no = [], 0
    for el in state["elements"]:
        k = el["kind"]
        if k == "image":
            if el.get("status") == "dekoratif":
                continue
            teks, tanda = _deskripsi(el)
            awal = f"{labels[el['id']]}. " + (CATATAN if tanda == "ditandai" else "")
            ucapan = awal + (teks or TANPA_DESKRIPSI)
            asli = el.get("alt_auto") or _ucapan_draf(el.get("draft") or "")
        else:
            if k == "table":
                tab_no += 1
                asli = listen.table_say(el["rows"], tab_no)
            else:
                asli = el["text"]
            teks = el.get("ucapan_uld") or asli
            tanda = "diperbaiki" if el.get("ucapan_uld") else "diperiksa" if el.get("dicek") else "otomatis"
            ucapan = teks
        ucapan = listen._clean(ucapan)
        if ucapan:
            out.append({"el": el["id"], "kind": k, "page": el["page"], "teks": teks, "ucapan": ucapan,
                        "tanda": tanda, "asli": asli if teks != asli else None})
    return out


def _potong(text: str, batas: int = BATAS) -> list[str]:
    """Potong di akhir kalimat agar setiap permintaan ElevenLabs tetap di bawah batasnya."""
    out, rest = [], text.strip()
    while len(rest) > batas:
        head = rest[:batas]
        akhir = [m.end() for m in re.finditer(r"[.!?;]\s+", head)]
        cut = akhir[-1] if akhir and akhir[-1] > batas // 2 else head.rfind(" ")
        if cut < batas // 2:
            cut = batas
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out


RINGKASAN = "ringkasan"  # id bagian ringkasan di API dan pemutar


def ringkasan(state: dict) -> dict | None:
    """Ringkasan sebagai satu bagian berbentuk sama dengan bagian(), agar ULD memeriksanya dengan cara yang sama."""
    r = state.get("ringkasan")
    if not r:
        return None
    ucapan = f"Ringkasan materi {judul(state)}. " + (CATATAN_RINGKASAN if r["status"] == "ditandai" else "") + r["teks"]
    return {"el": RINGKASAN, "kind": RINGKASAN, "page": None, "teks": r["teks"], "ucapan": listen._clean(ucapan),
            "tanda": r["status"], "asli": r["asli"] if r["teks"] != r["asli"] else None}


def sumber_ringkasan(state: dict) -> str:
    """Isi yang boleh diringkas: deskripsi gambar yang belum diperiksa tidak ikut, agar angkanya tidak menyebar."""
    baris = []
    for b in bagian(state):
        if b["tanda"] in ("ditandai", "tanpa_deskripsi"):
            continue
        baris.append(f"Judul: {b['teks']}" if b["kind"] == "heading" else b["teks"])
    return "\n".join(baris)[:SUMBER_MAKS]


def _paragraf(teks: str) -> str:
    """Rapikan spasi tetapi pertahankan paragraf agar mudah dibaca ULD."""
    return "\n\n".join(" ".join(b.split()) for b in teks.splitlines() if b.strip())


def buat_ringkasan(job: Path, ulang: bool = False):
    """Panggil LLM di luar kunci sesi (bisa lama), lalu simpan ke state terbaru."""
    state = pipeline.load(job)
    if state.get("ringkasan") and not ulang:
        return
    teks = _paragraf(vlm.ringkas_materi(judul(state), sumber_ringkasan(state)))
    if not teks:
        raise ValueError("Peringkas tidak menghasilkan teks")
    with pipeline.job_lock(job):
        state = pipeline.load(job)
        if state.get("ringkasan") and not ulang:
            return
        log = (state.get("ringkasan") or {}).get("log", [])
        state["ringkasan"] = {"teks": teks, "asli": teks, "status": "ditandai", "dibuat": time.time(), "log": log}
        pipeline.save(job, state)


def putar(state: dict, jenis: str = "materi") -> list[dict]:
    """Daftar putar: satu potongan audio per bagian (atau beberapa bila bagiannya panjang)."""
    if jenis == RINGKASAN:
        r = ringkasan(state)
        return [{"el": RINGKASAN, "teks": t} for t in _potong(r["ucapan"])] if r else []
    return [{"el": b["el"], "teks": t} for b in bagian(state) for t in _potong(b["ucapan"])]


def ringkas(jid: str, state: dict, siap) -> dict:
    segs = bagian(state)
    r = ringkasan(state)
    daftar_putar = putar(state) + putar(state, RINGKASAN)
    return {"id": jid, "judul": judul(state), "berkas": state.get("file"), "halaman": state.get("pages"),
            "dibuat": state.get("dibuat"), "bagian": len(segs),
            "ditandai": sum(b["tanda"] in ("ditandai", "tanpa_deskripsi") for b in segs + ([r] if r else [])),
            "diperbaiki": sum(b["tanda"] == "diperbaiki" for b in segs),
            "ringkasan": r["tanda"] if r else None,
            "audio": {"siap": sum(map(siap, (p["teks"] for p in daftar_putar))), "total": len(daftar_putar)}}


def daftar() -> list[tuple[str, dict]]:
    """Materi terbit, urut waktu unggah: nomor materi tetap sama saat materi baru ditambahkan."""
    out = []
    for f in WORK.glob("job_*/state.json"):
        state = pipeline.load(f.parent)
        if state.get("katalog"):
            out.append((f.parent.name.removeprefix("job_"), state))
    return sorted(out, key=lambda x: x[1].get("dibuat") or 0)


def _elemen(state: dict, el_id: str) -> dict:
    el = next((e for e in state["elements"] if e["id"] == el_id), None)
    if el is None or el["kind"] not in ("heading", "paragraph", "table", "image"):
        raise LookupError("Bagian tidak ditemukan")
    return el


def _ringkasan_ada(state: dict) -> dict:
    if not state.get("ringkasan"):
        raise LookupError("Ringkasan belum dibuat")
    return state["ringkasan"]


def _catat(el: dict, aksi: str):
    el.setdefault("log", []).append({"aksi": aksi, "oleh": "ULD", "waktu": time.strftime("%Y-%m-%d %H:%M:%S")})


def perbaiki(job: Path, el_id: str, teks: str):
    """Ganti isi yang dibacakan. Gambar lewat tinjauan pipeline agar PDF dan HTML ikut berubah."""
    teks = teks.strip()
    if not teks:
        raise ValueError("Isi perbaikan tidak boleh kosong")
    with pipeline.job_lock(job):
        state = pipeline.load(job)
        if el_id == RINGKASAN:
            r = _ringkasan_ada(state)
            r["teks"] = _paragraf(teks)
            r["status"] = "diperiksa" if r["teks"] == r["asli"] else "diperbaiki"
            _catat(r, "ubah")
            pipeline.save(job, state)
            return
        el = _elemen(state, el_id)
        if el["kind"] == "image":
            pipeline.review(job, el_id, "ubah", teks)
            return
        asli = el["text"] if el["kind"] != "table" else None
        if teks == asli:
            el.pop("ucapan_uld", None)
        else:
            el["ucapan_uld"] = teks
        _catat(el, "ubah")
        pipeline.save(job, state)


def benarkan(job: Path, el_id: str):
    """ULD menyatakan bagian ini sudah benar; penanda 'belum diperiksa' hilang."""
    with pipeline.job_lock(job):
        state = pipeline.load(job)
        if el_id == RINGKASAN:
            r = _ringkasan_ada(state)
            if r["status"] == "ditandai":
                r["status"] = "diperiksa"
            _catat(r, "benar")
            pipeline.save(job, state)
            return
        el = _elemen(state, el_id)
        if el["kind"] == "image":
            teks, _ = _deskripsi(el)
            if not teks:
                raise ValueError("Gambar ini belum memiliki deskripsi. Tulis deskripsinya lewat Perbaiki.")
            pipeline.review(job, el_id, "setujui", teks)
            return
        el["dicek"] = True
        _catat(el, "benar")
        pipeline.save(job, state)


def ganti_judul(job: Path, baru: str):
    baru = " ".join(baru.split())
    if not baru:
        raise ValueError("Judul tidak boleh kosong")
    with pipeline.job_lock(job):
        state = pipeline.load(job)
        state["judul_uld"] = baru[:200]
        pipeline.save(job, state)
