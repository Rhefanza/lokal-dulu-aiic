/* Halaman pendengar (tunanetra). Tidak memuat kredensial.

   Satu lapisan perintah (PERINTAH) dipakai oleh agen ElevenLabs, perintah suara sederhana, tombol, dan keyboard.
   Setengah dupleks: selama materi diputar sesi agen ditutup dan yang mendengar hanya pendeteksi "Halo SIMAK".
   Begitu terdeteksi (atau tombol Bicara/spasi ditekan), materi dijeda dulu, baru agen dibuka. Aksi yang
   memutar materi ditunda sampai agen selesai menjawab, lalu sesi ditutup supaya dua suara tidak pernah tumpang tindih. */
(() => {
  const $ = s => document.querySelector(s);
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const WAKE = /\b(halo|hallo|helo|hai|hei|hey|oke|ok)\s*,?\s*(si ?mak|semak|cimak|simak)\b/;
  const BANTUAN = 'Perintah yang bisa diucapkan: daftar materi, putar nomor satu, jeda, lanjut, ulangi, sebelumnya, berikutnya, berhenti, dan posisi.';
  const SENYAP = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';

  const S = {
    materi: [],        // [{id, judul}] urut nomor
    aktif: null,       // {id, judul, bagian: [{el, teks}]}
    i: 0,
    status: 'diam',    // diam | putar | jeda
    mode: 'dengar',    // dengar | ngobrol
    peramban: false,   // bagian ini dibacakan suara peramban karena audio server gagal
    agenSiap: false,
    sesi: null,
    membuka: false,
    tertunda: null,    // aksi pemutar yang menunggu agen selesai bicara
    sudahBicara: false,
    timer: [],
  };
  const audio = new Audio();   // materi
  const suara = new Audio();   // ucapan pemandu saat tanpa agen
  audio.preload = 'auto';

  // ------------------------------------------------------------------ tampilan
  function tampil(pesan) { if (pesan) $('#pesan').textContent = pesan; }
  function catat(siapa, teks) {
    const li = document.createElement('li');
    li.innerHTML = '<b></b> ';
    li.firstChild.textContent = siapa + ':';
    li.append(teks);
    $('#transkrip').prepend(li);
    while ($('#transkrip').children.length > 10) $('#transkrip').lastChild.remove();
  }
  function perbaruiUI() {
    const n = S.aktif?.bagian.length || 0;
    $('#judul').textContent = S.aktif?.judul || 'SIMAK';
    $('#bar').style.width = n ? `${Math.round((S.i + (S.status === 'diam' ? 0 : 1)) / n * 100)}%` : '0';
    $('#mode').textContent = S.mode === 'ngobrol' ? 'Bicara dengan SIMAK'
      : {putar: 'Memutar materi', jeda: 'Dijeda', diam: 'Siap'}[S.status];
    $('#b-jeda').textContent = S.status === 'putar' ? 'Jeda' : 'Lanjut';
    document.querySelectorAll('.kendali button').forEach(b => { b.disabled = !S.aktif; });
    const b = $('#bicara');
    b.dataset.mode = S.mode;
    $('#bicara-label').textContent = S.mode === 'ngobrol' ? 'Selesai bicara' : 'Bicara';
    $('#bicara-ket').textContent = S.mode === 'ngobrol' ? 'Sentuh untuk menutup percakapan.'
      : SR ? 'atau ucapkan “Halo SIMAK”. Tombol spasi juga bisa.' : 'Peramban ini belum mendukung panggilan suara; sentuh tombol ini untuk bicara.';
    document.querySelectorAll('#pilihan button').forEach(x => x.setAttribute('aria-current', String(x.dataset.id === S.aktif?.id)));
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = S.status === 'putar' ? 'playing' : S.status === 'jeda' ? 'paused' : 'none';
      if (S.aktif) navigator.mediaSession.metadata = new MediaMetadata({title: S.aktif.judul, artist: 'SIMAK', album: `Bagian ${S.i + 1} dari ${n}`});
    }
  }

  // ------------------------------------------------------------------ materi
  async function muatMateri() {
    try {
      const d = await fetch('/api/materi').then(r => r.json());
      S.materi = d.materi.map(m => ({id: m.id, judul: m.judul}));
    } catch (_) {}
    $('#pilihan').innerHTML = S.materi.map((m, k) => `<li><button data-id="${m.id}"><b>Nomor ${k + 1}</b></button></li>`).join('');
    document.querySelectorAll('#pilihan button').forEach((b, k) => b.append(S.materi[k].judul));
    perbaruiUI();
  }
  const teksDaftar = () => S.materi.length
    ? `Ada ${S.materi.length} materi. ` + S.materi.map((m, k) => `Nomor ${k + 1}, ${m.judul}.`).join(' ')
    : 'Belum ada materi. Minta Unit Layanan Disabilitas mengunggah materi terlebih dahulu.';
  const teksPosisi = () => S.aktif
    ? `${S.aktif.judul}, bagian ${S.i + 1} dari ${S.aktif.bagian.length}, ${S.status === 'putar' ? 'sedang diputar' : 'dijeda'}.`
    : 'Belum ada materi yang diputar.';

  const ANGKA = {satu: 1, pertama: 1, dua: 2, kedua: 2, tiga: 3, ketiga: 3, empat: 4, keempat: 4, lima: 5, kelima: 5,
    enam: 6, keenam: 6, tujuh: 7, ketujuh: 7, delapan: 8, kedelapan: 8, sembilan: 9, kesembilan: 9, sepuluh: 10, kesepuluh: 10};
  const UMUM = new Set(['materi', 'putar', 'putarkan', 'tolong', 'yang', 'dan', 'dengan', 'untuk', 'tentang', 'mau', 'ingin',
    'dengar', 'dengarkan', 'buka', 'bacakan', 'baca', 'mainkan', 'saya', 'aku']);
  const kata = s => String(s).toLowerCase().normalize('NFKD').replace(/[^\p{L}\p{N}\s]/gu, ' ').split(/\s+/).filter(w => w.length > 2 && !UMUM.has(w));
  const angka = w => /^\d{1,2}$/.test(w) ? Number(w) : ANGKA[w] || null;

  function cariMateri({nomor, judul}) {
    if (nomor) return S.materi[nomor - 1] || null;
    const q = kata(judul || '');
    let terbaik = null, skor = 0;
    for (const m of S.materi) {
      const w = kata(m.judul);
      const s = q.filter(x => w.some(y => y.startsWith(x) || x.startsWith(y))).length;
      if (s > skor) { skor = s; terbaik = m; }
    }
    return terbaik;
  }

  // ------------------------------------------------------------------ pemutar
  const urlAudio = k => `/api/materi/${S.aktif.id}/audio/${k}`;

  async function mulaiMateri(m) {
    const d = await fetch(`/api/materi/${m.id}/putar`).then(r => r.ok ? r.json() : Promise.reject());
    S.aktif = {id: d.id, judul: d.judul, bagian: d.bagian};
    putarBagian(0);
  }

  function putarBagian(k) {
    if (!S.aktif) return;
    k = Math.max(0, k);
    if (k >= S.aktif.bagian.length) return selesaiMateri();
    speechSynthesis.cancel();
    S.i = k; S.status = 'putar'; S.peramban = false;
    audio.src = urlAudio(k);
    audio.play().catch(() => { if (S.status === 'putar' && S.i === k && !S.peramban) bacaPeramban(k); });
    if (k + 1 < S.aktif.bagian.length) fetch(urlAudio(k + 1)).catch(() => {});  // siapkan bagian berikutnya
    tampil(S.aktif.bagian[k].teks.slice(0, 220));
    perbaruiUI();
  }
  audio.onended = () => { if (S.status === 'putar' && !S.peramban) putarBagian(S.i + 1); };
  audio.onerror = () => { if (S.status === 'putar' && !S.peramban && audio.getAttribute('src')) bacaPeramban(S.i); };

  function bacaPeramban(k) {  // audio ElevenLabs tidak tersedia: bagian ini dibacakan suara perangkat
    S.peramban = true;
    const u = new SpeechSynthesisUtterance(S.aktif.bagian[k].teks);
    u.lang = 'id-ID';
    u.onend = () => { if (S.status === 'putar' && S.i === k && S.peramban) putarBagian(k + 1); };
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }

  function jeda() {
    if (S.status !== 'putar') return;
    S.status = 'jeda';
    audio.pause();
    speechSynthesis.cancel();  // pause() suara peramban tidak andal di Chrome; lanjut mengulang bagiannya
    perbaruiUI();
  }
  function lanjut() {
    if (!S.aktif) return;
    if (S.status === 'jeda' && !S.peramban && audio.getAttribute('src')) {
      S.status = 'putar';
      audio.play().catch(() => bacaPeramban(S.i));
      perbaruiUI();
    } else if (S.status !== 'putar') putarBagian(S.i);
  }
  function berhenti() {
    S.status = 'diam'; S.aktif = null; S.i = 0;
    audio.pause(); audio.removeAttribute('src');
    speechSynthesis.cancel();
    perbaruiUI();
  }
  function selesaiMateri() {
    const j = S.aktif.judul;
    berhenti();
    ucap(`Materi ${j} selesai. Ucapkan Halo SIMAK atau sentuh tombol Bicara untuk memilih materi lain.`);
  }

  // ------------------------------------------------------------------ lapisan perintah
  // Setiap perintah mengembalikan {pesan, aksi?}. Aksi pemutar dijalankan langsung, atau ditunda saat agen masih bicara.
  const tanpaMateri = () => ({pesan: 'Belum ada materi yang diputar. ' + teksDaftar()});
  const pemutar = (pesan, aksi) => () => S.aktif ? {pesan, aksi} : tanpaMateri();
  const PERINTAH = {
    daftar_materi: async () => { await muatMateri(); return {pesan: teksDaftar()}; },
    posisi: () => ({pesan: teksPosisi()}),
    putar_materi: async ({nomor, judul} = {}) => {
      await muatMateri();
      const m = cariMateri({nomor: Number(nomor) || null, judul});
      if (!m) return {pesan: `Materi itu tidak ditemukan. ${teksDaftar()}`};
      return {pesan: `Memutar ${m.judul}.`, aksi: () => mulaiMateri(m).catch(() => ucap('Materi gagal dimuat. Coba lagi.'))};
    },
    jeda: pemutar('Materi dijeda.', jeda),
    lanjut: pemutar('Melanjutkan.', lanjut),
    ulangi: pemutar('Mengulang bagian ini.', () => putarBagian(S.i)),
    bagian_sebelumnya: pemutar('Kembali ke bagian sebelumnya.', () => putarBagian(S.i - 1)),
    bagian_berikutnya: pemutar('Ke bagian berikutnya.', () => putarBagian(S.i + 1)),
    berhenti: () => { const ada = !!S.aktif; berhenti(); return {pesan: ada ? 'Pemutaran dihentikan.' : 'Tidak ada materi yang diputar.'}; },
    isi_sekitar: () => {  // bahan agen untuk menjawab pertanyaan tentang isi yang baru didengar
      if (!S.aktif) return tanpaMateri();
      const awal = Math.max(0, S.i - 2);
      return {pesan: `Materi ${S.aktif.judul}.\n` + S.aktif.bagian.slice(awal, S.i + 2)
        .map((b, k) => (awal + k === S.i ? '[Bagian yang sedang diputar] ' : '') + b.teks).join('\n')};
    },
  };

  // Perintah suara sederhana saat agen tidak tersedia.
  function tafsir(t) {
    t = t.toLowerCase();
    const w = t.split(/\s+/);
    const no = t.match(/\b(?:nomor|no|materi|yang)\s+(\S+)/);
    if (no && angka(no[1])) return ['putar_materi', {nomor: angka(no[1])}];
    if (w.length <= 2 && w.some(angka)) return ['putar_materi', {nomor: angka(w.find(angka))}];
    if (/daftar|pilihan|ada apa saja|materi apa/.test(t)) return ['daftar_materi'];
    if (/jeda|tunggu|pause/.test(t)) return ['jeda'];
    if (/lanjut|teruskan|resume/.test(t)) return ['lanjut'];
    if (/ulang/.test(t)) return ['ulangi'];
    if (/sebelum|mundur/.test(t)) return ['bagian_sebelumnya'];
    if (/berikut|maju|lewati|skip/.test(t)) return ['bagian_berikutnya'];
    if (/berhenti|stop|hentikan/.test(t)) return ['berhenti'];
    if (/posisi|di mana|sampai mana/.test(t)) return ['posisi'];
    if (/bantu|perintah/.test(t)) return ['bantuan'];
    if (/putar|buka|dengar|baca|mainkan|materi/.test(t) && cariMateri({judul: t})) return ['putar_materi', {judul: t}];
    return null;
  }
  async function tafsirLLM(t) {  // salah dengar atau kalimat bebas: LLM server memilih perintah terdekat
    const opsi = [['daftar_materi'], ['jeda'], ['lanjut'], ['ulangi'], ['bagian_sebelumnya'], ['bagian_berikutnya'], ['berhenti'], ['posisi'],
      ...S.materi.map((m, k) => ['putar_materi', {nomor: k + 1}])];
    const label = ['daftar materi', 'jeda', 'lanjut', 'ulangi bagian ini', 'bagian sebelumnya', 'bagian berikutnya', 'berhenti', 'posisi sekarang',
      ...S.materi.map(m => 'putar materi ' + m.judul)];
    try {
      const r = await fetch('/api/perintah', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ucapan: t, tombol: label})});
      const {pilihan} = await r.json();
      return Number.isInteger(pilihan) ? opsi[pilihan] : null;
    } catch (_) { return null; }
  }

  // ------------------------------------------------------------------ suara pemandu dan pendengaran
  function ucap(teks) {
    tampil(teks); catat('SIMAK', teks);
    const dengarLagi = S.mode === 'dengar';
    berhentiDengar();  // jangan sampai pendeteksi mendengar suara pemandu sendiri
    return new Promise(async selesai => {
      const akhir = () => { if (dengarLagi && S.mode === 'dengar') mulaiDengar(); selesai(); };
      try {
        const r = await fetch('/api/suara', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({teks})});
        if (!r.ok) throw new Error();
        suara.src = URL.createObjectURL(await r.blob());
        suara.onended = suara.onerror = akhir;
        await suara.play();
      } catch (_) {
        const u = new SpeechSynthesisUtterance(teks);
        u.lang = 'id-ID';
        u.onend = u.onerror = akhir;
        speechSynthesis.speak(u);
      }
    });
  }

  let rek = null, ingin = false, rekSekali = null;
  function mulaiDengar() {  // pendeteksi "Halo SIMAK" yang berjalan terus selama mode dengar
    ingin = true;
    if (!SR || rek || S.mode !== 'dengar') return;
    rek = new SR();
    rek.lang = 'id-ID'; rek.continuous = true; rek.interimResults = true;
    rek.onresult = e => {
      for (let k = e.resultIndex; k < e.results.length; k++) {
        if (WAKE.test(e.results[k][0].transcript.toLowerCase())) { berhentiDengar(); sela(); return; }
      }
    };
    rek.onerror = e => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        ingin = false;
        tampil('Mikrofon tidak diizinkan. Tombol Bicara dan spasi tetap bisa dipakai.');
      }
    };
    rek.onend = () => { rek = null; if (ingin && S.mode === 'dengar') setTimeout(mulaiDengar, 250); };
    try { rek.start(); } catch (_) { rek = null; }
  }
  function berhentiDengar() {
    ingin = false;
    if (rek) { rek.onend = null; try { rek.abort(); } catch (_) {} rek = null; }
  }
  function dengarSekali(batas = 7000) {
    return new Promise(selesai => {
      if (!SR) return selesai('');
      const r = new SR();
      let hasil = '';
      r.lang = 'id-ID'; r.interimResults = false;
      r.onresult = e => { hasil = e.results[0][0].transcript; };
      r.onend = () => { clearTimeout(t); selesai(hasil); };
      r.onerror = () => {};
      const t = setTimeout(() => { try { r.stop(); } catch (_) {} }, batas);
      rekSekali = r;
      try { r.start(); tampil('Mendengarkan…'); } catch (_) { clearTimeout(t); selesai(''); }
    });
  }

  // ------------------------------------------------------------------ percakapan
  async function sela() {  // "Halo SIMAK", tombol Bicara, atau spasi
    if (S.mode === 'ngobrol') {  // sentuhan kedua menutup percakapan
      if (S.sesi) return tutupAgen();
      try { rekSekali?.stop(); } catch (_) {}
      return;
    }
    jeda();
    const sapaan = S.aktif ? `Ya? ${S.aktif.judul} dijeda.` : 'Ya? Ada yang bisa dibantu?';
    if (S.agenSiap) bukaAgen(sapaan); else perintahSederhana(sapaan);
  }

  async function perintahSederhana(pembuka) {
    S.mode = 'ngobrol'; berhentiDengar(); perbaruiUI();
    await ucap(pembuka);
    const t = SR ? await dengarSekali() : '';
    S.mode = 'dengar'; perbaruiUI();
    if (!t) {
      if (SR) await ucap(S.aktif ? 'Tidak terdengar perintah. Materi tetap dijeda.' : 'Tidak terdengar perintah.');
      return mulaiDengar();
    }
    catat('Kamu', t);
    const p = tafsir(t) || await tafsirLLM(t);
    const r = !p ? {pesan: 'Maaf, saya belum paham. ' + BANTUAN}
      : p[0] === 'bantuan' ? {pesan: BANTUAN} : await PERINTAH[p[0]](p[1] || {});
    await ucap(r.pesan);
    r.aksi?.();
    mulaiDengar();
    perbaruiUI();
  }

  function alatAgen() {
    const alat = {};
    for (const [nama, fn] of Object.entries(PERINTAH)) {
      alat[nama] = async (p) => {
        const r = await fn(p || {});
        if (r.aksi) tunda(r.aksi);
        tampil(r.pesan);
        return r.pesan;
      };
    }
    return alat;
  }
  function tunda(aksi) {
    S.tertunda = aksi; S.sudahBicara = false;
    S.timer.forEach(clearTimeout);
    S.timer = [setTimeout(() => { if (S.tertunda && !S.sudahBicara) tutupAgen(); }, 4000),  // agen tidak menjawab setelah alat
      setTimeout(() => { if (S.tertunda) tutupAgen(); }, 15000)];
  }

  async function bukaAgen(sapaan) {
    if (S.sesi || S.membuka) return;
    S.membuka = true; S.mode = 'ngobrol'; S.tertunda = null;
    berhentiDengar(); perbaruiUI(); tampil('Menyambungkan…');
    try {
      const r = await fetch('/api/agen/sesi');
      const j = await r.json();
      if (!r.ok) throw new Error(j.detail);
      S.sesi = await window.ElevenLabsConversation.startSession({
        signedUrl: j.signed_url,
        connectionType: 'websocket',
        dynamicVariables: {sapaan, daftar_materi: teksDaftar(), status_pemutar: teksPosisi()},
        clientTools: alatAgen(),
        onModeChange: ({mode}) => {
          if (mode === 'speaking') S.sudahBicara = true;
          else if (S.tertunda && S.sudahBicara) tutupAgen();  // jawaban selesai: tutup sesi, lalu jalankan aksi
        },
        onMessage: ({message, role, source}) => {
          const agen = (role || source) !== 'user';
          catat(agen ? 'SIMAK' : 'Kamu', message);
          if (agen) tampil(message);
        },
        onDisconnect: setelahAgen,
        onError: m => console.warn('Agen:', m),
      });
    } catch (e) {
      console.warn(e);
      S.agenSiap = false;  // jatuh ke perintah sederhana sampai halaman dimuat ulang
      S.mode = 'dengar';
      perintahSederhana('Asisten suara sedang tidak tersambung. Saya pakai perintah sederhana. ' + sapaan);
    } finally {
      S.membuka = false;
    }
  }
  function tutupAgen() { S.sesi?.endSession(); }
  function setelahAgen() {
    S.sesi = null; S.mode = 'dengar';
    S.timer.forEach(clearTimeout);
    const aksi = S.tertunda;
    S.tertunda = null;
    if (aksi) aksi();
    else if (S.status === 'jeda') tampil('Materi dijeda. Ucapkan “Halo SIMAK” atau sentuh Bicara untuk melanjutkan.');
    mulaiDengar();
    perbaruiUI();
  }

  // Tombol: dipakai pendamping yang melihat, keyboard, dan pembaca layar. Saat agen bicara, aksi menunggu sesi ditutup.
  function jalankan(aksi) {
    if (S.sesi) { S.tertunda = aksi; tutupAgen(); } else aksi();
  }
  const KENDALI = {
    sebelumnya: () => putarBagian(S.i - 1),
    jedaLanjut: () => (S.status === 'putar' ? jeda() : lanjut()),
    ulangi: () => putarBagian(S.i),
    berikutnya: () => putarBagian(S.i + 1),
    berhenti,
  };
  document.querySelector('.kendali').onclick = e => { const b = e.target.closest('[data-k]'); if (b) jalankan(KENDALI[b.dataset.k]); };
  $('#pilihan').onclick = e => {
    const b = e.target.closest('[data-id]');
    const m = b && S.materi.find(x => x.id === b.dataset.id);
    if (m) jalankan(() => mulaiMateri(m));
  };
  $('#bicara').onclick = sela;
  if ('mediaSession' in navigator) {  // tombol putar/jeda di earphone atau keyboard media
    navigator.mediaSession.setActionHandler('play', () => jalankan(lanjut));
    navigator.mediaSession.setActionHandler('pause', () => jalankan(jeda));
    navigator.mediaSession.setActionHandler('nexttrack', () => jalankan(KENDALI.berikutnya));
    navigator.mediaSession.setActionHandler('previoustrack', () => jalankan(KENDALI.sebelumnya));
  }

  // ------------------------------------------------------------------ sentuhan pertama
  // Peramban tidak mengizinkan suara atau mikrofon sebelum ada interaksi; seluruh layar menjadi tombol mulai.
  async function mulai() {
    if ($('#mulai').hidden) return;
    $('#mulai').hidden = true; $('#isi').hidden = false; $('#bicara').focus();
    for (const a of [audio, suara]) { a.src = SENYAP; a.play().catch(() => {}); }  // buka kunci autoplay di dalam gestur
    await muatMateri();
    const ag = await fetch('/api/agen').then(r => r.json()).catch(() => ({}));
    S.agenSiap = !!ag.aktif && !!window.ElevenLabsConversation;
    const sapaan = `Halo, saya SIMAK. ${teksDaftar()} Mau dengar yang mana?`;
    if (S.agenSiap) bukaAgen(sapaan); else perintahSederhana(sapaan + (SR ? ' Sebutkan nomornya.' : ' Pilih dari daftar materi.'));
  }
  $('#mulai').onclick = mulai;
  document.addEventListener('keydown', e => {
    if (!$('#mulai').hidden) {  // tombol pengubah dan tombol pembaca layar (NVDA/JAWS) tidak memulai
      if (!['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Insert', 'Tab'].includes(e.key)) { e.preventDefault(); mulai(); }
      return;
    }
    if (e.key === 'Escape' && S.sesi) return tutupAgen();
    if (e.key === ' ' && !e.target.closest('button, input, textarea, select, summary')) { e.preventDefault(); sela(); }
  });
  $('#mulai').focus();
  window.SIMAK = {S, PERINTAH, tafsir};  // pemeriksaan di konsol
})();
