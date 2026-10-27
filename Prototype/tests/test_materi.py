import json
import shutil
import tempfile
import unittest
from pathlib import Path

from simak import materi, pipeline

ROOT = Path(__file__).resolve().parent.parent
CONTOH = ROOT / "work" / "contoh_materi_02" / "state.json"


def _state():
    return {"title": "Uji", "pages": 1, "katalog": True, "elements": [
        {"id": "e000", "kind": "heading", "level": 1, "page": 1, "text": "Pendahuluan"},
        {"id": "e001", "kind": "paragraph", "page": 1, "text": "Teks asli dari PDF."},
        {"id": "e002", "kind": "image", "page": 1, "status": "antrean", "draft": "LaTeX: x^2\nUcapan: x kuadrat"},
        {"id": "e003", "kind": "image", "page": 1, "status": "antrean"},
        {"id": "e004", "kind": "image", "page": 1, "status": "terbit_otomatis", "alt_auto": "Grafik batang terverifikasi."},
        {"id": "e005", "kind": "image", "page": 1, "status": "dekoratif"},
    ]}


class MateriTests(unittest.TestCase):
    def test_unverified_description_is_read_with_flag_not_held(self):
        b = {x["el"]: x for x in materi.bagian(_state())}
        self.assertEqual(b["e002"]["tanda"], "ditandai")
        self.assertIn(materi.CATATAN + "x kuadrat", b["e002"]["ucapan"])
        self.assertNotIn("LaTeX", b["e002"]["ucapan"])
        self.assertEqual(b["e003"]["tanda"], "tanpa_deskripsi")
        self.assertTrue(b["e003"]["ucapan"].endswith(materi.TANPA_DESKRIPSI))
        self.assertEqual(b["e004"]["tanda"], "terverifikasi")
        self.assertNotIn(materi.CATATAN, b["e004"]["ucapan"])
        self.assertNotIn("e005", b)  # dekoratif tidak dibacakan

    def test_long_section_split_at_sentence_under_limit(self):
        teks = " ".join(f"Kalimat nomor {i} cukup panjang untuk diuji." for i in range(200))
        potong = materi._potong(teks, 500)
        self.assertTrue(all(len(p) <= 500 for p in potong))
        self.assertTrue(all(p.endswith(".") for p in potong))
        self.assertEqual(" ".join(potong), teks)

    def test_uld_fix_keeps_llm_original_and_logs(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        pipeline.save(tmp, _state())
        materi.perbaiki(tmp, "e001", "Teks yang diperbaiki ULD.")
        st = pipeline.load(tmp)
        el = next(e for e in st["elements"] if e["id"] == "e001")
        self.assertEqual(el["text"], "Teks asli dari PDF.")
        self.assertEqual(el["log"][-1]["aksi"], "ubah")
        b = next(x for x in materi.bagian(st) if x["el"] == "e001")
        self.assertEqual((b["tanda"], b["ucapan"], b["asli"]), ("diperbaiki", "Teks yang diperbaiki ULD.", "Teks asli dari PDF."))
        with self.assertRaises(ValueError):
            materi.perbaiki(tmp, "e001", "   ")
        with self.assertRaises(LookupError):
            materi.benarkan(tmp, "tidak-ada")

    @unittest.skipUnless(CONTOH.exists(), "contoh sesi tidak ada")
    def test_sample_playlist_has_no_empty_parts(self):
        st = json.loads(CONTOH.read_text(encoding="utf-8"))
        daftar = materi.putar(st)
        self.assertTrue(daftar)
        self.assertTrue(all(p["teks"].strip() and len(p["teks"]) <= materi.BATAS for p in daftar))


if __name__ == "__main__":
    unittest.main()
