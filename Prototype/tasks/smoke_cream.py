"""Smoke sintetis dari cache, tanpa panggilan VLM live atau kalibrasi ulang."""
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
import app
from simak import pdfa11y, pipeline, vlm

vlm.KEYS = []
client = TestClient(app.app)
result = {'date': '2026-10-23', 'vlm_live': False}
result['pages'] = {p: client.get(p).status_code for p in ['/', '/uld.html', '/pendengar.html', '/evaluasi.html']}
r = client.post('/api/sampel/materi_03.pdf')
r.raise_for_status()
jid = r.json()['id']
result['job'] = jid
for _ in range(180):
    j = client.get('/api/pekerjaan/' + jid).json()
    if j.get('tahap') in ('selesai', 'gagal'):
        break
    time.sleep(1)
result['stage'] = j.get('tahap')
if j.get('tahap') != 'selesai':
    raise RuntimeError('Smoke PDF tidak selesai: ' + str(j))
st = j['state']
result['statuses_before_review'] = dict(Counter(e['status'] for e in st['elements'] if e['kind'] == 'image'))
result['report'] = st['report']
result['outputs'] = {p: client.get(f'/keluaran/{jid}/{p}').status_code for p in ['simak.pdf', 'simak.html', 'asli.pdf']}
result['review'] = {}
pending = [e for e in st['elements'] if e.get('status') == 'antrean']
if pending:
    e = pending[0]
    text = 'Deskripsi uji transaksi untuk elemen sintetis ' + e['id'] + '.'
    r = client.post(f'/api/tinjau/{jid}/{e["id"]}', json={'aksi': 'ubah', 'alt': text})
    result['review']['http'] = r.status_code
    state = client.get('/api/pekerjaan/' + jid).json()['state']
    html = client.get(f'/keluaran/{jid}/simak.html').text
    pdf = pipeline.output_path(app.WORK / ('job_' + jid), 'simak.pdf')
    result['review']['state'] = next(e['status'] for e in state['elements'] if e['id'] == pending[0]['id'])
    result['review']['html_has_new_text'] = text in html
    result['review']['pdf_has_new_text'] = any(text in str(a) for a in pdfa11y.figure_alts(pdf))
    result['review']['version'] = state.get('output_version')
result['source_sizes'] = {str(p.relative_to(ROOT)): p.stat().st_size for p in (ROOT/'web').rglob('*') if p.is_file()}
out = ROOT / 'tasks/evidence/cream/smoke.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'source_sizes'}, ensure_ascii=True, indent=2))
assert all(v == 200 for v in result['pages'].values())
assert result['report']['D']['verapdf']['compliant']
assert result['review'].get('pdf_has_new_text') and result['review'].get('html_has_new_text')
