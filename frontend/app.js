/**
 * Frank Türen AG – KI Angebotserstellung
 * Modern Frontend App
 */

const API = 'http://localhost:8000/api';

let state = {
  file: null,
  fileId: null,
  analysis: null,
  offer: null,
};

// ─────────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────────

function switchView(view, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById(`view-${view}`).classList.add('active');
  btn.classList.add('active');

  const titles = {
    offer:    ['Angebot erstellen', 'Ausschreibung hochladen und KI-Analyse starten'],
    products: ['Produktkatalog', 'FTAG-Produktmatrix durchsuchen'],
  };
  document.getElementById('topbar-title').textContent = titles[view][0];
  document.getElementById('topbar-sub').textContent   = titles[view][1];

  if (view === 'products') loadProducts();
}

// ─────────────────────────────────────────────
// FILE HANDLING
// ─────────────────────────────────────────────

function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function handleDragLeave() {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
}
function handleFileSelect(e) {
  if (e.target.files[0]) setFile(e.target.files[0]);
}

function setFile(file) {
  const allowed = ['.pdf','.xlsx','.xls','.docx','.doc','.txt'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) { showError(`Dateityp "${ext}" nicht unterstützt.`); return; }

  state.file = file;

  const icons = { '.pdf': '📕', '.xlsx': '📗', '.xls': '📗', '.docx': '📘', '.doc': '📘', '.txt': '📄' };
  document.getElementById('file-type-icon').textContent = icons[ext] || '📄';
  document.getElementById('file-name').textContent = file.name;
  document.getElementById('file-size').textContent = fmtSize(file.size);
  document.getElementById('file-preview').classList.remove('hidden');
  document.getElementById('btn-upload').disabled = false;
}

function clearFile() {
  state.file = null;
  document.getElementById('file-preview').classList.add('hidden');
  document.getElementById('file-input').value = '';
  document.getElementById('btn-upload').disabled = true;
}

