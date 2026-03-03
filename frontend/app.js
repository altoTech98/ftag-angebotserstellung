/**
 * Frank Tueren AG – KI Machbarkeitsanalyse
 * Simplified Frontend (single file upload, detail modal, catalog management)
 */

const API = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api'
  : `${window.location.origin}/api`;

let state = {
  file: null,
  fileId: null,
  analysis: null,
  offer: null,
};

// Store analysis items for detail modal
window._analysisItems = [];

// ─────────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────────

function switchView(view, btn) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById(`view-${view}`).classList.add('active');
  btn.classList.add('active');

  if (view === 'catalog') loadCatalogInfo();
  if (view === 'history') loadHistory();
}

// ─────────────────────────────────────────────
// FILE HANDLING (single Excel file)
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
  const files = Array.from(e.dataTransfer.files);
  if (files.length > 0) {
    const f = files[0];
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['xlsx', 'xls', 'xlsm', 'pdf', 'docx', 'doc', 'txt'].includes(ext)) {
      showToast('Dateityp nicht unterstuetzt. Erlaubt: Excel, PDF, Word, TXT');
      return;
    }
    setFile(f);
  }
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  if (files.length > 0) setFile(files[0]);
}

function setFile(f) {
  state.file = f;
  document.getElementById('file-preview').classList.remove('hidden');
  document.getElementById('file-name').textContent = f.name;
  document.getElementById('file-size').textContent = fmtSize(f.size);
  const ext = f.name.split('.').pop().toLowerCase();
  const icons = { pdf: '\u{1F4D5}', xlsx: '\u{1F4D7}', xls: '\u{1F4D7}', xlsm: '\u{1F4D7}', docx: '\u{1F4D8}', doc: '\u{1F4D8}', txt: '\u{1F4C4}' };
  document.querySelector('#file-preview .file-preview-icon').textContent = icons[ext] || '\u{1F4C4}';
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
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

// ─────────────────────────────────────────────
// MAIN WORKFLOW (upload → analyze → generate)
// ─────────────────────────────────────────────

function startUpload() {
  if (state.file) runAnalysisWorkflow();
}

async function runAnalysisWorkflow() {
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
    setStep('upload', 'done', `${up.filename} hochgeladen (${up.text_length.toLocaleString('de-CH')} Zeichen)`);

    // 2. Analyze (background job)
    setStep('ai', 'running', 'Tuerliste wird geparst...');
    document.getElementById('processing-subtitle').textContent = 'Tuerliste wird analysiert...';

    const { job_id } = await api('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: state.fileId }),
    });

    const analysis = await pollJob(job_id, (progress) => {
      document.getElementById('processing-subtitle').textContent = progress || 'Analyse laeuft...';
    });
    state.analysis = analysis;

    const pos = analysis.requirements?.positionen?.length || 0;
    setStep('ai', 'done', `${pos} Tuerpositionen erkannt`);

    // 3. Matching results
    const s = analysis.matching?.summary || {};
    setStep('match', 'done',
      `${s.matched_count || 0} erfuellbar, ${s.partial_count || 0} teilweise, ${s.unmatched_count || 0} nicht erfuellbar`
    );
    document.getElementById('processing-subtitle').textContent = 'Machbarkeitsanalyse wird erstellt...';

    // 4. Generate result Excel
    setStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...');
    const { job_id: resultJobId } = await api('/result/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requirements: analysis.requirements,
        matching: analysis.matching,
      }),
    });
    const result = await pollJob(resultJobId, (progress) => {
      document.getElementById('processing-subtitle').textContent = progress || 'Ergebnis wird erstellt...';
    }, '/result/status/');
    state.offer = result;
    setStep('gen', 'done', result.message);

    setPill(3);
    showResults(analysis, result);

  } catch (err) {
    console.error('[Workflow] Analysis failed:', err);
    showError(err.message);
    setPill(1);
  }
}

// ─────────────────────────────────────────────
// JOB POLLING
// ─────────────────────────────────────────────

