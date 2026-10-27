"""Perakitan awal adaptasi Sill; edit HTML hasil untuk perubahan berikutnya."""
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
evidence=ROOT/'tasks/evidence/fluid'
evidence.mkdir(parents=True,exist_ok=True)
backup=evidence/'before-fluid.zip'
if not backup.exists():
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
        for p in [*(ROOT/'web').glob('*.html'),*(ROOT/'web').glob('*.css'),*(ROOT/'web').glob('*.js'),ROOT/'simak/output.py']:
            z.write(p,p.relative_to(ROOT))

curl='''<svg class="m-curl {cls}" viewBox="0 0 200 300" aria-hidden="true" {motion}><path pathLength="1" d="M100 296 C58 236 38 158 90 110 C140 64 200 92 190 140 C181 184 121 186 115 146 C110 116 150 104 158 130"/></svg>'''
def image(name,alt='',extra=''):
    return f'<img src="assets/{name}.svg" alt="{alt}" width="900" height="1100" {extra}>'

windows=''
labels=['Judul','Paragraf','Grafik','Tabel','Diagram','Rumus','Data','Deskripsi','Verifikasi','Tinjauan','Audio','HTML']
for i,label in enumerate(labels):
    surface=['','-4','-3','-8','-6','-7','-5','-2','-7','','-5','-8'][i]
    if i%2:
        windows+=f'<li class="op-win m-surface{surface}"><div class="m-photo op-win__photo">{image(["reading","evidence","listening"][i%3])}</div><span class="m-text-4 op-win__label">{label}</span></li>'
    else:
        windows+=f'<li class="op-win op-win--plain m-surface{surface}"><span class="m-text-4 op-win__label">{label}</span></li>'

