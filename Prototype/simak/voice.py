"""Suara ElevenLabs dan cache MP3. Key/voice dibaca dari environment server.

Pemutar memilih ElevenLabs saat tersedia; suara peramban menjadi pilihan lokal.
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from .config import CACHE, ROOT

AUDIO = CACHE / "audio"
AUDIO.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ angka → kata (bahasa Indonesia)
_SATUAN = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]


def terbilang(n: int) -> str:
    if n < 0:
        return "minus " + terbilang(-n)
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return _SATUAN[n - 10] + " belas"
    if n < 100:
        return _SATUAN[n // 10] + " puluh" + ("" if n % 10 == 0 else " " + _SATUAN[n % 10])
    if n < 200:
        return "seratus" + ("" if n == 100 else " " + terbilang(n - 100))
    if n < 1000:
        return _SATUAN[n // 100] + " ratus" + ("" if n % 100 == 0 else " " + terbilang(n % 100))
    if n < 2000:
        return "seribu" + ("" if n == 1000 else " " + terbilang(n - 1000))
    for unit, name in ((10 ** 12, "triliun"), (10 ** 9, "miliar"), (10 ** 6, "juta"), (1000, "ribu")):
        if n >= unit:
            head, rest = divmod(n, unit)
            return terbilang(head) + " " + name + ("" if rest == 0 else " " + terbilang(rest))
    return str(n)


_NUM = re.compile(r"(?<![\w])(-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?)(?![\w])")


def _say_number(tok: str) -> str:
    neg = tok.startswith("-")
    tok = tok.lstrip("-")
    whole, _, frac = tok.replace(".", "").partition(",")
    out = terbilang(int(whole))
    if frac:
        out += " koma " + " ".join(_SATUAN[int(d)] for d in frac)
    return ("minus " if neg else "") + out


def normalize(text: str) -> str:
    """Siapkan teks untuk diucapkan: angka menjadi kata, satuan umum dieja."""
    text = text.replace("%", " persen").replace("“", "").replace("”", "").replace("·", ",")
    text = re.sub(r"\s*\(([^)]*)\)", r", \1", text)
    text = _NUM.sub(lambda m: _say_number(m.group(1)), text)
    text = re.sub(r"\s*,\s*(,\s*)+", ", ", text)
    return re.sub(r"\s+([,.;])", r"\1", text)


# ------------------------------------------------------------------ suara manusia (ElevenLabs, berbayar)
# Suara hasil kloning/pelatihan dari rekaman manusia (dengan izin pemiliknya) di akun ElevenLabs sendiri.
# Key dan voice id dibaca dari environment variable; teks yang dibacakan dikirim ke layanan ElevenLabs.
ELEVEN_SPEAKER = "eleven"
PAID_SPEAKERS = {ELEVEN_SPEAKER}  # dipakai server agar tidak membuat audio massal di latar belakang
ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def eleven_ready() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_VOICE_ID"))


class VoiceError(RuntimeError):
    """Pesan aman untuk pengguna; tidak berisi respons layanan atau kredensial."""


def _eleven(text: str, out: Path, rate: str):
    if not eleven_ready():
        raise VoiceError("Suara ElevenLabs belum dikonfigurasi. Pilih suara peramban.")
    speed = max(0.7, min(1.2, 1 + int(rate.rstrip("%")) / 100))
    body = json.dumps({"text": text, "model_id": ELEVEN_MODEL,
                       "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.0, "speed": speed}})
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{os.environ['ELEVENLABS_VOICE_ID']}?output_format=mp3_44100_128",
        data=body.encode(), method="POST",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    temporary = out.with_suffix(f".{uuid.uuid4().hex}.tmp")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            audio = r.read()
        if not audio:
            raise VoiceError("ElevenLabs mengembalikan audio kosong. Coba lagi atau pilih suara peramban.")
        temporary.write_bytes(audio)
        temporary.replace(out)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            message = "Akses ElevenLabs ditolak. Periksa API key dan izin voice di server."
        elif e.code == 404:
            message = "Voice ElevenLabs tidak ditemukan atau belum tersedia pada akun ini."
        elif e.code == 429:
            message = "Kuota atau batas permintaan ElevenLabs tercapai. Coba lagi atau pilih suara peramban."
        else:
            message = "ElevenLabs sedang tidak tersedia. Coba lagi atau pilih suara peramban."
        raise VoiceError(message) from None
    except (urllib.error.URLError, TimeoutError):
        raise VoiceError("Koneksi ElevenLabs terputus. Coba lagi atau pilih suara peramban.") from None
    finally:
        temporary.unlink(missing_ok=True)


def agent_ready() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_AGENT_ID"))


def agent_signed_url() -> str:
    """URL sesi sementara untuk agen percakapan; API key tidak pernah sampai ke peramban."""
    if not agent_ready():
        raise VoiceError("Agen ElevenLabs belum dikonfigurasi (ELEVENLABS_AGENT_ID).")
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url?agent_id="
        + urllib.parse.quote(os.environ["ELEVENLABS_AGENT_ID"]),
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["signed_url"]
    except urllib.error.HTTPError as e:
        raise VoiceError("Agen ElevenLabs menolak sesi. Periksa API key dan ELEVENLABS_AGENT_ID."
                         if e.code in (401, 403, 404) else "Agen ElevenLabs sedang tidak tersedia.") from None
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
        raise VoiceError("Koneksi ke agen ElevenLabs terputus.") from None


def cache_path(text: str, speaker: str = ELEVEN_SPEAKER, rate: str = "+0%") -> Path:
    """Letak MP3 untuk teks dan pengaturan ini; teks yang diperbaiki ULD otomatis mendapat berkas baru."""
    if speaker != ELEVEN_SPEAKER:
        raise ValueError(f"Sumber suara tidak didukung: {speaker}")
    key = hashlib.sha256(f"{speaker}|{ELEVEN_MODEL}|{os.environ.get('ELEVENLABS_VOICE_ID')}|{rate}|{normalize(text)}".encode()).hexdigest()[:20]
    return AUDIO / f"{key}.mp3"


def cached(text: str) -> bool:
    out = cache_path(text)
    return out.exists() and out.stat().st_size > 0


def synthesize(text: str, speaker: str = ELEVEN_SPEAKER, rate: str = "+0%", pitch: str = "+0Hz", tau: float = 0.3) -> Path:
    """Teks → berkas MP3 dengan suara ElevenLabs; hasil di-cache menurut isi dan pengaturan."""
    out = cache_path(text, speaker, rate)
    if not out.exists() or not out.stat().st_size:
        _eleven(normalize(text), out, rate)
    return out
