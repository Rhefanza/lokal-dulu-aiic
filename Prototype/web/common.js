// Komponen bersama SIMAK: panel editorial dan bukti yang dapat ditelusuri.
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : '';
const fmtId = v => typeof v === 'string' ? v : Number(v).toLocaleString('id-ID', {maximumFractionDigits: 2});
const norm = s => String(s).toLowerCase().normalize('NFKC').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const $ = s => document.querySelector(s);

// Ikon garis 24px, satu ketebalan; dekoratif (aria-hidden) kecuali diberi label di elemen induk.
const ICON_PATHS = {
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  cross: '<path d="M6 6l12 12M18 6L6 18"/>',
  hold: '<rect x="5" y="4" width="14" height="16" rx="1.5"/><path d="M9 9h6M9 13h6M9 17h3"/>',
  alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.5v.01"/>',
  play: '<path d="M8 5.5v13l11-6.5z"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  prev: '<path d="M18 6l-8 6 8 6zM6 6v12"/>',
  next: '<path d="M6 6l8 6-8 6zM18 6v12"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5M5 20h14"/>',
  doc: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>',
  open: '<path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/>',
  trash: '<path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/>',
  inject: '<path d="M14 4l6 6M17 7l-9 9-3 1 1-3 9-9M4 20l2-2"/>',
  undo: '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 010 10h-3"/>',
  gauge: '<path d="M4 18a8 8 0 1116 0"/><path d="M12 18l4-6"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  chart: '<path d="M4 20V4M4 20h16"/><path d="M8 16v-4M12 16V8M16 16v-6"/>',
  ear: '<path d="M7 9a5 5 0 0110 0c0 3-3 4-3 7a3 3 0 01-5.5 1.6"/><path d="M10 9a2 2 0 014 0"/>',
  skip: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/>',
  heading: '<path d="M6 4v16M18 4v16M6 12h12"/>',
  table: '<rect x="4" y="5" width="16" height="14" rx="1"/><path d="M4 10h16M10 10v9"/>',
};
const icon = (name, label) => `<svg class="icon" viewBox="0 0 24 24" ${label ? `role="img" aria-label="${esc(label)}"` : 'aria-hidden="true"'}>${ICON_PATHS[name] || ''}</svg>`;

async function requestJson(url, options) {
  let r;
  try { r = await fetch(url, options); }
  catch (e) { if (e.name === 'AbortError') throw e; throw new Error('Koneksi ke SIMAK terputus. Periksa server lalu coba lagi.'); }
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    const e = new Error(typeof data?.detail === 'string' ? data.detail : `Permintaan gagal (${r.status}). Coba lagi.`);
    e.status = r.status; throw e;
  }
  if (data === null) throw new Error('Respons server tidak dapat dibaca. Coba periksa status lagi.');
  return data;
}
function rememberJob(jid) {
  try { jid ? sessionStorage.setItem('simak-job', jid) : sessionStorage.removeItem('simak-job'); } catch (e) {}
  document.querySelectorAll('[data-job-link]').forEach(a => { a.href = a.dataset.jobLink + (jid ? '?job=' + encodeURIComponent(jid) : ''); });
}
function currentJob() { try { return sessionStorage.getItem('simak-job'); } catch (e) { return null; } }