home=f'''
<section id="opening" data-8b-section="opening" aria-labelledby="opening-title">
 <div class="op-s1"><div class="op-grid">
  <div class="op-cell op-a"><div class="op-panel m-surface"><h1 id="opening-title" class="m-text-2 op-title">Materi kuliah,<br>untuk semua.</h1></div></div>
  <div class="op-cell op-b"><div class="op-panel m-surface-4"><div class="m-photo op-photo">{image('material','Ilustrasi materi kuliah, grafik, dan perangkat dengar.', 'fetchpriority="high"')}</div><p class="m-text-4 op-ledge">Baca. Dengar. Telusuri.</p></div></div>
  <div class="op-cell op-c"><div class="op-panel m-surface-3"><p class="m-text-7">Ubah PDF menjadi materi yang lebih mudah dibaca, didengar, dan ditelusuri.</p></div></div>
  <div class="op-cell op-d"><div class="op-panel m-surface-4"><p class="m-text-4">Satu PDF.<br>Lebih banyak cara belajar.</p>{curl.format(cls='op-curl',motion='')}<div class="op-actions"><a class="m-btn" href="#contact"><span class="m-btn__label">Mulai dari PDF</span></a><a class="m-link" href="#rooms">Kenali SIMAK</a></div></div></div>
  <div class="op-cell op-e"><div class="op-panel m-surface-2"><p class="m-text-4">Dari visual<br>ke suara.</p><p class="m-text">Dengarkan apa yang semula hanya terlihat.</p><a class="m-link" href="pendengar.html">Coba dengarkan</a></div></div>
 </div></div>
 <div class="op-s2"><div class="op-ink" aria-hidden="true"><svg class="op-ink__hill" viewBox="0 0 1000 1000" preserveAspectRatio="none"><path d="M0 1000 V200 C70 200 150 26 370 12 C560 2 640 150 810 168 C900 177 960 180 1000 180 V1000 Z"/></svg>{curl.format(cls='op-ink__curl',motion='')}</div>
 <div class="op-s2__text"><h2 class="m-text-3">Setiap bagian punya arti.</h2><p class="m-text-7">Dari judul hingga grafik. Materi disusun untuk dibaca, dipahami, dan ditinjau dengan jelas.</p><a class="m-link" href="#rooms">Temukan cara mengaksesnya</a></div>
 <ul class="op-house" aria-label="Bagian materi dan hasil SIMAK">{windows}</ul></div>
</section>
<section id="rooms" data-8b-section="rooms" aria-labelledby="rooms-title"><div class="rm-grid">
 <div class="rm-head m-surface-6"><h2 id="rooms-title" class="m-text-3" data-8b-motion="rise">Baca. Dengar.<br>Pahami.</h2><p class="m-text">Satu materi, beberapa cara untuk menjangkaunya. Pilih yang paling nyaman bagi Anda.</p></div>
 <article class="rm-room rm-ledge m-surface-7"><div class="m-photo">{image('reading')}</div><div class="rm-body"><h3 class="m-text-6 rm-name">Baca</h3><p class="m-text">Struktur lebih jelas. Deskripsi dan tabel hadir bersama isi materi.</p><a class="m-link" href="#contact">Buka ruang remediasi</a></div></article>
 <article class="rm-room rm-tower m-surface-3"><div class="m-photo">{image('listening')}</div><div class="rm-body"><h3 class="m-text-6 rm-name" style="--len:6">Dengar</h3><p class="m-text">Ikuti materi lewat suara. Atur kecepatan, pilih bagian, lanjutkan belajar.</p><a class="m-link" href="pendengar.html">Dengarkan materi</a></div></article>
 <article class="rm-room rm-burrow m-surface-2"><div class="m-photo">{image('evidence')}</div><div class="rm-body"><h3 class="m-text-6 rm-name">Telusuri</h3><p class="m-text">Lihat sumber angka dan alasan di balik setiap keputusan.</p><a class="m-link" href="evaluasi.html">Lihat bukti</a></div></article>
 <div class="rm-every m-surface-8"><h3 class="m-text-6">Tetap dalam kendali.</h3><ul class="m-text"><li>Status yang terbaca</li><li>Data yang bisa diperiksa</li><li>Tinjauan manusia</li><li>Hasil PDF dan HTML</li></ul></div>
</div></section>
<section id="letters" data-8b-section="letters" aria-labelledby="letters-title"><div class="lt-grid"><div class="lt-intro"><h2 id="letters-title" class="m-text-3" data-8b-motion="rise">Angka bercerita.<br>Konteks menyertai.</h2><p class="m-text-7">Deskripsi membantu memahami grafik. Sumber data membantu memeriksanya.</p>{curl.format(cls='',motion='data-8b-motion="curl"')}</div><div class="lt-list">
 <article class="lt-letter m-surface-4"><div class="m-photo lt-photo" data-8b-motion="peek">{image('evidence')}</div><div class="lt-body"><p class="m-text-4">Contoh grafik sintetis</p><p class="m-text-5">“Juli mencatat 1.452 kunjungan, tertinggi pada grafik.”</p><p class="m-text lt-sign">Angka disusun dari tabel, bukan tebakan kalimat.</p><a class="m-link" href="evaluasi.html">Periksa buktinya</a></div></article>
 <article class="lt-letter m-surface-8"><div class="m-photo lt-photo" data-8b-motion="peek">{image('reading')}</div><div class="lt-body"><h3 class="m-text-6">Bukan sekadar teks.</h3><p class="m-text">Judul, tabel, dan deskripsi membentuk urutan baca yang lebih jelas.</p><a class="m-link" href="#contact">Coba materi contoh</a></div></article>
 <article class="lt-letter m-surface-7"><div class="m-photo lt-photo" data-8b-motion="peek">{image('listening')}</div><div class="lt-body"><h3 class="m-text-6">Bukan sekadar suara.</h3><p class="m-text">Deskripsi yang belum terverifikasi tetap ditandai untuk ditinjau.</p><a class="m-link" href="pendengar.html">Coba pendengar</a></div></article>
</div></div></section>
<section id="day" data-8b-section="day" aria-labelledby="day-title"><div class="dy-stage"><div class="dy-head"><h2 id="day-title" class="m-text-3">Dari berkas<br>ke akses.</h2><p class="m-text">Enam tahap yang menjaga materi tetap terstruktur dan keputusan tetap terlihat.</p></div><div class="dy-sky" aria-hidden="true"><div class="dy-disc"></div></div><div class="dy-rail"><ol class="dy-track">'''

