"""Membuat agen suara SIMAK di ElevenLabs lewat API, tanpa dashboard.

    python setup/buat_agen.py           # membuat 10 client tool + agen, mencetak ELEVENLABS_AGENT_ID
    python setup/buat_agen.py --paksa   # tetap membuat agen baru walau ELEVENLABS_AGENT_ID sudah ada

System prompt diambil dari setup/agen-elevenlabs.md (bagian 2) agar teksnya hanya ada di satu tempat.
Key dibaca dari environment (atau environment User Windows); tidak pernah dicetak.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1/convai"
DOK = Path(__file__).with_name("agen-elevenlabs.md")

TANPA_PARAM = {
    "daftar_materi": "Menyebutkan semua materi yang tersedia beserta nomornya.",
    "jeda": "Membiarkan materi tetap dijeda dan menutup percakapan.",
    "lanjut": "Melanjutkan materi dari posisi terakhir.",
    "ulangi": "Mengulang bagian yang sedang diputar dari awal.",
    "bagian_sebelumnya": "Kembali ke bagian sebelumnya dari materi.",
    "bagian_berikutnya": "Melompat ke bagian berikutnya dari materi.",
    "berhenti": "Menghentikan materi sepenuhnya.",
    "posisi": "Memberi tahu materi dan bagian yang sedang diputar.",
    "isi_sekitar": "Mengambil teks bagian yang sedang diputar dan dua bagian sebelumnya, untuk menjawab pertanyaan tentang isi materi.",
}
PUTAR = {
    "name": "putar_materi",
    "description": "Memutar materi dari awal. Isi nomor bila pengguna menyebut nomor, atau judul bila pengguna menyebut judul.",
    "parameters": {"type": "object", "required": [], "properties": {
        "nomor": {"type": "integer", "description": "Nomor materi sesuai daftar, mulai dari 1."},
        "judul": {"type": "string", "description": "Judul atau potongan judul materi seperti yang diucapkan pengguna."}}},
}

RINGKASAN = {
    "name": "ringkasan_materi",
    "description": "Memutar ringkasan materi (gambaran umum, bagian utama, istilah penting). Isi nomor atau judul bila "
                   "pengguna menyebut materi tertentu; kosongkan keduanya untuk materi yang sedang diputar.",
    "parameters": {"type": "object", "required": [], "properties": {
        "nomor": {"type": "integer", "description": "Nomor materi sesuai daftar, mulai dari 1."},
        "judul": {"type": "string", "description": "Judul atau potongan judul materi seperti yang diucapkan pengguna."}}},
}


def env(nama: str) -> str:
    v = os.environ.get(nama)
    if not v and sys.platform == "win32":  # variabel User yang belum masuk ke proses ini
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v = winreg.QueryValueEx(k, nama)[0]
        except OSError:
            v = None
    return v or ""


def kirim(path: str, body: dict) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs menolak {path} ({e.code}): {e.read().decode(errors='replace')[:800]}")


def prompt() -> str:
    teks = DOK.read_text(encoding="utf-8")
    m = re.search(r"## 2\. System prompt\s+```\n(.*?)```", teks, re.S)
    if not m:
        sys.exit(f"System prompt tidak ditemukan di {DOK.name}")
    return m.group(1).strip()


def main():
    if not env("ELEVENLABS_API_KEY") or not env("ELEVENLABS_VOICE_ID"):
        sys.exit("ELEVENLABS_API_KEY dan ELEVENLABS_VOICE_ID harus diatur dulu.")
    if env("ELEVENLABS_AGENT_ID") and "--paksa" not in sys.argv:
        sys.exit("ELEVENLABS_AGENT_ID sudah ada. Pakai --paksa untuk membuat agen baru.")
    alat = [{"name": n, "description": d, "parameters": None} for n, d in TANPA_PARAM.items()] + [PUTAR, RINGKASAN]
    ids = []
    for a in alat:
        cfg = {"type": "client", **{k: v for k, v in a.items() if v is not None},
               "expects_response": True, "response_timeout_secs": 10}
        ids.append(kirim("/tools", {"tool_config": cfg})["id"])
        print("tool dibuat:", a["name"])
    agen = kirim("/agents/create", {
        "name": "[SIMAK] Pemandu Suara",
        "conversation_config": {
            "agent": {
                "first_message": "{{sapaan}}",
                "language": "id",
                "dynamic_variables": {"dynamic_variable_placeholders": {
                    "sapaan": "Halo, saya SIMAK. Mau dengar materi apa?",
                    "daftar_materi": "Belum ada materi.",
                    "status_pemutar": "Belum ada materi yang diputar."}},
                "prompt": {"prompt": prompt(), "tool_ids": ids, "built_in_tools": {"end_call": {}}},
            },
            "tts": {"voice_id": env("ELEVENLABS_VOICE_ID"), "model_id": "eleven_flash_v2_5"},
            "turn": {"turn_timeout": 7, "turn_eagerness": "patient", "silence_end_call_timeout": 20},
            "conversation": {"max_duration_seconds": 600},
        },
        "platform_settings": {"auth": {"enable_auth": True}},
    })
    print("ELEVENLABS_AGENT_ID=" + agen["agent_id"])


if __name__ == "__main__":
    main()
