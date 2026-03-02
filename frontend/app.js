/**
 * Frank Türen AG – KI Angebotserstellung
 * Modern Frontend App
 */

const API = window.location.hostname === 'localhost'
  ? 'http://localhost:8000/api'
  : `${window.location.origin}/api`;

let state = {
  file: null,
  fileId: null,
  analysis: null,
  offer: null,
  // Project mode (folder upload)
  uploadMode: 'folder',  // 'folder' | 'files'
  files: [],             // Array of File objects
  projectId: null,
  projectFiles: [],      // Response from /api/upload/folder
  classificationOverrides: {},
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
    history:  ['Analyse-Historie', 'Vergangene Analysen einsehen und vergleichen'],
  };
  document.getElementById('topbar-title').textContent = titles[view][0];
  document.getElementById('topbar-sub').textContent   = titles[view][1];

  if (view === 'products') loadProducts();
  if (view === 'history') loadHistory();
}

// ─────────────────────────────────────────────
// UPLOAD MODE TOGGLE
// ─────────────────────────────────────────────

function setUploadMode(mode) {
  state.uploadMode = mode;
  document.getElementById('toggle-folder').classList.toggle('active', mode === 'folder');
  document.getElementById('toggle-files').classList.toggle('active', mode === 'files');

  const mainText = document.getElementById('drop-main-text');
  const hintText = document.getElementById('drop-hint-text');

  if (mode === 'folder') {
    mainText.textContent = 'Ordner hier ablegen';
    hintText.innerHTML = 'oder <span class="drop-link" onclick="triggerFileInput(); event.stopPropagation()">auswählen</span> · PDF, XLSX, DOCX und mehr · max. 500 MB';
  } else {
    mainText.textContent = 'Dateien hier ablegen';
    hintText.innerHTML = 'oder <span class="drop-link" onclick="triggerFileInput(); event.stopPropagation()">auswählen</span> · Mehrere Dateien möglich · max. 500 MB';
  }
}

function triggerFileInput() {
  if (state.uploadMode === 'folder') {
    document.getElementById('folder-input').click();
  } else {
    document.getElementById('files-input').click();
  }
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

  // Check for folder drop via webkitGetAsEntry
  const items = e.dataTransfer.items;
  if (items && items.length > 0 && items[0].webkitGetAsEntry) {
    const entry = items[0].webkitGetAsEntry();
    if (entry && entry.isDirectory) {
      collectFolderFiles(entry).then(files => {
        if (files.length > 0) setFiles(files);
      });
      return;
    }
  }

  // Multi-file drop
  const files = Array.from(e.dataTransfer.files);
  if (files.length > 1) {
    setFiles(files);
  } else if (files.length === 1) {
    setFiles(files);
  }
}

function handleFolderSelect(e) {
  const files = Array.from(e.target.files);
  if (files.length > 0) setFiles(files);
}

function handleFilesSelect(e) {
  const files = Array.from(e.target.files);
  if (files.length > 0) setFiles(files);
}