steps=[('Pilih PDF','Mulai dari materi kuliah Anda.','-5'),('Susun struktur','Judul, paragraf, tabel, dan gambar dikenali.','-3'),('Baca data','Grafik diekstraksi melalui dua pembacaan.',''),('Periksa klaim','Angka dan konsistensinya diperiksa.','-7'),('Tinjau elemen','Yang belum pasti masuk antrean ULD.','-6'),('Buka hasil','PDF bertag dan HTML siap diakses.','-2')]
for i,(title,text,surface) in enumerate(steps):
    home+=f'<li class="dy-hour m-surface{surface}"><p class="dy-time">{i+1:02}</p><h3 class="m-text-6">{title}</h3><p class="m-text">{text}</p><div class="m-photo dy-photo">{image("step-"+str(i+1))}</div></li>'
home+='</ol></div></div></section>'
home+='''<section id="sitters" data-8b-section="sitters" aria-labelledby="sitters-title"><div class="st-head"><h2 id="sitters-title" class="m-text-3" data-8b-motion="rise">Empat pemeriksaan.<br>Satu keputusan.</h2><p class="m-text">Deskripsi grafik terbit otomatis setelah seluruh pemeriksaan lolos.</p></div><ul class="st-list">'''
for i,(term,title,text,surface) in enumerate([('cF','Klaim setia','Klaim sesuai dengan tabel data.','-7'),('cδ','Data konsisten','Dua pembacaan saling mendukung.',''),('cA','Sumbu sesuai','Nilai berada dalam rentang sumbu.','-4'),('cL','Nilai tercetak','Angka tersedia pada grafik.','-3')]):
    home+=f'<li class="st-person"><div class="m-surface{surface}"><div class="m-photo st-photo" data-8b-motion="peek">{image("step-"+str([3,2,1,4][i]))}<span class="gate-art" aria-hidden="true">{term}</span></div><div class="st-ledge"><h3 class="m-text-6">{title}</h3><p class="m-text">{text}</p></div></div></li>'
home+='</ul></section>'
home+='''<section id="courtyard" data-8b-section="courtyard" aria-labelledby="courtyard-title"><div class="cy-grid"><div class="cy-window">'''
for i in range(6):
    c,r=i%3,i//3;mc,mr=i%2,i//2
    home+=f'<div class="cy-pane" style="--c:{c};--r:{r};--mc:{mc};--mr:{mr}" '+('aria-hidden="true"' if i else '')+'>'+image('evidence','Ilustrasi grafik, tabel data, dan pemeriksaan.' if not i else '')+'<span class="cy-tint"></span></div>'
home+=f'''</div><div class="cy-text m-surface-7"><h2 id="courtyard-title" class="m-text-3">Data tetap terlihat.</h2><p class="m-text">Deskripsi tidak berdiri sendiri. Tabel dan status ikut menyertai.</p><ul class="m-text"><li>Lihat nilai sumber.</li><li>Pahami hasil pemeriksaan.</li><li>Tinjau bagian yang tertahan.</li></ul><a class="m-link" href="evaluasi.html">Lihat cara kerjanya</a></div><figure class="cy-birds m-surface-8"><div class="m-photo">{image('listening')}</div><figcaption class="m-text"><p>Lihat angkanya. Dengarkan maknanya.</p></figcaption></figure></div></section>
<section id="visit" data-8b-section="visit" aria-labelledby="visit-title"><div class="vs-grid"><div class="vs-head"><h2 id="visit-title" class="m-text-3" data-8b-motion="rise">Mulai sederhana.<br>Lanjut lebih jauh.</h2><p class="m-text-7">Anda menyiapkan materi. SIMAK membantu membuka aksesnya.</p>{curl.format(cls='vs-curl',motion='data-8b-motion="curl"')}</div>'''
for i,(title,text,surface) in enumerate([('Pilih materi','Unggah PDF atau gunakan contoh yang tersedia.','-4'),('Proses dokumen','Ikuti progres struktur dan analisis gambar.',''),('Tinjau hasil','Periksa dan setujui deskripsi yang memerlukan perhatian.','-7'),('Buka akses','Unduh PDF atau buka HTML dengan mode dengar.','-3')]):
    home+=f'<article class="vs-step m-surface{surface}">'+(f'<div class="m-photo vs-photo">{image("reading")}</div>' if i==3 else '')+f'<p class="vs-num">{i+1}</p><h3 class="m-text-6">{title}</h3><p class="m-text">{text}</p></article>'
