# SIMAK: prototipe

Prototipe *Sistem Ilustrasi Materi Aksesibel untuk Kuliah* (proposal ICC 2026, tim IRIS).
Masukannya PDF materi kuliah apa adanya. Keluarannya PDF bertag (PDF/UA-1) dan HTML aksesibel dengan
mode dengar. Setiap deskripsi grafik **terverifikasi terhadap tabel data atau ditahan** di antrean tinjauan ULD.

## Dua peran: ULD dan pendengar — 27 Oktober 2026

- **`/uld.html`** (Unit Layanan Disabilitas, tanpa login untuk prototipe): unggah PDF → LLM memproses semuanya → materi **langsung terbit**. ULD hanya memeriksa: bagian yang belum terverifikasi ditandai, bisa dibenarkan atau diperbaiki. Teks asli LLM tetap tersimpan; perbaikan dicatat terpisah beserta lognya.
- **`/pendengar.html`** (tunanetra): satu sentuhan untuk mulai (kebijakan peramban), lalu bebas sentuh. Pemandu suara memakai agen ElevenLabs; tanpa agen, perintah suara sederhana (Web Speech). Ucapkan "Halo SIMAK" atau tekan spasi untuk menyela.
- Deskripsi gambar yang gagal verifikasi **ditandai, bukan ditahan**: dibacakan dengan awalan "Catatan: deskripsi gambar ini belum diperiksa."
- Audio ElevenLabs dibuat **per bagian, sekali saat terbit** (berbayar per karakter), dan dibuat ulang hanya untuk bagian yang diperbaiki ULD.
- **Ringkasan materi** dibuat otomatis setelah terbit (Gemini Flash Lite, ±200–350 kata: gambaran umum, bagian utama, istilah penting), lengkap dengan audionya. Deskripsi gambar yang belum diperiksa tidak dipakai sebagai sumber. ULD memeriksa ringkasan di atas halaman Periksa; pendengar memintanya dengan "ringkasan nomor satu".
- Siapkan agen: [setup/agen-elevenlabs.md](setup/agen-elevenlabs.md), lalu isi `ELEVENLABS_AGENT_ID`.

## Pembaruan antarmuka dan suara — 23 Oktober 2026

Latar aplikasi cream. Halaman pengantar mengadaptasi seluruh urutan dan motion Sill: pembuka lima panel, jendela, fitur yang mengembang, proses horizontal, gerbang, panel menyatu, prinsip dan formulir. Empat halaman memakai palet/typografi yang sama, dengan transisi navigasi serta menu ponsel. Library dan font di-host lokal; preferensi reduced motion tetap dihormati. ElevenLabs menjadi pilihan awal saat tersedia, dengan pilihan peramban tetap dapat dipakai. Detail desain dan bukti: [tasks/implementation-fluid.md](tasks/implementation-fluid.md); perbaikan domain/suara sebelumnya: [tasks/implementation-cream.md](tasks/implementation-cream.md). Panduan presentasi: [tasks/demo-runbook.md](tasks/demo-runbook.md).

Pembuka: `/?jelajah=1#opening`. Langsung ke unggah: `/index.html?mulai=1#contact`. Tombol Mulai melewati sesi lama tanpa menghapus hasilnya. Navigasi Remediasi tetap membawa sesi aktif bila ada. Halaman Dengar (sebelum/sesudah) dan Demo Gerbang dihapus pada 27 Oktober 2026 karena tumpang tindih dengan halaman pendengar dan Bukti.