async function collectFolderFiles(entry) {
  const files = [];

  async function readEntry(dirEntry) {
    return new Promise((resolve) => {
      if (dirEntry.isFile) {
        dirEntry.file(f => { files.push(f); resolve(); });
      } else if (dirEntry.isDirectory) {
        const reader = dirEntry.createReader();
        reader.readEntries(async (entries) => {
          for (const e of entries) {
            await readEntry(e);
          }
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  await readEntry(entry);
  return files;
}

function setFiles(fileList) {
  state.files = fileList;
  state.file = null;
  renderFilesPreview();
  document.getElementById('btn-upload').disabled = false;
}

function renderFilesPreview() {
  const container = document.getElementById('files-preview');
  const listEl = document.getElementById('files-list');
  const countEl = document.getElementById('files-count');
  const sizeEl = document.getElementById('files-total-size');

  if (!state.files.length) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  document.getElementById('file-preview').classList.add('hidden');

  const totalSize = state.files.reduce((sum, f) => sum + f.size, 0);
  countEl.textContent = `${state.files.length} Dateien`;
  sizeEl.textContent = fmtSize(totalSize);

  const FILE_ICONS = {
    '.pdf': '📕', '.xlsx': '📗', '.xls': '📗', '.xlsm': '📗',
    '.docx': '📘', '.doc': '📘', '.docm': '📘', '.txt': '📄',
    '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
    '.dwg': '📐', '.crbx': '📦',
  };

  listEl.innerHTML = state.files.map((f, i) => {
    const ext = '.' + f.name.split('.').pop().toLowerCase();
    const icon = FILE_ICONS[ext] || '📄';
    const category = guessCategory(f.name);
    return `
      <div class="file-item">
        <span class="file-item-icon">${icon}</span>
        <span class="file-item-name">${esc(f.name)}</span>
        <span class="file-item-size">${fmtSize(f.size)}</span>
        <span class="category-badge ${category}">${categoryLabel(category)}</span>
      </div>
    `;
  }).join('');
}

function guessCategory(filename) {
  const name = filename.toLowerCase();
  const ext = '.' + name.split('.').pop();
  if (['.dwg', '.dxf'].includes(ext)) return 'plan';
  if (['.jpg', '.jpeg', '.png', '.bmp', '.tif'].includes(ext)) return 'foto';
  if (ext === '.crbx') return 'sonstig';
  if (/t[üu]rliste|t[üu]rmatrix|tuerliste|tuermatrix/.test(name) && ['.xlsx', '.xls', '.xlsm'].includes(ext)) return 'tuerliste';
  if (/grundriss|situationsplan|lageplan/.test(name)) return 'plan';
  if (/leistungsverzeichnis|lv[_.\s-]|t[üu]rbuch|typicals|spezifikation|bedingung/.test(name)) return 'spezifikation';
  if (['.xlsx', '.xls', '.xlsm'].includes(ext)) return 'tuerliste';
  if (ext === '.pdf') return 'spezifikation';
  if (['.docx', '.doc', '.docm'].includes(ext)) return 'spezifikation';
  return 'sonstig';
}

function categoryLabel(cat) {
  const labels = {
    tuerliste: 'Türliste',
    spezifikation: 'Spezifikation',
    plan: 'Plan',
    foto: 'Foto',
    sonstig: 'Sonstig',
  };
  return labels[cat] || cat;
}

function clearFiles() {
  state.files = [];
  state.projectId = null;
  state.projectFiles = [];
  state.classificationOverrides = {};
  document.getElementById('files-preview').classList.add('hidden');
  document.getElementById('folder-input').value = '';
  document.getElementById('files-input').value = '';
  document.getElementById('btn-upload').disabled = true;
}

function clearFile() {
  state.file = null;
  document.getElementById('file-preview').classList.add('hidden');
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

function startUpload() {
  if (state.files.length > 0) {
    runProjectWorkflow();
  } else if (state.file) {
    runFullWorkflow();
  }
}

async function runProjectWorkflow() {
  if (!state.files.length) return;

  showPanel('processing');
  setPill(1);
  setStep('upload', 'running', `${state.files.length} Dateien werden hochgeladen...`);
  document.getElementById('processing-subtitle').textContent = 'Dateien werden hochgeladen...';

  try {
    // 1. Upload all files
    const form = new FormData();
    state.files.forEach(f => form.append('files', f));

    const up = await api('/upload/folder', { method: 'POST', body: form });
    state.projectId = up.project_id;
    state.projectFiles = up.files;

    const tl = up.summary.tuerliste_count;
    const sp = up.summary.spezifikation_count;
    setStep('upload', 'done',
      `${up.total_files} Dateien: ${tl} Türliste${tl !== 1 ? 'n' : ''}, ${sp} Spezifikation${sp !== 1 ? 'en' : ''}`
    );

    // 2. Show classification review
    setPill(2);
    renderClassification(up.files, up.summary);
    showPanel('classify');

  } catch (err) {
    console.error('[Workflow] Upload/classify failed:', err);
    showError(err.message);
    setPill(1);
  }
}

function renderClassification(files, summary) {
  const grid = document.getElementById('classification-grid');
  const subtitle = document.getElementById('classify-subtitle');
  const summaryEl = document.getElementById('classify-summary');

  subtitle.textContent = `${files.length} Dateien automatisch klassifiziert`;

  summaryEl.innerHTML = `
    <div class="classify-summary-badges">
      ${summary.tuerliste_count ? `<span class="category-badge tuerliste">${summary.tuerliste_count} Türliste${summary.tuerliste_count !== 1 ? 'n' : ''}</span>` : ''}
      ${summary.spezifikation_count ? `<span class="category-badge spezifikation">${summary.spezifikation_count} Spezifikation${summary.spezifikation_count !== 1 ? 'en' : ''}</span>` : ''}
      ${summary.plan_count ? `<span class="category-badge plan">${summary.plan_count} Pläne</span>` : ''}
      ${summary.foto_count ? `<span class="category-badge foto">${summary.foto_count} Fotos</span>` : ''}
      ${summary.sonstig_count ? `<span class="category-badge sonstig">${summary.sonstig_count} Sonstige</span>` : ''}
    </div>
  `;

  // Sort: tuerliste first, then spezifikation, then rest
  const order = { tuerliste: 0, spezifikation: 1, plan: 2, foto: 3, sonstig: 4 };
  const sorted = [...files].sort((a, b) => (order[a.category] || 9) - (order[b.category] || 9));

  const FILE_ICONS = {
    '.pdf': '📕', '.xlsx': '📗', '.xls': '📗', '.xlsm': '📗',
    '.docx': '📘', '.doc': '📘', '.docm': '📘', '.txt': '📄',
    '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️',
    '.dwg': '📐', '.crbx': '📦',
  };

  grid.innerHTML = sorted.map(f => {
    const ext = '.' + f.filename.split('.').pop().toLowerCase();
    const icon = FILE_ICONS[ext] || '📄';
    const skipped = ['plan', 'foto', 'sonstig'].includes(f.category);

    return `
      <div class="classify-card ${skipped ? 'skipped' : ''}" data-file-id="${esc(f.file_id)}">
        <div class="classify-card-header">
          <span class="classify-card-icon">${icon}</span>
          <div class="classify-card-info">
            <span class="classify-card-name">${esc(f.filename)}</span>
            <span class="classify-card-meta">${fmtSize(f.size)} · ${esc(f.reason)}</span>
          </div>
        </div>
        <select class="classify-dropdown" onchange="updateClassification('${esc(f.file_id)}', this.value)">
          <option value="tuerliste" ${f.category === 'tuerliste' ? 'selected' : ''}>Türliste</option>
          <option value="spezifikation" ${f.category === 'spezifikation' ? 'selected' : ''}>Spezifikation</option>
          <option value="plan" ${f.category === 'plan' ? 'selected' : ''}>Plan (ignorieren)</option>
          <option value="foto" ${f.category === 'foto' ? 'selected' : ''}>Foto (ignorieren)</option>
          <option value="sonstig" ${f.category === 'sonstig' ? 'selected' : ''}>Sonstig (ignorieren)</option>
        </select>
      </div>
    `;
  }).join('');
}

function updateClassification(fileId, newCategory) {
  state.classificationOverrides[fileId] = newCategory;

  // Update visual
  const card = document.querySelector(`.classify-card[data-file-id="${fileId}"]`);
  if (card) {
    card.classList.toggle('skipped', ['plan', 'foto', 'sonstig'].includes(newCategory));
  }
}

async function startProjectAnalysis() {
  if (!state.projectId) return;

  showPanel('processing');
  setPill(3);
  setStep('upload', 'done', 'Dateien hochgeladen');
  setStep('ai', 'running', 'Excel wird geparst & KI normalisiert...');
  document.getElementById('processing-subtitle').textContent = 'Türliste wird analysiert...';

  try {
    // Analyze project
    const analysis = await api('/analyze/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: state.projectId,
        file_overrides: state.classificationOverrides,
      }),
    });
    state.analysis = analysis;

    const pos = analysis.requirements?.positionen?.length || 0;
    setStep('ai', 'done', `${pos} Türposition${pos !== 1 ? 'en' : ''} erkannt`);

    // Matching results
    const s = analysis.matching?.summary || {};
    setStep('match', 'done',
      `${s.matched_count || 0} erfüllbar · ${s.partial_count || 0} teilweise · ${s.unmatched_count || 0} nicht erfüllbar`
    );
    document.getElementById('processing-subtitle').textContent = 'Angebot & Gap-Report werden erstellt...';

    // Generate offer
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
    setPill(4);
    showResults(analysis, offer);

  } catch (err) {
    console.error('[Workflow] Project analysis failed:', err);
    showError(err.message);
    setPill(1);
  }
}

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
    setPill(4);
    showResults(analysis, offer);

  } catch (err) {
    console.error('[Workflow] Full workflow failed:', err);
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
      const matchedJson = esc(JSON.stringify(item.matched_products || []));
      return `
        <tr>
          <td><strong>${esc(item.position || pos.position || '—')}</strong></td>
          <td>${esc(item.beschreibung || pos.beschreibung || '—')}</td>
          <td>${esc(String(pos.menge || item.menge || 1))} ${esc(pos.einheit || 'Stk')}</td>
          <td>${esc(pos.tuertyp || '—')}</td>
          <td>${pos.brandschutz ? `<span class="tag tag-red">${esc(pos.brandschutz)}</span>` : '<span style="color:var(--gray-300)">—</span>'}</td>
          <td>${pos.einbruchschutz ? `<span class="tag tag-blue">${esc(pos.einbruchschutz)}</span>` : '<span style="color:var(--gray-300)">—</span>'}</td>
          <td style="font-size:.75rem;max-width:260px;">
            ${item.review_needed ? `<span class="review-badge" title="Confidence ${(item.confidence * 100).toFixed(0)}% – Status automatisch von '${esc(item.original_status || '')}' angepasst">Prüfen</span> ` : ''}
            ${renderMatchCriteria(item.match_criteria)}
            ${item.reason && (!item.match_criteria || !item.match_criteria.length)
              ? `<span style="color:var(--gray-500);">${esc(item.reason)}</span>` : ''}
          </td>
          <td class="action-cell">
            <button class="confirm-btn"
              data-position="${esc(item.position || pos.position || '')}"
              data-beschreibung="${esc(item.beschreibung || pos.beschreibung || '')}"
              data-tuertyp="${esc(pos.tuertyp || '')}"
              data-brandschutz="${esc(pos.brandschutz || '')}"
              data-einbruchschutz="${esc(pos.einbruchschutz || '')}"
              data-matched-product="${matchedJson}"
              data-status="${esc(item.status || cls)}"
              onclick="confirmMatch(this)" title="Match bestätigen">&#10003;</button>
            <button class="correction-btn"
              data-position="${esc(item.position || pos.position || '')}"
              data-beschreibung="${esc(item.beschreibung || pos.beschreibung || '')}"
              data-tuertyp="${esc(pos.tuertyp || '')}"
              data-brandschutz="${esc(pos.brandschutz || '')}"
              data-einbruchschutz="${esc(pos.einbruchschutz || '')}"
              data-breite="${esc(String(pos.breite || ''))}"
              data-hoehe="${esc(String(pos.hoehe || ''))}"
              data-status="${esc(item.status || cls)}"
              data-matched-product="${matchedJson}"
              onclick="openCorrection(this)">Korrektur</button>
          </td>
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
              <th>Türtyp</th><th>Brandschutz</th><th>Einbruchschutz</th><th>Hinweis</th><th>Aktion</th>
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
  state = {
    file: null, fileId: null, analysis: null, offer: null,
    uploadMode: state.uploadMode || 'folder',
    files: [], projectId: null, projectFiles: [],
    classificationOverrides: {},
  };

  clearFiles();
  clearFile();
  ['upload','ai','match','gen'].forEach(s => setStep(s, 'pending', 'Warte...'));

  document.getElementById('stat-grid').innerHTML = '';
  document.getElementById('download-grid').innerHTML = '';
  document.getElementById('positions-container').innerHTML = '';
  document.getElementById('match-bar').style.width = '0%';
  document.getElementById('classification-grid').innerHTML = '';
  document.getElementById('classify-summary').innerHTML = '';

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
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById(`pill-${i}`);
    if (!el) continue;
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
          <button class="confirm-btn" onclick="deleteHistory('${esc(a.id)}')" style="color:var(--red-600);background:var(--red-50);border-color:var(--red-100);">&times;</button>
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
      { num: summary.matched_count || 0, label: 'Erfüllbar', cls: 'green' },
      { num: summary.partial_count || 0, label: 'Teilweise', cls: 'orange' },
      { num: summary.unmatched_count || 0, label: 'Nicht erfüllbar', cls: 'red' },
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
      { items: match.matched || [], label: 'Erfüllbar', cls: 'green', icon: '&#10003;' },
      { items: match.partial || [], label: 'Teilweise', cls: 'orange', icon: '~' },
      { items: match.unmatched || [], label: 'Nicht erfüllbar', cls: 'red', icon: '&#10007;' },
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
            ? `<span style="color:var(--gray-500);">${esc(item.reason)}</span>` : ''
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
            <thead><tr><th>Pos.</th><th>Beschreibung</th><th>Menge</th><th>Türtyp</th><th>Kriterien</th></tr></thead>
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
  if (!confirm('Analyse mit aktuellen Feedback-Daten und Synonymen neu matchen?')) return;
  showToast('Rematch wird durchgeführt...');
  try {
    const result = await api(`/history/${historyId}/rematch`, { method: 'POST' });
    showToast(result.message);
    loadHistory();
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
  }
}

async function deleteHistory(historyId) {
  if (!confirm('Diese Analyse wirklich löschen?')) return;
  try {
    await api(`/history/${historyId}`, { method: 'DELETE' });
    showToast('Analyse gelöscht.');
    loadHistory();
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
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
    console.error(`[API] Error ${res.status} for ${path}:`, detail || msg);
    throw new Error(msg);
  }
  return res.json();
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

  // Show current match info
  let products = [];
  try { products = JSON.parse(d.matchedProduct || '[]'); } catch {}
  const currentProduct = products.length > 0
    ? Object.values(products[0]).join(' | ')
    : 'Kein Produkt zugeordnet';
  document.getElementById('correction-current-product').textContent = currentProduct;

  const reqParts = [d.beschreibung, d.tuertyp, d.brandschutz, d.einbruchschutz].filter(Boolean);
  document.getElementById('correction-requirement').textContent = reqParts.join(' | ') || '---';

  // Reset search
  document.getElementById('correction-search-input').value = '';
  document.getElementById('correction-results').innerHTML = '';
  document.getElementById('correction-note-input').value = '';
  document.getElementById('btn-save-correction').disabled = true;
  document.getElementById('btn-save-correction').textContent = 'Korrektur speichern';

  // Show modal
  document.getElementById('correction-modal').classList.remove('hidden');

  // Pre-populate search with tuertyp + brandschutz
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
    showToast('Korrektur gespeichert – wird beim nächsten Matching berücksichtigt.');
  } catch (err) {
    showToast(`Fehler: ${err.message}`);
    const btn = document.getElementById('btn-save-correction');
    btn.disabled = false;
    btn.textContent = 'Korrektur speichern';
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
// POSITIVE FEEDBACK (Bestätigen)
// ─────────────────────────────────────────────

async function confirmMatch(btn) {
  const d = btn.dataset;
  let products = [];
  try { products = JSON.parse(d.matchedProduct || '[]'); } catch {}
  if (!products.length) {
    showToast('Kein Produkt zum Bestätigen vorhanden.');
    return;
  }

  btn.disabled = true;
  btn.textContent = '...';

  try {
    await api('/feedback/confirm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requirement_text: [d.beschreibung, d.tuertyp, d.brandschutz, d.einbruchschutz]
          .filter(Boolean).join(' | '),
        requirement_fields: {
          tuertyp: d.tuertyp || null,
          brandschutz: d.brandschutz || null,
          einbruchschutz: d.einbruchschutz || null,
        },
        confirmed_product: {
          product_summary: Object.values(products[0]).join(' | '),
        },
        position_id: d.position || '?',
        match_status_was: d.status || 'unknown',
      }),
    });
    btn.textContent = '&#10003;';
    btn.classList.add('confirmed');
    showToast('Match bestätigt – wird beim nächsten Matching berücksichtigt.');
  } catch (err) {
    btn.disabled = false;
    btn.textContent = '&#10003;';
    showToast(`Fehler: ${err.message}`);
  }
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
// HEALTH CHECK
// ─────────────────────────────────────────────

async function checkServerHealth() {
  const chip = document.getElementById('server-status');
  const dot = chip.querySelector('.status-dot');
  const label = chip.querySelector('span');

  try {
    const res = await fetch(`${API.replace('/api', '')}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.api_key_set) {
      chip.style.background = '#ffedd5';
      chip.style.color = '#ea580c';
      chip.style.borderColor = '#fed7aa';
      dot.style.background = '#ea580c';
      label.textContent = 'API-Key fehlt!';
      showToast('ANTHROPIC_API_KEY ist nicht gesetzt. Analyse wird fehlschlagen.');
    } else {
      chip.style.background = '';
      chip.style.color = '';
      chip.style.borderColor = '';
      dot.style.background = '';
      label.textContent = 'Server verbunden';
    }
  } catch (err) {
    chip.style.background = '#fee2e2';
    chip.style.color = '#dc2626';
    chip.style.borderColor = '#fca5a5';
    dot.style.background = '#dc2626';
    dot.style.animation = 'none';
    label.textContent = 'Server nicht erreichbar';
    console.error('Health check failed:', err);
  }
}

// Run health check on load
checkServerHealth();