// Nama fungsi dipertahankan untuk pemanggil yang sudah ada.
function renderRail(current) {
  const items = [['index.html','Remediasi','doc'],['uld.html','ULD','hold'],['pendengar.html','Pendengar','mic'],['evaluasi.html','Bukti','chart']];
  const links = items.map(([h,l,i])=>`<a href="${h}" ${h==='index.html'?`data-job-link="${h}"`:''} ${h===current?'aria-current="page"':''}>${icon(i)}${l}</a>`).join('');
  document.querySelector('.rail').innerHTML=`<a class="wordmark" href="index.html?jelajah=1#opening" aria-label="SIMAK · kenali aplikasi"><b>SIMAK<span class="brand-dot" aria-hidden="true">.</span></b></a>
    <nav class="nav" aria-label="Navigasi utama">${links}<a class="nav-start" href="uld.html">Mulai dari PDF</a></nav>
    <button class="nav-toggle" id="nav-toggle" type="button" aria-expanded="false" aria-controls="site-menu">Menu ${icon('layers')}</button>
    <div class="nav-menu" id="site-menu" hidden role="dialog" aria-modal="true" aria-label="Menu SIMAK" data-lenis-prevent><div class="nav-menu-head"><b class="wordmark">SIMAK.</b><button class="nav-close" id="nav-close" type="button">Tutup ${icon('cross')}</button></div><ul>
      <li><a class="m-surface-8 nav-menu-work" href="index.html" data-job-link="index.html">Remediasi</a></li><li><a class="m-surface-2" href="uld.html">Ruang ULD</a></li><li><a class="m-surface-7" href="pendengar.html">Pendengar</a></li><li><a class="m-surface-4" href="evaluasi.html">Bukti</a></li><li><a class="m-surface-3" href="uld.html">Mulai dari PDF</a></li><li><a class="m-surface" href="index.html?jelajah=1#opening">Kenali SIMAK</a></li>
    </ul></div>`;
  rememberJob(currentJob());
}

const STATUS = {
  terbit_otomatis: ['pass', 'Terbit otomatis', 'check'],
  antrean: ['hold', 'Ditahan · menunggu ULD', 'hold'],
  disetujui: ['pass', 'Disetujui ULD', 'check'],
  diubah: ['pass', 'Diubah ULD', 'check'],
  ditolak: ['fail', 'Ditolak ULD', 'cross'],
  dekoratif: ['pending', 'Dekoratif', 'doc'],
};
const statusStamp = s => {
  const [k, t, i] = STATUS[s] || ['pending', s, 'doc'];
  return `<span class="stamp ${k === 'pass' ? '' : k}">${icon(i)}${t}</span>`;
};

const CHECKS = {cF: 'klaim setia pada tabel', 'cδ': 'dua ekstraksi konsisten', cA: 'nilai dalam rentang sumbu', cL: 'nilai tercetak pada grafik'};
const nowStamp = () => new Date().toLocaleTimeString('id-ID', {hour: '2-digit', minute: '2-digit'});
const checkStamps = (checks, when) => Object.entries(checks || {}).map(([k, v], i) =>
  `<span class="stamp ${v ? '' : 'fail'}" style="--i:${i}" title="${esc(CHECKS[k] || k)}">${icon(v ? 'check' : 'cross')}${esc(k)} ${v ? 'lulus' : 'gagal'}${when ? ` <span class="when">${esc(when)}</span>` : ''}<span class="sr"> · ${esc(CHECKS[k] || k)}</span></span>`).join('');
const checkLegend = () => Object.entries(CHECKS).map(([k, v]) => `<b class="num">${k}</b> ${v}`).join(' · ');

