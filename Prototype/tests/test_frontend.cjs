// Regression tests execute the page's actual scripts with a minimal DOM and controlled network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/ui_states.json'), 'utf8'));
const response = data => ({ok: true, json: async () => data});
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return {promise, resolve}; };

async function harness(page) {
  const elements = new Map();
  function element(key) {
    if (elements.has(key)) return elements.get(key);
    const e = {value: '', textContent: '', disabled: false, files: [], options: [], children: [], dataset: {}, htmlWrites: 0,
      classList: {add() {}, remove() {}, toggle() {}}, focus() {}, setAttribute() {}, addEventListener() {},
      querySelector: s => element(key + ' ' + s), querySelectorAll(selector) { return selector === 'button' && this.html?.includes('data-a=') ? ['play','prev','next','img'].map(k => element(key + ' [data-a="' + k + '"]')) : []; }, scrollIntoView() {}};
    Object.defineProperty(e, 'innerHTML', {set(v) { this.htmlWrites++; this.html = v; }, get() { return this.html || ''; }});
    elements.set(key, e);
    return e;
  }
  const context = vm.createContext({
    console, AbortController, URLSearchParams, setTimeout, clearTimeout,
    fetch: async url => response(url === '/api/sampel' ? [] : {}),
    window: {addEventListener() {}}, document: {querySelector: element, querySelectorAll: () => [], getElementById: element},
    localStorage: {getItem: () => null, setItem() {}}, sessionStorage: {getItem: () => null, setItem() {}, removeItem() {}},
    location: {search: ''}, history: {replaceState() {}}, matchMedia: () => ({matches: true}), confirm: () => true,
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'web/speech.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(root, 'web/common.js'), 'utf8'), context);
  const html = fs.readFileSync(path.join(root, 'web', page), 'utf8');
  for (const [, script] of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
    if (script.trim()) vm.runInContext(script, context);
  }
  await new Promise(setImmediate);
  return {context, element, run: s => vm.runInContext(s, context)};
}

(async () => {
  {
    const h = await harness('index.html');
    const a = deferred();
    const bState = {...fixture.completed, title: 'B wins'};
    h.context.fetch = async url => url.endsWith('/A') ? a.promise : response({tahap: 'selesai', state: bState});
    h.run("JID='A'; TOKEN=0;");
    const oldPoll = h.run("poll('A',0)");
    h.run("JID='B'; TOKEN=1;");
    await h.run("poll('B',1)");
    a.resolve(response({tahap: 'selesai', state: {...fixture.completed, title: 'stale A'}}));
    await oldPoll;
    assert.equal(h.run('STATE.title'), 'B wins', 'late poll must not overwrite the active job');
  }
  {
    const h = await harness('index.html');
    const pending = deferred(); let starts = 0;
    h.context.fetch = async url => {
      if (url === '/create') { starts++; return pending.promise; }
      return response({tahap: 'selesai', state: fixture.completed});
    };
    const first = h.run("start('/create',{method:'POST'})");
    await h.run("start('/create',{method:'POST'})");
    assert.equal(starts, 1, 'busy must be locked before starting the network request');
    pending.resolve(response({id: 'fixture'}));
    await first;
    await new Promise(setImmediate);
    assert.equal(h.run('BUSY'), false);
  }
  {
    const h = await harness('index.html');
    h.context.fetch = async () => { throw new TypeError('offline'); };
    await h.run("start('/create',{method:'POST'})");
    assert.equal(h.run('BUSY'), false);
    assert.equal(h.element('#up-btn').disabled, false);
    assert.match(h.element('#prog').textContent, /Koneksi/);
  }
  {
    // R = masuk antrean setelah gerbang / gambar nondekoratif; keputusan ULD tidak mengubahnya.
    const h = await harness('index.html');
    const gate = {e0: 'terbit_otomatis', e1: 'antrean', e2: 'antrean', e3: 'antrean', e4: 'antrean', e5: 'dekoratif'};
    const state = JSON.parse(JSON.stringify(fixture.completed));
    state.elements.forEach(e => { if (gate[e.id]) e.status_gerbang = gate[e.id]; });
    h.context.STATE_IN = state;
    h.run('STATE = STATE_IN; render();');
    assert.match(h.element('#tally').innerHTML, /<dt>80%<\/dt><dd>beban tinjauan R · 4\/5 masuk antrean/);
    h.run("STATE.elements.find(e => e.id === 'e1').status = 'dekoratif'; render();");
    assert.match(h.element('#tally').innerHTML, /<dt>80%<\/dt>/, 'ULD decisions must not change R');
    const legacy = JSON.parse(JSON.stringify(fixture.completed));
    legacy.elements.forEach(e => { if (['e2', 'e3', 'e4'].includes(e.id)) e.log = [{aksi: 'setujui'}]; });
    h.context.STATE_IN = legacy;
    h.run('STATE = STATE_IN; render();');
    assert.match(h.element('#tally').innerHTML, /beban tinjauan R · 4\/5 masuk antrean/, 'legacy sessions count ULD-decided elements as queued');
  }
  console.log('PASS: stale polling, duplicate start, offline recovery, review burden R');
})().catch(e => { console.error(e); process.exitCode = 1; });
