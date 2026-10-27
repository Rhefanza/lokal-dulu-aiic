"""Transkrip 'apa yang terdengar' untuk halaman Dengar: sebelum vs sesudah.

Transkrip PDF asli adalah simulasi pembaca layar pada PDF tanpa tag: teks dibacakan
menurut urutan aliran konten berkas (bukan urutan visual), gambar tanpa teks alternatif
hanya diucapkan "Gambar.", dan sel tabel terbaca berurutan tanpa judul kolom.
Transkrip SIMAK disusun dari elemen hasil remediasi, sama dengan mode dengar pada HTML keluaran.
"""
import re
import unicodedata
from pathlib import Path

import fitz

_NUM = re.compile(r"\d")
_ORDINAL = ["pertama", "kedua", "ketiga", "keempat", "kelima", "keenam", "ketujuh", "kedelapan", "kesembilan", "kesepuluh"]


def figure_labels(elements) -> dict:
    """Label gambar yang dibacakan, tanpa nomor urut buatan: "Gambar N" milik keterangan penulis materi,
    dan nomor buatan bergeser setiap kali ULD menandai gambar dekoratif. Bentuknya "Gambar di halaman 2",
    atau "Gambar kedua di halaman 2" bila halaman itu memuat lebih dari satu gambar yang dibacakan."""
    per_page: dict[int, list] = {}
    for e in elements:
        if e["kind"] == "image" and e.get("status") != "dekoratif":
            per_page.setdefault(e["page"], []).append(e["id"])
    out = {}
    for page, ids in per_page.items():
        for k, el_id in enumerate(ids):
            if len(ids) == 1:
                out[el_id] = f"Gambar di halaman {page}"
            else:
                out[el_id] = f"Gambar {_ORDINAL[k] if k < len(_ORDINAL) else f'ke-{k + 1}'} di halaman {page}"
    return out


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def original(pdf: Path) -> list[dict]:
    """Simulasi pembacaan PDF asli: blok dalam urutan berkas, gambar tanpa keterangan."""
    segs = []
    with fitz.open(pdf) as doc:
        for pno, page in enumerate(doc, start=1):
            flags = fitz.TEXTFLAGS_BLOCKS | fitz.TEXT_PRESERVE_IMAGES
            for b in page.get_text("blocks", flags=flags, sort=False):
                if b[6] == 1:
                    segs.append({"kind": "image", "page": pno, "text": "Gambar.", "say": "Gambar.",
                                 "note": "tanpa teks alternatif"})
                    continue
                t = _clean(b[4])
                if t:
                    segs.append({"kind": "text", "page": pno, "text": t, "say": t})
    return segs


def remediated(state: dict) -> list[dict]:
    """Urutan yang dibacakan dari keluaran SIMAK (judul, paragraf, tabel berjudul, deskripsi gambar)."""
    segs = _remediated(state)
    for s in segs:
        s["text"], s["say"] = _clean(s["text"]), _clean(s["say"])
    return segs


def table_say(rows: list[list[str]], no: int) -> str:
    """Tabel dibacakan per baris dengan judul kolom, bukan sel berurutan."""
    return f"Tabel {no}, {len(rows) - 1} baris. Kolom: {', '.join(rows[0])}. " + " ".join(
        f"Baris {i + 1}: " + "; ".join(f"{h} {c}" for h, c in zip(rows[0], r)) + "." for i, r in enumerate(rows[1:]))


def _remediated(state: dict) -> list[dict]:
    segs, tab_no = [], 0
    labels = figure_labels(state["elements"])
    for el in state["elements"]:
        k = el["kind"]
        if k == "heading":
            segs.append({"kind": "heading", "page": el["page"], "text": el["text"],
                         "say": f"Judul tingkat {el['level']}. {el['text']}"})
        elif k == "paragraph":
            segs.append({"kind": "text", "page": el["page"], "text": el["text"], "say": el["text"]})
        elif k == "table":
            tab_no += 1
            say = table_say(el["rows"], tab_no)
            segs.append({"kind": "table", "page": el["page"], "text": say, "say": say})
        elif k == "image":
            st = el.get("status")
            if st == "dekoratif":
                segs.append({"kind": "skip", "page": el["page"], "text": "Hiasan dilewati.", "say": "",
                             "note": "gambar dekoratif, tidak dibacakan", "el": el["id"]})
                continue
            if st == "terbit_otomatis":
                body, note = el["alt_auto"], "dihasilkan otomatis, angka terverifikasi"
            elif st in ("disetujui", "diubah"):
                body, note = el["alt_final"], "disetujui ULD"
            elif st == "ditolak":
                body, note = "Deskripsi ditolak ULD; uraian belum tersedia.", "ditolak ULD"
            else:
                body, note = (f"{(el.get('jenis') or 'gambar').capitalize()}, menunggu tinjauan "
                              "Unit Layanan Disabilitas."), "ditahan, belum diverifikasi"
            text = f"{labels[el['id']]}. {body}"
            segs.append({"kind": "image", "page": el["page"], "text": text, "say": text, "note": note,
                         "el": el["id"], "status": st})
    return segs


def pair(asli: list[dict], state: dict) -> None:
    """Pasangkan setiap 'Gambar.' pada transkrip asli dengan elemen gambar SIMAK di halaman yang sama,
    hanya bila jumlahnya per halaman cocok (agar gambar tidak tertukar)."""
    by_page: dict[int, list] = {}
    for el in state["elements"]:
        if el["kind"] == "image":
            by_page.setdefault(el["page"], []).append(el["id"])
    seen: dict[int, list] = {}
    for sg in asli:
        if sg["kind"] == "image":
            seen.setdefault(sg["page"], []).append(sg)
    for pno, segs in seen.items():
        ids = by_page.get(pno, [])
        if len(ids) == len(segs):
            for sg, i in zip(segs, ids):
                sg["el"] = i


def summary(asli: list[dict], simak: list[dict]) -> dict:
    """Angka sederhana untuk dibandingkan: berapa gambar yang terdengar bermakna dan berapa angka grafik yang sampai."""
    a_img = [s for s in asli if s["kind"] == "image"]
    s_img = [s for s in simak if s["kind"] == "image"]
    s_info = [s for s in s_img if s.get("status") in ("terbit_otomatis", "disetujui", "diubah")]
    return {
        "asli_gambar": len(a_img),
        "asli_gambar_bermakna": 0,
        "asli_angka_grafik": 0,
        "simak_gambar": len(s_img),
        "simak_gambar_bermakna": len(s_info),
        "simak_ditahan": len(s_img) - len(s_info),
        "simak_angka_grafik": sum(len(re.findall(r"\d+(?:[.,]\d+)*", s["say"].split(".", 1)[1] if "." in s["say"] else ""))
                                  for s in s_info),
    }