function pressSlip(slip) {
  if (!slip || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  slip.animate?.([{backgroundColor: '#fff0c2'}, {backgroundColor: 'transparent'}], {duration: 220});
}

const MEASURE = {nilai: 'nilai', maksimum: 'maksimum', minimum: 'minimum', selisih: 'selisih', rerata: 'rerata',
  total: 'total', perubahan_terfit: 'perubahan terfit', perubahan: 'perubahan', tren: 'tren'};

function segHtml(seg, detail) {
  return seg.map(s => {
    if (s.claim === undefined || s.claim === null) return esc(s.text);
    const d = detail && detail[s.claim];
    const bad = d && !d.ok;
    const title = d ? `Klaim (${d.e}, ${MEASURE[d.m] || d.m}, ${fmtId(d.v)}): ${d.ok ? 'cocok dengan tabel data' : 'tidak cocok, tabel memuat ' + (d.ref === null ? 'tidak ada' : fmtId(d.ref))}` : '';
    return `<span class="cl${bad ? ' bad' : ''}${s.injected ? ' inj' : ''}" tabindex="0" role="button" data-claim="${s.claim}" data-e="${esc(d ? d.e : '')}" title="${esc(title)}" aria-label="${esc(s.text + '. ' + title)}">${esc(s.text)}</span>`;
  }).join('');
}

function t1t2(e) {
  const m2 = Object.fromEntries((e.T2 || []).map(r => [norm(r.kategori), r.nilai]));
  return `<table><caption>Ekstraksi ganda, δ = ${Number(e.delta).toFixed(3)}</caption><thead><tr><th scope="col">Kategori</th><th scope="col" class="n">T1</th><th scope="col" class="n">T2</th><th scope="col" class="n">|T1 − T2|</th></tr></thead><tbody>` +
    e.T1.map(r => {
      const v2 = m2[norm(r.kategori)];
      const dd = v2 === undefined ? null : Math.abs(r.nilai - v2);
      return `<tr data-row="${esc(norm(r.kategori))}"><th scope="row">${esc(r.kategori)}</th><td class="n">${fmtId(r.nilai)}</td><td class="n">${v2 === undefined ? '–' : fmtId(v2)}</td><td class="n ${dd ? 'd' : ''}">${dd === null ? '–' : fmtId(dd)}</td></tr>`;
    }).join('') + '</tbody></table>';
}

function bindClaims(root) {
  root.querySelectorAll('.cl').forEach(el => {
    const on = () => {
      root.querySelectorAll('.on').forEach(x => x.classList.remove('on'));
      el.classList.add('on');
      el.dataset.e.split('|').forEach(k => root.querySelectorAll(`tr[data-row="${CSS.escape(norm(k))}"]`).forEach(tr => tr.classList.add('on')));
    };
    el.addEventListener('click', on);
    el.addEventListener('focus', on);
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); on(); } });
  });
}

function announce(msg) {
  let r = document.getElementById('sr-live');
  if (!r) { r = document.createElement('div'); r.id = 'sr-live'; r.setAttribute('aria-live', 'polite'); r.className = 'sr'; document.body.appendChild(r); }
  r.textContent = '';
  setTimeout(() => { r.textContent = msg; }, 30);
}

// ---------------------------------------------------------------- suara (mode dengar)
const Voice = new SimakSpeech();
Voice.prefetch = () => {}; // ElevenLabs hanya dibuat saat pengguna menekan Putar.
Voice.controls = function(el, onchange) {
  el.innerHTML = `<label class="lbl" for="v-suara">Suara</label><select id="v-suara" disabled><option value="peramban">Menyiapkan suara…</option></select>
    <label class="lbl" for="v-cepat">Kecepatan</label><select id="v-cepat">${[-20,-10,0,10,20].map(v=>`<option value="${v}" ${v===this.pref.kecepatan?'selected':''}>${v===0?'Normal':(v>0?'+':'')+v+'%'}</option>`).join('')}</select>
    <button type="button" id="v-coba" disabled>${icon('play')}Coba suara</button><span class="voice-note small" id="voice-note" role="status"></span>`;
  const sel=el.querySelector('#v-suara'), note=el.querySelector('#voice-note'), test=el.querySelector('#v-coba');
  const describe=()=>{note.textContent=this.pref.suara==='eleven'?'ElevenLabs · teks yang diputar dikirim ke layanan suara.':'Suara peramban · bahasa Indonesia mengikuti perangkat.';};
  const update=()=>{this.stop();onchange?.();this.pref.suara=sel.value;this.pref.kecepatan=+el.querySelector('#v-cepat').value;this.save();describe();};
  sel.onchange=el.querySelector('#v-cepat').onchange=update;
  this.ready.then(()=>{
    sel.innerHTML='<option value="peramban">Peramban (id-ID)</option>'+(this.available?'<option value="eleven">ElevenLabs · suara pilihan</option>':'');
    sel.value=this.pref.suara;sel.disabled=false;test.disabled=false;describe();
  });
  test.onclick=()=>{onchange?.();note.textContent='Menyiapkan audio…';this.speak('Halo, saya membacakan materi kuliah untuk Anda.',describe,e=>{note.textContent=e.message;},()=>{note.textContent='Memutar contoh suara…';});};
};

window.addEventListener('pagehide', () => Voice.stop());