## Menjalankan

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Windows: ./run.ps1
# Alternatif, memakai interpreter environment aktif:
python data/make_synth.py 90          # set sintetis: 90 grafik + 6 dokumen PDF
python -m uvicorn app:app --port 8017 # buka http://localhost:8017
```

Key API disimpan di environment variable `GEMINI_API_KEY`, ditambah `GEMINI_API_KEY_2`, `_3`, … untuk
rotasi kuota. Konfigurasi lokal dapat disimpan pada `.env.local` (diabaikan Git), mengikuti `.env.example`; environment sistem memiliki prioritas. Jangan memasukkan key ke source, frontend, atau commit.

### Persiapan alat (folder `tools/`, tidak ikut di repo)

1. **Java 21** (Temurin), lalu **veraPDF 1.30** (diuji 1.30.3) dipasang headless ke `tools/verapdf/`:
   unduh `https://software.verapdf.org/releases/verapdf-installer.zip`, ekstrak, ganti `TOOLS_DIR` di
   `setup/verapdf-auto-install.xml` dengan path absolute folder `tools` kamu **memakai garis miring**
   (mis. `C:/proyek/Prototype/tools`), lalu `java -jar verapdf-izpack-installer-*.jar setup/verapdf-auto-install.xml`.
   Berhasil bila `tools/verapdf/bin/` memuat `cli-*.jar` dan `gui-*.jar`.
2. **Suara.** Atur `ELEVENLABS_API_KEY` dan `ELEVENLABS_VOICE_ID` dalam environment atau `.env.local`. Model bawaan `eleven_multilingual_v2`. Aplikasi dan HTML hasil yang dibuka lewat server otomatis memilih ElevenLabs saat dikonfigurasi; pilihan suara peramban yang sengaja disimpan pengguna tetap dihormati. Teks yang diputar dikirim ke ElevenLabs. Audio dibuat saat diminta, lalu di-cache, tanpa pembuatan massal di latar.
   Pilihan **Peramban (id-ID)** tetap tersedia, juga untuk HTML yang dibuka langsung dari disk tanpa server. Ketersediaan suara Indonesia mengikuti perangkat. Pemutar memotong teks panjang dan menghentikan bagian berikutnya ketika pengguna menekan Jeda/berpindah halaman.

Server lokal memakai **satu worker**. Unggah PDF berlapis teks maksimal **20 MiB, 200 halaman**; PDF pindai/PPT belum didukung langsung. Berkas sesi tetap tersimpan sampai pengguna menekan Hapus sesi; belum ada retensi berkala. Query `?job=<id>` membuka kembali sesi Remediasi.

### Demo luring (tanpa internet dan tanpa key)

Hasil VLM di-cache di `cache/` menurut hash (citra, perintah, skema, model). Tanpa `GEMINI_API_KEY`:
- **Remediasi**: gambar yang hasil VLM-nya belum di cache **ditahan** ke antrean ULD dengan alasan
  "VLM tidak tersedia" (fail-closed); dokumen tetap selesai.
- Isi cache untuk semua contoh sekali dengan key aktif sebelum presentasi: jalankan `python -m eval.evaluate uji`
  dan proses setiap `materi_0x.pdf` lewat aplikasi, lalu commit `cache/`.

Pemeriksaan cepat tanpa API (berapa grafik uji yang belum ada di cache):

```bash
python -c "from simak import vlm; from eval.evaluate import charts; print(sum(not vlm.chart_cached(open(f'data/synth/charts/{c[\"id\"]}.png','rb').read()) for c in charts('uji')), 'grafik uji belum di cache')"
```

Data yang sengaja tidak ikut di repo: PDF materi kuliah nyata (`data/cc/*.pdf`, hanya metadata `cc.json`
yang disertakan; jalankan `python data/fetch_cc.py` untuk mengambil ulang dari Common Crawl), audio suara hasil cache, serta folder sesi `work/`.

Evaluasi dengan kriteria terkunci:

```bash
python -m eval.evaluate kalibrasi   # set pengembangan saja → simak/thresholds.json (locked)
python -m eval.evaluate uji         # set uji tertahan, sekali → eval/results.json
```

## Halaman

| Halaman | Isi |
|---|---|
| **Remediasi & Tinjauan** (`/`) | Unggah PDF atau pilih contoh. Menampilkan veraPDF B0/B1/D, G1, beban tinjauan R, antrean ULD (setujui/ubah/tolak/dekoratif) dengan T1 vs T2 dan klaim yang bisa diklik ke sumbernya |
| **Ruang ULD** (`/uld.html`) | Unggah PDF, materi langsung terbit; ULD membenarkan atau memperbaiki bagian yang ditandai |
| **Pendengar** (`/pendengar.html`) | Tunanetra memilih dan mendengarkan materi dengan agen suara ElevenLabs |
| **Evaluasi** (`/evaluasi.html`) | G1, G3, G4 dengan selang Wilson 95%, injeksi per jenis, dan manifes run |
| **Keluaran HTML** | HTML semantik `lang="id"`, penanda status per gambar, tabel data grafik, mode dengar ElevenLabs saat server siap, atau suara peramban id-ID |

