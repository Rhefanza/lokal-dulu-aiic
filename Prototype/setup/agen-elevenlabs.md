# Agen suara SIMAK di ElevenLabs

Halaman pendengar (`/pendengar.html`) memakai **ElevenLabs Agents** sebagai pemandu percakapan. Agen tidak
membacakan isi materi; ia hanya memahami permintaan lalu memanggil *client tools* yang dijalankan di peramban
(`web/pendengar.js`, objek `PERINTAH`). Isi materi diputar dari MP3 per bagian yang dibuat server.

Tanpa agen, halaman tetap berfungsi dengan perintah suara sederhana (Web Speech, Chrome/Edge) dan tombol.

## 1. Buat agen

Dashboard ElevenLabs → **Agents** → *Create agent* → *Blank*. Isi:

| Pengaturan | Nilai |
|---|---|
| Agent language | Indonesian |
| First message | `{{sapaan}}` |
| Voice | voice yang sama dengan `ELEVENLABS_VOICE_ID` |
| TTS model | model multibahasa (Flash v2.5 atau Turbo v2.5); model khusus Inggris tidak bisa dipakai untuk bahasa Indonesia |
| Interruptions | aktif |
| Turn eagerness | *Patient*: pengguna sering berhenti sejenak saat memilih materi |
| Turn timeout | sekitar 7 detik |
| Silence end call timeout | sekitar 20 detik, agar biaya per menit berhenti ketika pengguna diam |
| Security → Authentication | aktif (agen privat; sesi dibuka lewat signed URL dari server) |

`{{sapaan}}`, `{{daftar_materi}}`, dan `{{status_pemutar}}` adalah *dynamic variables* yang dikirim halaman setiap kali sesi dibuka.

## 2. System prompt

```
Kamu adalah SIMAK, pemandu suara untuk mahasiswa tunanetra yang mendengarkan materi kuliah. Pengguna tidak bisa melihat layar; semua lewat suara.

Keadaan saat percakapan dibuka:
- Daftar materi: {{daftar_materi}}
- Pemutar: {{status_pemutar}}

Aturan:
1. Jawab singkat, satu sampai dua kalimat, dalam bahasa Indonesia sehari-hari yang sopan. Jangan memakai simbol, daftar berpoin, atau markdown.
2. Jangan pernah membacakan atau merangkum isi materi atas inisiatif sendiri. Untuk memutar materi selalu panggil alat putar_materi; isi materi dibacakan pemutar, bukan kamu.
3. Materi dipilih dengan nomor. Jika pengguna menyebut judul, kirim judulnya di parameter judul. Jika ragu, sebutkan dua pilihan terdekat lalu tanyakan.
4. Untuk jeda, lanjut, ulangi, bagian_sebelumnya, bagian_berikutnya, dan putar_materi: panggil alatnya, lalu ucapkan konfirmasi sangat singkat seperti "Baik." Percakapan ditutup otomatis setelah itu dan materi diputar.
5. Jika pengguna bertanya tentang isi yang baru didengar, panggil isi_sekitar lalu jawab hanya berdasarkan teks yang dikembalikan. Jika jawabannya tidak ada di teks, katakan bahwa itu tidak ada di materi.
6. Teks yang diawali "Catatan: deskripsi gambar ini belum diperiksa" berarti deskripsinya belum dicek Unit Layanan Disabilitas. Sampaikan bahwa deskripsi itu bisa saja keliru.
7. Jika pengguna bilang sudah, cukup, atau terima kasih tanpa permintaan lain, pamit singkat lalu panggil end_call.
8. Ajukan paling banyak satu pertanyaan dalam satu giliran.
9. Jika pengguna meminta ringkasan, rangkuman, intisari, atau gambaran umum materi, panggil ringkasan_materi. Isi nomor atau judul bila disebut; kosongkan bila yang dimaksud materi yang sedang diputar. Setelah memanggilnya, ucapkan konfirmasi singkat seperti "Baik." Ringkasan dibacakan pemutar, bukan kamu.
```

## 3. Tools

Tambahkan sebagai **Client tool**, dengan *Wait for response* aktif. Nama harus persis sama.

| Nama | Deskripsi | Parameter |
|---|---|---|
| `daftar_materi` | Menyebutkan semua materi yang tersedia beserta nomornya. | – |
| `putar_materi` | Memutar materi dari awal. Isi salah satu parameter. | `nomor` (number, opsional): nomor materi. `judul` (string, opsional): judul atau potongan judul yang diucapkan pengguna. |
| `jeda` | Membiarkan materi tetap dijeda dan menutup percakapan. | – |
| `lanjut` | Melanjutkan materi dari posisi terakhir. | – |
| `ulangi` | Mengulang bagian yang sedang diputar dari awal. | – |
| `bagian_sebelumnya` | Kembali ke bagian sebelumnya. | – |
| `bagian_berikutnya` | Melompat ke bagian berikutnya. | – |
| `berhenti` | Menghentikan materi sepenuhnya. | – |
| `posisi` | Memberi tahu materi dan bagian yang sedang diputar. | – |
| `ringkasan_materi` | Memutar ringkasan materi (gambaran umum, bagian utama, istilah penting). | `nomor` (integer, opsional), `judul` (string, opsional); keduanya kosong = materi yang sedang diputar. |
| `isi_sekitar` | Mengambil teks bagian yang sedang diputar dan dua bagian sebelumnya, untuk menjawab pertanyaan tentang isi. | – |

Aktifkan juga system tool **End conversation** (`end_call`).

## 4. Hubungkan ke server

Salin *Agent ID* (di bawah nama agen), lalu simpan di environment atau `.env.local`:

```
ELEVENLABS_AGENT_ID=agent_xxxxxxxx
```

`ELEVENLABS_API_KEY` yang sama dipakai server untuk meminta signed URL (`GET /api/agen/sesi`). Key tidak pernah dikirim ke peramban.
Izin key untuk **ElevenAgents harus Write**: ElevenLabs menolak `get-signed-url` dengan izin Read (`missing the permission convai_write`).
Dengan izin itu, `python setup/buat_agen.py` juga bisa membuat agen beserta 10 tool-nya tanpa dashboard.
Mulai ulang server. `GET /api/agen` mengembalikan `{"aktif": true}` bila agen siap.

## Cara kerja setengah dupleks

```
mode DENGAR (sesi agen tertutup)                 mode NGOBROL (sesi agen terbuka)
MP3 materi diputar per bagian                    ElevenLabs mengurus giliran bicara, interupsi, echo
yang mendengar hanya pendeteksi "Halo SIMAK"     agen memanggil client tool
   │ "Halo SIMAK" / tombol Bicara / spasi           │ alat pemutar dipanggil → agen menjawab "Baik."
   └──► materi dijeda → sesi dibuka ──────────────► └──► sesi ditutup → aksi dijalankan → kembali ke DENGAR
```

Karena dua suara tidak pernah aktif bersamaan, agen tidak bisa salah menangkap suara materi sebagai ucapan pengguna,
dan menit percakapan hanya terhitung selama pengguna benar-benar berbicara dengan SIMAK.