async function pollJob(jobId, onProgress, statusPath = '/analyze/status/') {
  const POLL_INTERVAL = 2000;
  const MAX_POLLS = 450;

  for (let i = 0; i < MAX_POLLS; i++) {
    await new Promise(r => setTimeout(r, POLL_INTERVAL));
    const job = await api(`${statusPath}${jobId}`);
    if (job.progress && onProgress) onProgress(job.progress);
    if (job.status === 'completed') return job.result;
    if (job.status === 'failed') throw new Error(job.error || 'Verarbeitung fehlgeschlagen');
  }
  throw new Error('Timeout: Bitte erneut versuchen.');
}

// ─────────────────────────────────────────────
// RESULTS
// ─────────────────────────────────────────────

function showResults(analysis, offer) {
  showPanel('results');

  const req = analysis.requirements || {};
  const match = analysis.matching || {};
  const summary = match.summary || {};

  // Stat cards (clickable – scroll to section)
  const statGrid = document.getElementById('stat-grid');
  const stats = [
    { num: summary.total_positions || 0, label: 'Positionen gesamt', cls: 'blue', target: 'positions-container' },
    { num: summary.matched_count || 0, label: 'Erfuellbar', cls: 'green', target: 'section-matched' },
    { num: summary.partial_count || 0, label: 'Teilweise', cls: 'orange', target: 'section-partial' },
    { num: summary.unmatched_count || 0, label: 'Nicht erfuellbar', cls: 'red', target: 'section-unmatched' },
  ];
  statGrid.innerHTML = stats.map((s, i) => `
    <div class="stat-card ${s.cls} clickable" style="animation-delay:${i * 80}ms" onclick="scrollToSection('${s.target}')">
      <div class="stat-num">${s.num}</div>
      <div class="stat-label">${s.label}</div>
    </div>
  `).join('');

  // Match rate bar
  const rate = summary.match_rate || 0;
  document.getElementById('match-rate-pct').textContent = `${rate}%`;
  document.getElementById('match-rate-sub').textContent =
    `Projekt: ${req.projekt || 'Tuerliste'} · ${summary.total_positions || 0} Positionen`;
  setTimeout(() => {
    document.getElementById('match-bar').style.width = `${rate}%`;
  }, 100);

  // Downloads
  const dlGrid = document.getElementById('download-grid');
  dlGrid.innerHTML = '';

  if (offer.has_result && offer.result_id) {
    dlGrid.innerHTML += `
      <div class="dl-group">
        <div class="dl-group-title">Machbarkeitsanalyse + GAP-Report</div>
        <div class="dl-buttons">
          <a href="${API}/result/${offer.result_id}/download" class="dl-btn excel" download="FTAG_Machbarkeit_${offer.result_id}.xlsx">
            <span class="dl-icon">&#128215;</span> Excel herunterladen
          </a>
        </div>
      </div>
    `;
  }

  if (!offer.has_result) {
    dlGrid.innerHTML = '<p style="color:var(--text-faint);font-size:.875rem;grid-column:1/-1;">Keine Dokumente erstellt.</p>';
  }

  // Build flat list of all items for detail modal
  window._analysisItems = [];
  const sections = [
    { items: match.matched || [], status: 'matched', label: 'Erfuellbare Positionen', cls: 'green', icon: '&#10003;' },
    { items: match.partial || [], status: 'partial', label: 'Teilweise erfuellbare Positionen', cls: 'orange', icon: '&#9888;' },
    { items: match.unmatched || [], status: 'unmatched', label: 'Nicht erfuellbare Positionen', cls: 'red', icon: '&#10007;' },
  ];

  sections.forEach(sec => {
    sec.items.forEach(item => {
      window._analysisItems.push({ ...item, _status: sec.status });
    });
  });

  // Positions table
  const container = document.getElementById('positions-container');
  container.innerHTML = '';

  let globalIdx = 0;
  sections.forEach(({ items, label, cls, icon, status }) => {
    if (!items.length) return;

    const rows = items.map(item => {
      const idx = globalIdx++;
      const pos = item.original_position || item;

      // FTAG product name
      const products = item.matched_products || [];
      let ftag = '—';
      if (products.length > 0) {
        const p = products[0];
        ftag = p['Tuerblatt / Verglasungsart / Rollkasten']
          || p[Object.keys(p).find(k => k.includes('blatt') || k.includes('Verglasungsart')) || '']
          || Object.values(p)[1] || '—';
      }

      return `
        <tr onclick="openDetailModal(${idx})" class="clickable-row">
          <td><strong>${esc(item.position || pos.position || '—')}</strong></td>
          <td>${esc(item.beschreibung || pos.beschreibung || pos.tuertyp || '—')}</td>
          <td>${esc(String(pos.menge || item.menge || 1))}</td>
          <td>${esc(pos.brandschutz || '—')}</td>
          <td style="font-size:.8rem;" title="${esc(ftag)}">${esc(ftag.substring(0, 35))}${ftag.length > 35 ? '...' : ''}</td>
          <td>${esc(item.category || '—')}</td>
          <td style="font-size:.75rem;">
            ${item.confidence ? `<span style="color:var(--text-faint);">${(item.confidence * 100).toFixed(0)}%</span> ` : ''}
            ${item.reason ? `<span style="color:var(--text-muted);">${esc(item.reason.substring(0, 60))}</span>` : ''}
          </td>
        </tr>`;
    }).join('');

    container.innerHTML += `
      <div class="positions-section" id="section-${status}">
        <div class="section-header ${cls}">
          <span>${icon}</span>
          <span>${label}</span>
          <span class="section-badge">${items.length}</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr>
              <th>Pos.</th><th>Beschreibung</th><th>Menge</th>
              <th>Brandschutz</th><th>FTAG Produkt</th><th>Kategorie</th><th>Begruendung</th>
            </tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>`;
  });
}

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ─────────────────────────────────────────────
// DETAIL MODAL (clickable positions)
// ─────────────────────────────────────────────