## Pemetaan ke proposal

| Proposal | Berkas |
|---|---|
| STR-01 struktur dan urutan baca | `simak/pdfa11y.py` (`autotag`), `simak/pipeline.py` (`_blocks`, tabel cadangan PyMuPDF) |
| OUT-01 perakitan dan validasi | `simak/pdfa11y.py` (`patch`, `verapdf`, `g1_audit`) |
| CLS-01 jenis gambar | `pipeline._classify_decorative` (ukuran, hash, pengulangan) + kolom `jenis` dari VLM |
| CHT-01 ekstraksi ganda, pers. (2), cA | `simak/vlm.py`, `chart.delta`, `chart.axis_check` |
| CHT-02 statistik kode, pers. (3)–(4), templat level 1–3 | `chart.derived`, `chart.build_description` |
| GAT-01 gerbang, pers. (5) dan (7) | `simak/gate.py` (`fk`, `evaluate`) |
| REV-01 tinjauan ULD | `pipeline.review`, `web/index.html` |
| OUT-02 mode dengar | `simak/output.py` |
| Evaluasi, pers. (8), G1/G3/G4 | `eval/evaluate.py` |
| Adaptor VLM tidak terikat penyedia | `simak/vlm.py` (bawaan T1 dan T2 satu model dengan dua perintah; `SIMAK_MODEL_T2` untuk model berbeda) |

## Model

Bawaan: **Gemma 4 26B-A4B** (open-weight) lewat Gemini API untuk T1, T2, B2, dan penjawab G4.
T1 dan T2 memakai dua perintah berbeda, sesuai Bab III.F. Untuk akun berbayar, `SIMAK_MODEL_T2` bisa diisi
model lain (mis. `gemma-4-31b-it`, sudah diuji dan berjalan tetapi ±40–70 dtk/panggilan) supaya kedua pengenal
benar-benar independen. Model lain bisa diganti lewat env `SIMAK_MODEL`, `SIMAK_MODEL_T2`, `SIMAK_MODEL_QA`.
Respons di-cache di `cache/` menurut hash (citra, perintah, model) supaya demo stabil.

## Hasil (run 2, 23 Okt 2026, `eval/results.json`; run 1 12 Okt di `eval/results_run1_2026-10-12.json`, identik)

Set uji tertahan sintetis: 60 grafik, 4 dokumen. Ambang dikunci pada 30 grafik dev (θe = 0,01, ε = 0,02, ρ = 0,10).

| Gerbang | Hasil | Kriteria | Status |
|---|---|---|---|
| G1 | D 4/4 dokumen lulus (B0 0/4, B1 0/4); veraPDF: B0 6 → B1 5 → D 0 aturan gagal | ≥ 90%, lebih baik dari B1 | lulus |
| G1 ketat | D 0/4: penanda "[Menunggu tinjauan ULD]" dihitung belum bermakna (`pass_ketat`) | dilaporkan | — |
| G3 | Fk terbit **440/440 = 1,00** [0,991; 1,00]; injeksi tertahan **137/138 = 0,993** | Fk ≥ 0,98; ≥ 0,90 | lulus |
| G3 (pembanding) | B2 terbit 60/60, 17 angka tidak setia pada 7/60 grafik; D 0 angka keliru terbit | — | — |
| G3 (biaya) | D terbit 40/60; beban tinjauan R = 20/60 (semua grafik tanpa label nilai) | dilaporkan | — |
| G4 | Q(D) = **1,00** (80/80); Q(B2) = 0,99 | Q ≥ 0,80 | lulus |
| G6 ringan | 6 PDF nyata (Common Crawl ac.id, 4 kampus): G1 D 6/6 (B0, B1 0/6); veraPDF penuh D 2/6; R = 18/18 | dilaporkan | — |