function fmtSize(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b/1024).toFixed(1)} KB`;
  return `${(b/1048576).toFixed(1)} MB`;
}

// ─────────────────────────────────────────────
// MAIN WORKFLOW
// ─────────────────────────────────────────────

async function runFullWorkflow() {
  if (!state.file) return;

  showPanel('processing');
  setPill(2);
  setStep('upload', 'running', 'Datei wird hochgeladen...');
  document.getElementById('processing-subtitle').textContent = 'Datei wird hochgeladen...';

  try {
    // 1. Upload
    const form = new FormData();
    form.append('file', state.file);
    const up = await api('/upload', { method: 'POST', body: form });
    state.fileId = up.file_id;
    setStep('upload', 'done', `${up.text_length.toLocaleString('de-CH')} Zeichen extrahiert`);

    // 2. AI Analyse
    setStep('ai', 'running', 'Claude analysiert die Ausschreibung...');
    document.getElementById('processing-subtitle').textContent = 'Claude KI analysiert...';

    const analysis = await api('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: state.fileId }),
    });
    state.analysis = analysis;

    const pos = analysis.requirements?.positionen?.length || 0;
    setStep('ai', 'done', `${pos} Türposition${pos !== 1 ? 'en' : ''} erkannt`);

    // 3. Matching
    const s = analysis.matching?.summary || {};
    setStep('match', 'done',
      `${s.matched_count || 0} erfüllbar · ${s.partial_count || 0} teilweise · ${s.unmatched_count || 0} nicht erfüllbar`
    );
    document.getElementById('processing-subtitle').textContent = 'Angebot & Gap-Report werden erstellt...';

    // 4. Generate
    setStep('gen', 'running', 'Dokumente werden generiert...');
    const offer = await api('/offer/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requirements: analysis.requirements,
        matching: analysis.matching,
      }),
    });
    state.offer = offer;
    setStep('gen', 'done', offer.message);

    // Show results
    setPill(3);
    showResults(analysis, offer);

  } catch (err) {
    showError(err.message);
    setPill(1);
  }
}

// ─────────────────────────────────────────────
// RESULTS
// ─────────────────────────────────────────────

function showResults(analysis, offer) {
  showPanel('results');

  const req     = analysis.requirements || {};
  const match   = analysis.matching    || {};
  const summary = match.summary        || {};

  // Stat cards
  const statGrid = document.getElementById('stat-grid');
  const stats = [
    { num: summary.total_positions || 0,  label: 'Positionen gesamt', cls: 'blue' },
    { num: summary.matched_count   || 0,  label: 'Erfüllbar',          cls: 'green' },
    { num: summary.partial_count   || 0,  label: 'Teilweise',          cls: 'orange' },
    { num: summary.unmatched_count || 0,  label: 'Nicht erfüllbar',    cls: 'red' },
  ];
  statGrid.innerHTML = stats.map((s, i) => `
    <div class="stat-card ${s.cls}" style="animation-delay:${i * 80}ms">
      <div class="stat-num">${s.num}</div>
      <div class="stat-label">${s.label}</div>
    </div>
  `).join('');

  // Match rate bar
  const rate = summary.match_rate || 0;
  document.getElementById('match-rate-pct').textContent = `${rate}%`;
  document.getElementById('match-rate-sub').textContent =
    `Projekt: ${req.projekt || 'Ausschreibung'} · Auftraggeber: ${req.auftraggeber || 'n/a'}`;
  setTimeout(() => {
    document.getElementById('match-bar').style.width = `${rate}%`;
  }, 100);

  // Downloads
  const dlGrid = document.getElementById('download-grid');
  dlGrid.innerHTML = '';

  if (offer.has_offer && offer.offer_id) {
    dlGrid.innerHTML += `
      <div class="dl-group">
        <div class="dl-group-title">📄 Angebot</div>
        <div class="dl-buttons">
          <a href="${API}/offer/${offer.offer_id}/download?format=xlsx" class="dl-btn excel" download="FTAG_Angebot_${offer.offer_id}.xlsx">
            <span class="dl-icon">📗</span> Excel herunterladen
          </a>
          <a href="${API}/offer/${offer.offer_id}/download?format=docx" class="dl-btn word" download="FTAG_Angebot_${offer.offer_id}.docx">
            <span class="dl-icon">📘</span> Word herunterladen
          </a>
        </div>
      </div>
    `;
  }

  if (offer.has_gap_report && offer.report_id) {
    dlGrid.innerHTML += `
      <div class="dl-group">
        <div class="dl-group-title">⚠️ Gap-Report</div>
        <div class="dl-buttons">
          <a href="${API}/report/${offer.report_id}/download?format=xlsx" class="dl-btn orange-btn" download="FTAG_Gap_Report_${offer.report_id}.xlsx">
            <span class="dl-icon">📗</span> Excel herunterladen
          </a>
          <a href="${API}/report/${offer.report_id}/download?format=docx" class="dl-btn orange-word" download="FTAG_Gap_Report_${offer.report_id}.docx">
            <span class="dl-icon">📘</span> Word herunterladen
          </a>
        </div>
      </div>
    `;
  }

  if (!offer.has_offer && !offer.has_gap_report) {
    dlGrid.innerHTML = '<p style="color:var(--gray-400);font-size:.875rem;grid-column:1/-1;">Keine Dokumente erstellt.</p>';
  }

  // Positions
  const container = document.getElementById('positions-container');
  container.innerHTML = '';

  const sections = [
    { items: match.matched  || [], label: 'Erfüllbare Positionen',         cls: 'green',  icon: '✅' },
    { items: match.partial  || [], label: 'Teilweise erfüllbare Positionen', cls: 'orange', icon: '⚠️' },
    { items: match.unmatched|| [], label: 'Nicht erfüllbare Positionen',    cls: 'red',    icon: '❌' },
  ];

  sections.forEach(({ items, label, cls, icon }) => {
    if (!items.length) return;
    const tagCls = { green: 'tag-green', orange: 'tag-orange', red: 'tag-red' }[cls];

    const rows = items.map(item => {
      const pos = item.original_position || item;
      return `
        <tr>
          <td><strong>${esc(item.position || pos.position || '—')}</strong></td>
          <td>${esc(item.beschreibung || pos.beschreibung || '—')}</td>
          <td>${esc(String(pos.menge || item.menge || 1))} ${esc(pos.einheit || 'Stk')}</td>
          <td>${esc(pos.tuertyp || '—')}</td>
          <td>${pos.brandschutz ? `<span class="tag tag-red">${esc(pos.brandschutz)}</span>` : '<span style="color:var(--gray-300)">—</span>'}</td>
          <td>${pos.einbruchschutz ? `<span class="tag tag-blue">${esc(pos.einbruchschutz)}</span>` : '<span style="color:var(--gray-300)">—</span>'}</td>
          <td style="font-size:.75rem;color:var(--gray-500);max-width:200px;">${esc(item.reason || '')}</td>
        </tr>`;
    }).join('');

    container.innerHTML += `
      <div class="positions-section">
        <div class="section-header ${cls}">
          <span>${icon}</span>
          <span>${label}</span>
          <span class="section-badge">${items.length}</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr>
              <th>Pos.</th><th>Beschreibung</th><th>Menge</th>
              <th>Türtyp</th><th>Brandschutz</th><th>Einbruchschutz</th><th>Hinweis</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  });
}