function openDetailModal(index) {
  const item = window._analysisItems[index];
  if (!item) return;

  const pos = item.original_position || item;
  const modal = document.getElementById('detail-modal');
  const title = document.getElementById('detail-modal-title');
  const body = document.getElementById('detail-modal-body');

  title.textContent = `Position ${item.position || pos.position || index + 1}`;

  // Build customer requirement fields
  const fields = [
    ['Tuer-Nr', pos.position || item.position],
    ['Beschreibung', item.beschreibung || pos.beschreibung],
    ['Tuertyp', pos.tuertyp],
    ['Brandschutz', pos.brandschutz],
    ['Schallschutz', pos.schallschutz],
    ['Einbruchschutz', pos.einbruchschutz || pos.widerstandsklasse],
    ['Breite', pos.breite ? `${pos.breite} mm` : null],
    ['Hoehe', pos.hoehe ? `${pos.hoehe} mm` : null],
    ['Menge', pos.menge],
    ['Raum', pos.raum_bezeichnung || pos.raum],
    ['Geschoss', pos.geschoss],
    ['Zargentyp', pos.zargentyp],
    ['Schlosstyp', pos.schloss_typ],
    ['Bandtyp', pos.bandtyp || pos.band],
    ['Oberflaechentyp', pos.oberflaechentyp || pos.oberflaeche],
    ['Glasausschnitt', pos.glasausschnitt || pos.verglasung],
    ['Fluegel', pos.fluegel_anzahl || pos.anzahl_fluegel],
  ].filter(([, v]) => v != null && v !== '' && v !== '—');

  const fieldsHtml = fields.map(([label, value]) =>
    `<div class="detail-field"><span class="detail-field-label">${esc(label)}</span><span class="detail-field-value">${esc(String(value))}</span></div>`
  ).join('');

  // FTAG product
  const products = item.matched_products || [];
  let productHtml = '<p style="color:var(--text-muted);">Kein passendes Produkt gefunden</p>';
  if (products.length > 0) {
    const p = products[0];
    const productFields = Object.entries(p)
      .filter(([k, v]) => v != null && v !== '' && !k.startsWith('_'))
      .slice(0, 10)
      .map(([k, v]) => `<div class="detail-field"><span class="detail-field-label">${esc(k)}</span><span class="detail-field-value">${esc(String(v))}</span></div>`)
      .join('');
    productHtml = `<div class="detail-fields">${productFields}</div>`;
  }

  // Match criteria / GAP
  const criteria = item.match_criteria || [];
  let criteriaHtml = '';
  if (criteria.length) {
    criteriaHtml = `
      <h4 style="font-size:.875rem;font-weight:600;margin:1rem 0 .5rem;">Kriterien</h4>
      <div class="detail-criteria">
        ${criteria.map(c => {
          const cls = c.status === 'ok' ? 'criteria-ok' : c.status === 'fehlt' ? 'criteria-fehlt' : 'criteria-teilweise';
          const icon = c.status === 'ok' ? '&#10003;' : c.status === 'fehlt' ? '&#10007;' : '~';
          return `<div class="detail-gap-item ${cls}">
            <span>${icon} <strong>${esc(c.kriterium || '')}</strong></span>
            <span style="color:var(--text-muted);font-size:.8rem;">${esc(c.detail || '')}</span>
          </div>`;
        }).join('')}
      </div>`;
  }

  // Reason
  const reasonHtml = item.reason
    ? `<div style="margin-top:.75rem;padding:.5rem .75rem;background:var(--bg-hover);border-radius:var(--radius);font-size:.8125rem;color:var(--text-muted);">${esc(item.reason)}</div>`
    : '';

  // Status badge
  const statusMap = {
    matched: { label: 'Erfuellbar', cls: 'tag-green' },
    partial: { label: 'Teilweise', cls: 'tag-orange' },
    unmatched: { label: 'Nicht erfuellbar', cls: 'tag-red' },
  };
  const st = statusMap[item._status] || { label: item._status, cls: '' };

  body.innerHTML = `
    <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:1rem;">
      <span class="tag ${st.cls}">${st.label}</span>
      ${item.confidence ? `<span style="color:var(--text-faint);font-size:.8125rem;">Konfidenz: ${(item.confidence * 100).toFixed(0)}%</span>` : ''}
      <span style="color:var(--text-faint);font-size:.8125rem;">Kategorie: ${esc(item.category || '—')}</span>
    </div>

    <h4 style="font-size:.875rem;font-weight:600;margin-bottom:.5rem;">Kundenanforderung</h4>
    <div class="detail-fields">${fieldsHtml}</div>

    <h4 style="font-size:.875rem;font-weight:600;margin:1rem 0 .5rem;">FTAG Produkt</h4>
    ${productHtml}

    ${criteriaHtml}
    ${reasonHtml}
  `;

  modal.classList.remove('hidden');
}