Catatan penting:
- Satu injeksi tukar label tidak tertahan karena kedua nilai berselisih 5 < ε·s = 6,74. Kesalahan di bawah ε memang tidak terdeteksi secara definisi.
- Audit pemeriksa B2 ada di `eval/audit_b2.md`. Kesalahan B2 yang bukan pembulatan semuanya berupa **rerata yang dihitung model** (mis. 1.107 vs 1.206,8). Inilah alasan SIMAK menghitung statistik dengan kode.
- Kalibrasi dua kali diperbaiki pada set dev sebelum set uji dibuka (riwayat di `simak/thresholds.json` dan `eval/kalibrasi_v1_sebelum_perbaikan.json`). v1 menunjukkan Fk 0,937 bahkan pada δ = 0: dua ekstraksi bisa *sepakat pada angka yang salah* untuk grafik tanpa label. Dari temuan ini lahir pemeriksaan **cL**.
- Pemetaan alt per halaman (fail-closed untuk figur vektor) ditambahkan setelah G6 menemukan Figure vektor yang tidak memiliki citra raster. Perubahan ini dipicu dokumen nyata, dan seluruh evaluasi dijalankan ulang sesudahnya.
- Temuan G6: di materi nyata, 13 dari 18 gambar adalah figur vektor dari Word/PowerPoint. Ekstraksi data langsung dari jalur vektor PDF (cadangan di Bab III.H) adalah langkah berikut yang paling berdampak untuk menurunkan R.

## Batasan (dilaporkan apa adanya)

- Kuota free tier Gemini Flash hanya 20 permintaan/hari/model. Karena itu evaluasi memakai Gemma, dan T1/T2 memakai model yang sama dengan dua perintah berbeda.
- Figur vektor (bukan citra raster) belum dideskripsikan; semuanya ditahan dengan penanda di PDF dan dihitung dalam R.
  Sejak branch `fitur/kartu-figur-vektor` (setelah tag v1.0-final), setiap Figure bertag tanpa citra terproses tampil
  sebagai kartu di antrean ULD dengan pratinjau dari `/BBox`. Pada halaman tanpa citra raster, keputusan ULD ditanam
  ke Figure yang tepat di PDF; pada halaman campuran PDF tetap berpenanda tahan dan keputusan hanya masuk HTML.
- Evaluasi dijalankan dua kali (VLM suhu 0 + cache): run 1 (12 Okt) dan run 2 (23 Okt) pada ambang yang sama; 0/60 status grafik berbeda (`python -m eval.banding_run eval/results_run1_2026-10-12.json eval/results.json`). Kedua run memakai model yang sama, jadi keduanya tidak mengukur variasi antarmodel.
- Rumus belum memakai pengenal kedua dan MathCAT, jadi seluruh rumus ditahan (fail-closed) dengan draf LaTeX + ucapan untuk ULD.
- Gambar dekoratif diberi `/Alt` "Hiasan (dekoratif)" di PDF; penandaan sebagai *Artifact* (menyunting aliran konten) belum dibuat. Di HTML sudah `alt=""`.
- Tabel yang tidak dikenali auto-tag tetap benar di HTML (deteksi PyMuPDF), tetapi di PDF bertag belum menjadi `Table/TH`.
- Pemeriksa angka B2 adalah pemeriksa pola pada teks bebas, sehingga Fk B2 berupa perkiraan.
- Set uji G1/G3/G4 sintetis buatan tim. G6 baru versi ringan: 6 PDF Common Crawl yang lolos aturan URL ternyata
  RPS, *module handbook*, SOP, dan pengumuman, bukan salindia; tidak ada grafik raster, sehingga R = 18/18.
  G2, G5, G6 penuh (60 dokumen, kappa, NVDA), dan G7 belum dijalankan.
- G1 menghitung teks alt penanda "[Menunggu tinjauan ULD] …" sebagai bermakna (aturannya hanya menolak kosong,
  "image N", nama berkas). Karena itu G1 ketat dilaporkan berdampingan.
- Hasil beku 12 Okt dibuat sebelum commit pertama; skema JSON ekstraksi berubah sesudahnya, sehingga kunci cache
  sebagian grafik uji tidak cocok dengan kode sekarang. Hash skema kini tercatat di manifes (`skema`).