// ─────────────────────────────────────────────
// RESET
// ─────────────────────────────────────────────

function resetAll() {
  state = { file: null, fileId: null, analysis: null, offer: null };

  clearFile();
  ['upload','ai','match','gen'].forEach(s => setStep(s, 'pending', 'Warte...'));

  document.getElementById('stat-grid').innerHTML = '';
  document.getElementById('download-grid').innerHTML = '';
  document.getElementById('positions-container').innerHTML = '';
  document.getElementById('match-bar').style.width = '0%';

  showPanel('upload');
  setPill(1);
}

// ─────────────────────────────────────────────
// UI HELPERS
// ─────────────────────────────────────────────

function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active-panel'));
  document.getElementById(`panel-${name}`).classList.add('active-panel');
}

function showError(msg) {
  document.getElementById('error-msg').textContent = msg;
  showPanel('error');
}

function setPill(n) {
  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById(`pill-${i}`);
    el.classList.remove('active','done');
    if (i < n) el.classList.add('done');
    if (i === n) el.classList.add('active');
  }
}

const DOT_SVG = {
  running: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><circle cx="12" cy="12" r="3" fill="white"/></svg>`,
  done:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`,
  error:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  pending: '',
};

function setStep(id, state, statusText) {
  const item   = document.getElementById(`step-${id}`);
  const dot    = item.querySelector('.step-dot');
  const status = item.querySelector('.step-status');

  dot.className = `step-dot ${state}`;
  dot.innerHTML = DOT_SVG[state] || '';
  status.textContent = statusText;
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─────────────────────────────────────────────
// PRODUCTS
// ─────────────────────────────────────────────

let _searchTimer;

async function loadProducts() {
  const loading = document.getElementById('products-loading');
  const errEl   = document.getElementById('products-error');
  const infoEl  = document.getElementById('products-info');
  const tableW  = document.getElementById('products-table-wrap');

  loading.classList.remove('hidden');
  errEl.classList.add('hidden');
  tableW.classList.add('hidden');

  try {
    const q = document.getElementById('product-search').value.trim();
    const url = q ? `/products?search=${encodeURIComponent(q)}&limit=100` : '/products?limit=100';
    const data = await api(url);

    loading.classList.add('hidden');
    infoEl.classList.remove('hidden');
    infoEl.textContent = `${data.returned} von ${data.total} Produkten`;

    renderProducts(data.products);
  } catch (err) {
    loading.classList.add('hidden');
    errEl.classList.remove('hidden');
    errEl.textContent = `Fehler: ${err.message}`;
  }
}

function searchProducts() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(loadProducts, 400);
}

function renderProducts(products) {
  const tableW = document.getElementById('products-table-wrap');
  if (!products?.length) { tableW.classList.add('hidden'); return; }

  const cols = [...new Set(products.slice(0,5).flatMap(p => Object.keys(p)))].slice(0, 8);

  document.getElementById('products-thead').innerHTML =
    '<tr>' + cols.map(c => `<th>${esc(c)}</th>`).join('') + '</tr>';

  document.getElementById('products-tbody').innerHTML =
    products.map(p => '<tr>' + cols.map(c => `<td>${esc(p[c] || '')}</td>`).join('') + '</tr>').join('');

  tableW.classList.remove('hidden');
}

// ─────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────

async function api(path, opts = {}) {
  const url = path.startsWith('http') ? path : `${API}${path}`;
  const res  = await fetch(url, opts);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}