function closeDetailModal() {
  document.getElementById('detail-modal').classList.add('hidden');
}

// ─────────────────────────────────────────────
// CATALOG MANAGEMENT
// ─────────────────────────────────────────────

let _catalogFile = null;

async function loadCatalogInfo() {
  const loading = document.getElementById('catalog-info-loading');
  const content = document.getElementById('catalog-info-content');
  const errEl = document.getElementById('catalog-info-error');

  loading.classList.remove('hidden');
  content.classList.add('hidden');
  errEl.classList.add('hidden');

  try {
    const data = await api('/catalog/info');
    loading.classList.add('hidden');
    content.classList.remove('hidden');

    const statsEl = document.getElementById('catalog-stats');
    statsEl.innerHTML = [
      { num: data.total_products, label: 'Produkte gesamt', cls: 'blue' },
      { num: data.main_products, label: 'Hauptprodukte', cls: 'green' },
      { num: data.accessory_products, label: 'Zubehoer', cls: 'orange' },
      { num: data.categories, label: 'Kategorien', cls: '' },
    ].map(s => `
      <div class="stat-card ${s.cls}">
        <div class="stat-num">${s.num}</div>
        <div class="stat-label">${s.label}</div>
      </div>
    `).join('');

    const catEl = document.getElementById('catalog-categories');
    if (data.category_breakdown) {
      const cats = Object.entries(data.category_breakdown).sort((a, b) => b[1] - a[1]);
      catEl.innerHTML = `
        <p style="font-size:.8125rem;font-weight:600;margin-bottom:.5rem;">Kategorien</p>
        <div style="display:flex;flex-wrap:wrap;gap:.375rem;">
          ${cats.map(([name, count]) =>
            `<span class="tag tag-blue">${esc(name)}: ${count}</span>`
          ).join('')}
        </div>
        <p style="font-size:.75rem;color:var(--text-faint);margin-top:.5rem;">
          Datei: ${esc(data.filename)} &middot; Letzte Aenderung: ${esc(data.last_modified)}
        </p>
      `;
    }
  } catch (err) {
    loading.classList.add('hidden');
    errEl.classList.remove('hidden');
    errEl.textContent = `Katalog konnte nicht geladen werden: ${err.message}`;
  }
}