home+='''</div></section><section id="quiet" data-8b-section="quiet" aria-labelledby="quiet-title"><div class="qt-head"><h2 id="quiet-title" class="m-text-3">Akses yang jelas.<br>Proses yang terbuka.</h2><p class="m-text">Kepercayaan dibangun dari keputusan yang dapat diperiksa.</p></div><ul class="qt-rules">'''
for title,text,surface in [('Jelas.','Hasil otomatis dan tinjauan manusia memiliki penanda berbeda.','-4'),('Data.','Statistik dihitung dari tabel dan diperiksa sebelum terbit.','-7'),('ULD.','Elemen yang belum terverifikasi menunggu tinjauan.','-3'),('Bukti.','Cakupan dan keterbatasan hasil dilaporkan bersama.','-8')]:
    home+=f'<li class="qt-rule m-surface{surface}"><p class="m-text-8 qt-word">{title}</p><p class="m-text">{text}</p></li>'
home+='''</ul></section><section id="faq" data-8b-section="faq" aria-labelledby="faq-title"><div class="fq-grid"><div class="fq-head m-surface-4"><h2 id="faq-title" class="m-text-3" data-8b-motion="rise">Sebelum<br>memulai.</h2><a class="m-link" href="#contact">Buka ruang remediasi</a></div><div class="fq-list">'''
faqs=[('PDF apa yang dapat digunakan?','PDF berlapis teks hingga 20 MiB dan 200 halaman. PDF hasil pindai dan PowerPoint belum didukung langsung.'),('Apakah semua gambar diproses otomatis?','Grafik yang lolos pemeriksaan dapat terbit otomatis. Rumus, diagram, dan elemen yang belum terverifikasi memerlukan tinjauan ULD.'),('Apakah perlu koneksi internet?','Contoh yang sudah tersimpan di cache dapat diproses tanpa VLM live. ElevenLabs memerlukan internet; suara peramban mengikuti perangkat.'),('Di mana dokumen disimpan?','Dokumen dan keputusan tersimpan lokal selama sesi. Gunakan Hapus sesi untuk menghapusnya.'),('Sejauh mana hasilnya sudah diuji?','Evaluasi sintetis dan dokumen nyata terbatas tersedia pada halaman Bukti. Simulasi Dengar bukan rekaman NVDA atau pengujian pengalaman mahasiswa.')]
for i,(q,a) in enumerate(faqs):
    home+=f'<details class="fq-item m-surface{["-7","-8","-5","-3","-4"][i]}"><summary class="m-text-6">{q}</summary><div class="fq-a m-text">{a}</div></details>'
home+='''</div></div></section>
<section id="contact" data-8b-section="contact" aria-labelledby="h-pilih"><div class="ct-grid">
 <div class="ct-side ct-call m-surface-7"><p class="m-text-8 ct-label" style="--len:4">Baca</p><div class="ct-detail"><p class="m-text">PDF bertag.<br>HTML aksesibel.</p><a class="m-link" href="#rooms">Kenali hasilnya</a></div></div>
 <div class="ct-side ct-visit m-surface"><p class="m-text-6">Materi Anda.<br>Awal akses yang lebih baik.</p><p class="m-text">Pilih PDF, lalu mulai.</p></div>
 <div class="ct-form m-surface-4"><form id="up" class="upload" aria-labelledby="h-pilih"><h2 id="h-pilih" class="m-text-3">Buka akses<br>materi Anda.</h2><p class="m-text">PDF berlapis teks, hingga 20 MiB dan 200 halaman.</p><input type="file" id="file" accept="application/pdf" class="sr" aria-describedby="file-help"><label for="file" class="btn file-pick" id="file-lbl">Pilih berkas PDF</label><button class="btn-primary" id="up-btn" type="submit">Proses PDF</button><p class="small" id="file-help">Dokumen disimpan lokal. Hapus sesi untuk menghapus dokumen dan keputusan.</p></form></div>
 <section class="ct-side ct-hours m-surface-3 samples" aria-labelledby="h-samples"><div><h3 id="h-samples" class="m-text-6">Coba dulu, tanpa unggah.</h3><p class="m-text">Pilih salah satu materi sintetis.</p></div><div id="sampel"><p>Memuat materi contoh…</p></div><button id="samples-retry" class="hide">Muat ulang contoh</button></section>
 <div class="ct-side ct-write m-surface-8"><p class="m-text-8 ct-label" style="--len:6">Dengar</p><div class="ct-detail"><p class="m-text">Pilih bagian.<br>Atur kecepatan.</p><a class="m-link" href="pendengar.html">Coba mode dengar</a></div></div>
</div></section>
'''