function handleCatalogDragOver(e) {
  e.preventDefault();
  document.getElementById('catalog-drop-zone').classList.add('drag-over');
}

function handleCatalogDragLeave() {
  document.getElementById('catalog-drop-zone').classList.remove('drag-over');
}

function handleCatalogDrop(e) {
  e.preventDefault();
  document.getElementById('catalog-drop-zone').classList.remove('drag-over');
  const files = Array.from(e.dataTransfer.files);
  if (files.length > 0) {
    if (!files[0].name.toLowerCase().endsWith('.xlsx')) {
      showToast('Nur .xlsx Dateien erlaubt.');
      return;
    }
    setCatalogFile(files[0]);
  }
}

function handleCatalogFileSelect(e) {
  const files = Array.from(e.target.files);
  if (files.length > 0) setCatalogFile(files[0]);
}

function setCatalogFile(f) {
  _catalogFile = f;
  const preview = document.getElementById('catalog-upload-preview');
  preview.classList.remove('hidden');
  document.getElementById('catalog-file-name').textContent = f.name;
  document.getElementById('catalog-file-size').textContent = fmtSize(f.size);
  document.getElementById('btn-catalog-upload').disabled = false;
}

function clearCatalogFile() {
  _catalogFile = null;
  document.getElementById('catalog-upload-preview').classList.add('hidden');
  document.getElementById('catalog-file-input').value = '';
  document.getElementById('btn-catalog-upload').disabled = true;
}

async function uploadCatalog() {
  if (!_catalogFile) return;

  const btn = document.getElementById('btn-catalog-upload');
  btn.disabled = true;
  btn.textContent = 'Wird hochgeladen...';

  try {
    const form = new FormData();
    form.append('file', _catalogFile);
    const result = await api('/catalog/upload', { method: 'POST', body: form });

    showToast(result.message);
    clearCatalogFile();
    btn.textContent = 'Katalog hochladen';

    // Reload catalog info
    loadCatalogInfo();
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
    btn.disabled = false;
    btn.textContent = 'Katalog hochladen';
  }
}

// ─────────────────────────────────────────────
// RESET
// ─────────────────────────────────────────────

function resetAll() {
  state = { file: null, fileId: null, analysis: null, offer: null };
  window._analysisItems = [];

  clearFile();
  ['upload', 'ai', 'match', 'gen'].forEach(s => setStep(s, 'pending', 'Warte...'));

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
    if (!el) continue;
    el.classList.remove('active', 'done');
    if (i < n) el.classList.add('done');
    if (i === n) el.classList.add('active');
  }
}

const DOT_SVG = {
  running: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><circle cx="12" cy="12" r="3" fill="white"/></svg>`,
  done: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`,
  error: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  pending: '',
};