footer='''<footer id="footer" class="site-footer" data-8b-section="footer"><div class="ft-grid"><nav class="ft-nav" aria-label="Jelajahi SIMAK"><ul><li><a class="m-link" href="index.html#opening">Kenali SIMAK</a></li><li><a class="m-link" href="pendengar.html">Dengarkan materi</a></li><li><a class="m-link" href="uld.html">Ruang ULD</a></li><li><a class="m-link" href="evaluasi.html">Lihat bukti</a></li></ul></nav><div class="ft-contact"><p class="m-text-6">Materi kuliah,<br>untuk semua.</p><a class="m-link" href="index.html#contact">Mulai dari PDF</a></div><div class="ft-note"><p class="m-text">SIMAK oleh tim IRIS.<br>Universitas Airlangga.</p><p class="m-text-4">Prototipe ICC 2026</p><p class="credit">Desain mengacu pada Sill oleh <a href="https://8b.com/templates/sill/" target="_blank" rel="noopener">8B</a>.</p></div></div><div class="ft-mark" aria-hidden="true"><p class="m-text-2 ft-word" style="--len:6">SIMAK.</p></div></footer>'''

p=ROOT/'web/index.html'
s=p.read_text(encoding='utf-8')
a=s.index('<div class="ingest" id="input-stage">');b=s.index('<div class="progress hide"',a)
s=s[:a]+'<div class="brand-site" id="input-stage">'+home+'</div>\n'+s[b:]
s=re.sub(r'<footer class="footer">[\s\S]*?</footer>',footer,s,count=1)
p.write_text(s,encoding='utf-8')

template=(ROOT/'reference/sill/index.html').read_text(encoding='utf-8')
parts=[]
for attrs,css in re.findall(r'<style([^>]*)>([\s\S]*?)</style>',template):
    part=re.search(r'data-8b-part="([^"]+)"',attrs)
    if not part:continue
    name=part[1]
    if name=='system' or name.startswith(('section:','scene-style:')) and name!='section:nav':
        css=re.sub(r'^\s*@layer\s+\w+\s*\{','',css)
        css=re.sub(r'\}\s*$','',css)
        parts.append('/* Sill: '+name+' */\n'+css)
(ROOT/'web/sill.css').write_text('/* Adaptation of Sill by 8B. MIT notice: third_party/sill/LICENSE. */\n'+'\n'.join(parts),encoding='utf-8')

scenes=[]
for attrs,js in re.findall(r'<script([^>]*)>([\s\S]*?)</script>',template):
    part=re.search(r'data-8b-part="([^"]+)"',attrs)
    if part and (part[1]=='motion' or part[1].startswith('scene:')):
        scenes.append('// Sill: '+part[1]+'\n'+js)
(ROOT/'web/sill-scenes.js').write_text('/* Adapted from Sill by 8B. MIT. See third_party/sill/LICENSE. */\nfunction buildSillScenes(){\n'+'\n'.join(scenes)+'\n}\n',encoding='utf-8')
for p in (ROOT/'web').glob('*.html'):
    s=p.read_text(encoding='utf-8')
    if p.name!='index.html':s=re.sub(r'<footer class="footer">[\s\S]*?</footer>',footer,s,count=1)
    s=s.replace('cream-20261023','fluid-20261023')
    s=s.replace('</head>','<link rel="stylesheet" href="sill.css?v=fluid-20261023"><link rel="stylesheet" href="fluid.css?v=fluid-20261023"></head>')
    marker='<script>\n'
    at=s.index(marker,s.index('common.js?'))
    scripts=''.join(f'<script src="{name}?v=fluid-20261023"></script>' for name in ['vendor/gsap.min.js','vendor/ScrollTrigger.min.js','vendor/SplitText.min.js','vendor/lenis.min.js','sill-scenes.js','motion.js'])
    s=s[:at]+scripts+s[at:]
    p.write_text(s,encoding='utf-8')
print('Homepage, source motion scenes, footer, and local motion dependencies assembled.')