function setStep(id, dotState, statusText) {
  const item = document.getElementById(`step-${id}`);
  if (!item) return;
  const dot = item.querySelector('.step-dot');
  const status = item.querySelector('.step-status');
  dot.className = `step-dot ${dotState}`;
  dot.innerHTML = DOT_SVG[dotState] || '';
  status.textContent = statusText;
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ─────────────────────────────────────────────
// HISTORY
// ─────────────────────────────────────────────

async function loadHistory() {
  const loading = document.getElementById('history-loading');
  const errEl = document.getElementById('history-error');
  const emptyEl = document.getElementById('history-empty');
  const tableW = document.getElementById('history-table-wrap');

  loading.classList.remove('hidden');
  errEl.classList.add('hidden');
  emptyEl.classList.add('hidden');
  tableW.classList.add('hidden');
  document.getElementById('history-detail').classList.add('hidden');

  try {
    const data = await api('/history');
    loading.classList.add('hidden');

    if (!data.analyses || data.analyses.length === 0) {
      emptyEl.classList.remove('hidden');
      return;
    }
    renderHistoryTable(data.analyses);
  } catch (err) {
    loading.classList.add('hidden');
    errEl.classList.remove('hidden');
    errEl.textContent = `Fehler: ${err.message}`;
  }
}

function renderHistoryTable(analyses) {
  const tableW = document.getElementById('history-table-wrap');
  const tbody = document.getElementById('history-tbody');

  tbody.innerHTML = analyses.map(a => {
    const date = new Date(a.timestamp).toLocaleDateString('de-CH', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    const rateColor = a.match_rate >= 70 ? 'green' : a.match_rate >= 40 ? 'orange' : 'red';
    return `
      <tr>
        <td style="white-space:nowrap;">${esc(date)}</td>
        <td>${esc(a.filename || a.id)}</td>
        <td>${esc(a.projekt || '—')}</td>
        <td>
          <span class="tag tag-green">${a.matched_count || 0}</span>
          <span class="tag tag-orange">${a.partial_count || 0}</span>
          <span class="tag tag-red">${a.unmatched_count || 0}</span>
        </td>
        <td><span class="tag tag-${rateColor}">${a.match_rate || 0}%</span></td>
        <td class="action-cell">
          <button class="correction-btn" onclick="showHistoryDetail('${esc(a.id)}')">Details</button>
          <button class="correction-btn" onclick="rematchHistory('${esc(a.id)}')" title="Mit aktuellen Daten neu matchen">Neu matchen</button>
          <button class="confirm-btn" onclick="deleteHistory('${esc(a.id)}')" style="color:var(--danger);background:var(--danger-light);border-color:var(--danger-border);">&times;</button>
        </td>
      </tr>`;
  }).join('');

  tableW.classList.remove('hidden');
}

async function showHistoryDetail(historyId) {
  try {
    const data = await api(`/history/${historyId}`);
    const detailPanel = document.getElementById('history-detail');
    detailPanel.classList.remove('hidden');

    document.getElementById('history-detail-title').textContent =
      `Analyse: ${data.projekt || data.filename || historyId}`;
    document.getElementById('history-detail-sub').textContent =
      `${new Date(data.timestamp).toLocaleDateString('de-CH')} · ${data.auftraggeber || ''}`;

    const summary = data.matching?.summary || {};
    const statsEl = document.getElementById('history-detail-stats');
    statsEl.innerHTML = [
      { num: summary.total_positions || 0, label: 'Positionen', cls: 'blue' },
      { num: summary.matched_count || 0, label: 'Erfuellbar', cls: 'green' },
      { num: summary.partial_count || 0, label: 'Teilweise', cls: 'orange' },
      { num: summary.unmatched_count || 0, label: 'Nicht erfuellbar', cls: 'red' },
    ].map(s => `
      <div class="stat-card ${s.cls}">
        <div class="stat-num">${s.num}</div>
        <div class="stat-label">${s.label}</div>
      </div>
    `).join('');

    const container = document.getElementById('history-detail-positions');
    container.innerHTML = '';
    const match = data.matching || {};
    const sections = [
      { items: match.matched || [], label: 'Erfuellbar', cls: 'green', icon: '&#10003;' },
      { items: match.partial || [], label: 'Teilweise', cls: 'orange', icon: '~' },
      { items: match.unmatched || [], label: 'Nicht erfuellbar', cls: 'red', icon: '&#10007;' },
    ];
    sections.forEach(({ items, label, cls, icon }) => {
      if (!items.length) return;
      const rows = items.map(item => {
        const pos = item.original_position || item;
        return `<tr>
          <td><strong>${esc(item.position || pos.position || '—')}</strong></td>
          <td>${esc(item.beschreibung || pos.beschreibung || '—')}</td>
          <td>${esc(String(pos.menge || item.menge || 1))} ${esc(pos.einheit || 'Stk')}</td>
          <td>${esc(pos.tuertyp || '—')}</td>
          <td style="font-size:.75rem;">${renderMatchCriteria(item.match_criteria)}${
            item.reason && (!item.match_criteria || !item.match_criteria.length)
            ? `<span style="color:var(--text-muted);">${esc(item.reason)}</span>` : ''
          }</td>
        </tr>`;
      }).join('');
      container.innerHTML += `
        <div class="positions-section">
          <div class="section-header ${cls}">
            <span>${icon}</span><span>${label}</span>
            <span class="section-badge">${items.length}</span>
          </div>
          <div class="table-wrap"><table class="data-table">
            <thead><tr><th>Pos.</th><th>Beschreibung</th><th>Menge</th><th>Tuertyp</th><th>Kriterien</th></tr></thead>
            <tbody>${rows}</tbody>
          </table></div>
        </div>`;
    });

    detailPanel.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
  }
}

function closeHistoryDetail() {
  document.getElementById('history-detail').classList.add('hidden');
}

async function rematchHistory(historyId) {
  if (!confirm('Analyse mit aktuellen Daten neu matchen?')) return;
  showToast('Rematch wird durchgefuehrt...');
  try {
    const result = await api(`/history/${historyId}/rematch`, { method: 'POST' });
    showToast(result.message);
    loadHistory();
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
  }
}

async function deleteHistory(historyId) {
  if (!confirm('Diese Analyse wirklich loeschen?')) return;
  try {
    await api(`/history/${historyId}`, { method: 'DELETE' });
    showToast('Analyse geloescht.');
    loadHistory();
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
  }
}

// ─────────────────────────────────────────────
// MATCH CRITERIA RENDERING
// ─────────────────────────────────────────────

function renderMatchCriteria(criteria) {
  if (!criteria || !criteria.length) return '';
  return criteria.map(c => {
    const statusCls = c.status === 'ok' ? 'criteria-ok'
      : c.status === 'fehlt' ? 'criteria-fehlt'
      : 'criteria-teilweise';
    const icon = c.status === 'ok' ? '&#10003;' : c.status === 'fehlt' ? '&#10007;' : '~';
    return `<span class="criteria-tag ${statusCls}" title="${esc(c.detail || '')}">${icon} ${esc(c.kriterium || '')}</span>`;
  }).join(' ');
}

// ─────────────────────────────────────────────
// CORRECTION SYSTEM (Feedback / Training)
// ─────────────────────────────────────────────

let correctionState = {
  positionData: null,
  selectedProduct: null,
};

function openCorrection(btn) {
  const d = btn.dataset;
  correctionState.positionData = { ...d };
  correctionState.selectedProduct = null;

  let products = [];
  try { products = JSON.parse(d.matchedProduct || '[]'); } catch {}
  const currentProduct = products.length > 0
    ? Object.values(products[0]).join(' | ')
    : 'Kein Produkt zugeordnet';
  document.getElementById('correction-current-product').textContent = currentProduct;

  const reqParts = [d.beschreibung, d.tuertyp, d.brandschutz, d.einbruchschutz].filter(Boolean);
  document.getElementById('correction-requirement').textContent = reqParts.join(' | ') || '---';

  document.getElementById('correction-search-input').value = '';
  document.getElementById('correction-results').innerHTML = '';
  document.getElementById('correction-note-input').value = '';
  document.getElementById('btn-save-correction').disabled = true;
  document.getElementById('btn-save-correction').textContent = 'Korrektur speichern';

  document.getElementById('correction-modal').classList.remove('hidden');

  const autoSearch = [d.tuertyp, d.brandschutz].filter(Boolean).join(' ');
  if (autoSearch) {
    document.getElementById('correction-search-input').value = autoSearch;
    searchCorrectionProducts();
  }
}

function closeCorrection() {
  document.getElementById('correction-modal').classList.add('hidden');
  correctionState = { positionData: null, selectedProduct: null };
}

let _corrSearchTimer;
function searchCorrectionProducts() {
  clearTimeout(_corrSearchTimer);
  _corrSearchTimer = setTimeout(async () => {
    const q = document.getElementById('correction-search-input').value.trim();
    if (!q) {
      document.getElementById('correction-results').innerHTML = '';
      return;
    }
    try {
      const data = await api(`/products/search?q=${encodeURIComponent(q)}&limit=15`);
      renderCorrectionResults(data.products);
    } catch (err) {
      document.getElementById('correction-results').innerHTML =
        `<p class="error-inline" style="padding:0.75rem;">Fehler: ${esc(err.message)}</p>`;
    }
  }, 350);
}

function renderCorrectionResults(products) {
  const container = document.getElementById('correction-results');
  if (!products?.length) {
    container.innerHTML = '<p class="info-inline" style="padding:0.75rem;">Keine Produkte gefunden</p>';
    return;
  }
  container.innerHTML = products.map(p => `
    <div class="correction-product-item"
         data-row-index="${p._row_index}"
         data-summary="${esc(p._summary)}"
         onclick="selectCorrectionProduct(this)">
      <div class="correction-product-summary">${esc(p._summary)}</div>
      <div class="correction-product-details">
        ${Object.entries(p)
          .filter(([k]) => !k.startsWith('_'))
          .slice(0, 6)
          .map(([k, v]) => `<span class="tag tag-blue">${esc(k)}: ${esc(v)}</span>`)
          .join(' ')}
      </div>
    </div>
  `).join('');
}

function selectCorrectionProduct(el) {
  document.querySelectorAll('.correction-product-item.selected')
    .forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  correctionState.selectedProduct = {
    row_index: parseInt(el.dataset.rowIndex),
    product_summary: el.dataset.summary,
  };
  document.getElementById('btn-save-correction').disabled = false;
}

async function saveCorrection() {
  if (!correctionState.selectedProduct || !correctionState.positionData) return;

  const d = correctionState.positionData;
  let matchedProducts = [];
  try { matchedProducts = JSON.parse(d.matchedProduct || '[]'); } catch {}
  const wrongProduct = matchedProducts.length > 0
    ? { row_index: null, product_summary: Object.values(matchedProducts[0]).join(' | ') }
    : { row_index: null, product_summary: 'Kein Produkt' };

  const body = {
    requirement_text: [d.beschreibung, d.tuertyp, d.brandschutz, d.einbruchschutz]
      .filter(Boolean).join(' | '),
    requirement_fields: {
      tuertyp: d.tuertyp || null,
      brandschutz: d.brandschutz || null,
      einbruchschutz: d.einbruchschutz || null,
      breite: d.breite ? parseInt(d.breite) : null,
      hoehe: d.hoehe ? parseInt(d.hoehe) : null,
    },
    wrong_product: wrongProduct,
    correct_product: correctionState.selectedProduct,
    position_id: d.position || '?',
    match_status_was: d.status || 'unknown',
    user_note: document.getElementById('correction-note-input').value.trim(),
  };

  try {
    const btn = document.getElementById('btn-save-correction');
    btn.disabled = true;
    btn.textContent = 'Wird gespeichert...';
    await api('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    closeCorrection();
    showToast('Korrektur gespeichert.');
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
    const btn = document.getElementById('btn-save-correction');
    btn.disabled = false;
    btn.textContent = 'Korrektur speichern';
  }
}

// ─────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────

async function api(path, opts = {}) {
  const url = path.startsWith('http') ? path : `${API}${path}`;
  let res;
  try {
    res = await fetch(url, opts);
  } catch (networkErr) {
    console.error(`[API] Network error for ${path}:`, networkErr);
    throw new Error('Server nicht erreichbar. Ist der Server gestartet?');
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    let detail = null;
    try {
      const body = await res.json();
      detail = body.detail;
      msg = detail || msg;
    } catch {}
    if (res.status === 410) {
      msg = detail || 'Datei abgelaufen – bitte erneut hochladen.';
    }
    console.error(`[API] Error ${res.status} for ${path}:`, detail || msg);
    throw new Error(msg);
  }
  return res.json();
}

// ─────────────────────────────────────────────
// HEALTH CHECK
// ─────────────────────────────────────────────

async function checkServerHealth() {
  const dot = document.getElementById('server-status');
  if (!dot) return;

  try {
    const res = await fetch(`${API.replace('/api', '')}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.api_key_set) {
      dot.style.background = '#d97706';
      dot.title = 'API-Key fehlt (wird fuer Text-Analyse benoetigt)';
    } else {
      dot.style.background = '';
      dot.title = 'Server verbunden';
    }
  } catch (err) {
    dot.style.background = '#dc2626';
    dot.classList.add('offline');
    dot.title = 'Server nicht erreichbar';
    console.error('Health check failed:', err);
  }
}

// Close modals with Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeDetailModal();
    closeCorrection();
  }
});

// Header scroll shadow
window.addEventListener('scroll', () => {
  const header = document.getElementById('header');
  if (header) header.classList.toggle('scrolled', window.scrollY > 0);
}, { passive: true });

// Run health check on load
checkServerHealth();
