import { useState, useCallback, useEffect } from 'react'
import FileUpload from '../components/FileUpload'
import CorrectionModal from '../components/CorrectionModal'
import { useApp } from '../context/AppContext'
import { useSSE } from '../hooks/useSSE'
import * as api from '../services/api'
import { mapV2ResultToDisplay } from '../utils/v2ResultMapper'
import styles from '../styles/AnalysePage.module.css'
import corrStyles from '../styles/CorrectionModal.module.css'

const MAX_FILE_SIZE = 200 * 1024 * 1024

const STEP_NAMES_SINGLE = ['Datei hochladen', 'Tuerliste parsen', 'Produkt-Matching', 'Machbarkeitsanalyse erstellen']
const STEP_NAMES_FOLDER = ['Dateien hochladen & klassifizieren', 'Tuerlisten parsen & zusammenfuehren', 'Produkt-Matching', 'Machbarkeitsanalyse erstellen']
const STEP_IDS = ['upload', 'ai', 'match', 'gen']

function StepIndicator({ step }) {
  return (
    <div className={styles.stepsIndicator}>
      {[1, 2, 3].map((n, i) => (
        <div key={n} style={{ display: 'contents' }}>
          {i > 0 && <div className={styles.pillConnector} />}
          <div className={`${styles.pill} ${step > n ? styles.pillDone : ''} ${step === n ? styles.pillActive : ''}`}>
            <span className={styles.pillNum}>{n}</span>
            <span className={styles.pillLabel}>{['Upload', 'Analyse', 'Ergebnis'][i]}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function ProcessingPanel({ steps, subtitle, positionProgress }) {
  return (
    <div className={styles.processingCard}>
      <div className={styles.processingHeader}>
        <div className={styles.processingSpinner} />
        <div>
          <h2 className={styles.cardTitle}>Verarbeitung laeuft</h2>
          <p className={styles.cardDesc}>{subtitle}</p>
        </div>
      </div>
      {positionProgress && positionProgress.total > 0 && (
        <div style={{ padding: '0 1.25rem .75rem', fontSize: '.8125rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.25rem' }}>
            <span>Position {positionProgress.current || '...'}</span>
            <span>{positionProgress.done}/{positionProgress.total}</span>
          </div>
          <div style={{ background: 'var(--bg-hover)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
            <div style={{ background: 'var(--primary)', height: '100%', width: `${(positionProgress.done / positionProgress.total) * 100}%`, transition: 'width .3s ease' }} />
          </div>
        </div>
      )}
      <div className={styles.stepsList}>
        {steps.map(s => (
          <div key={s.id} className={styles.stepItem}>
            <div className={`${styles.stepDot} ${styles[s.state] || ''}`}>
              {s.state === 'done' && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>}
              {s.state === 'running' && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><circle cx="12" cy="12" r="3" fill="white"/></svg>}
              {s.state === 'error' && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>}
            </div>
            <div>
              <p className={styles.stepName}>{s.name}</p>
              <p className={styles.stepStatus}>{s.status}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PositionDetailModal({ item, onClose }) {
  const pos = item.original_position || item
  const statusMap = {
    matched: { label: 'Erfuellbar (Bestaetigt)', cls: styles.tagGreen },
    partial: { label: 'Teilweise (Unsicher)', cls: styles.tagOrange },
    unmatched: { label: 'Nicht erfuellbar (Abgelehnt)', cls: styles.tagRed },
  }
  const st = statusMap[item._status] || { label: item._status, cls: '' }

  const fields = [
    ['Tuer-Nr', pos.positions_nr || pos.position || item.position],
    ['Beschreibung', pos.positions_bezeichnung || item.beschreibung || pos.beschreibung],
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
    ['Oberflaeche', pos.oberflaechentyp || pos.oberflaeche],
    ['Glasausschnitt', pos.glasausschnitt || pos.verglasung],
    ['Fluegel', pos.fluegel_anzahl || pos.anzahl_fluegel],
  ].filter(([, v]) => v != null && v !== '' && v !== '\u2014')

  const products = item.matched_products || []
  const criteria = item.match_criteria || []
  const missingInfo = item.missing_info || []
  const gapItems = item.gap_items || []

  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [onClose])

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h3 className={styles.modalTitle}>Position {item.position || pos.positions_nr || pos.position || '\u2014'}</h3>
          <button className={styles.modalClose} onClick={onClose}>&times;</button>
        </div>
        <div className={styles.modalBody}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginBottom: '1rem' }}>
            <span className={`${styles.tag} ${st.cls}`}>{st.label}</span>
            {item.confidence && <span style={{ color: 'var(--text-faint)', fontSize: '.8125rem' }}>Konfidenz: {(item.confidence * 100).toFixed(0)}%</span>}
            <span style={{ color: 'var(--text-faint)', fontSize: '.8125rem' }}>Kategorie: {item.category || '\u2014'}</span>
          </div>

          <h4 className={styles.subHeading}>Kundenanforderung</h4>
          <div className={styles.detailFields}>
            {fields.map(([label, value]) => (
              <div key={label} className={styles.detailField}>
                <span className={styles.detailFieldLabel}>{label}</span>
                <span className={styles.detailFieldValue}>{String(value)}</span>
              </div>
            ))}
          </div>

          <h4 className={styles.subHeading} style={{ marginTop: '1rem' }}>
            FTAG Produkt{products.length > 1 ? `e (${products.length})` : ''}
          </h4>
          {products.length === 0 ? (
            <p style={{ color: 'var(--text-muted)' }}>Kein passendes Produkt gefunden</p>
          ) : (
            products.map((p, i) => (
              <div key={i} className={styles.detailFields} style={i > 0 ? { marginTop: '.5rem' } : undefined}>
                {Object.entries(p).filter(([k, v]) => v != null && v !== '' && !k.startsWith('_')).slice(0, 10).map(([k, v]) => (
                  <div key={k} className={styles.detailField}>
                    <span className={styles.detailFieldLabel}>{k}</span>
                    <span className={styles.detailFieldValue}>{String(v)}</span>
                  </div>
                ))}
              </div>
            ))
          )}

          {criteria.length > 0 && (
            <>
              <h4 className={styles.subHeading} style={{ marginTop: '1rem' }}>Kriterien</h4>
              <div className={styles.criteriaList}>
                {criteria.map((c, i) => {
                  const cls = c.status === 'ok' ? styles.criteriaOk : c.status === 'fehlt' ? styles.criteriaFehlt : styles.criteriaTeilweise
                  const icon = c.status === 'ok' ? '\u2713' : c.status === 'fehlt' ? '\u2717' : '~'
                  return (
                    <div key={i} className={`${styles.criteriaItem} ${cls}`}>
                      <span>{icon} <strong>{c.kriterium || ''}</strong></span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '.8rem' }}>{c.detail || ''}</span>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {missingInfo.length > 0 && (
            <>
              <h4 className={styles.subHeading} style={{ marginTop: '1rem', color: 'var(--warning)' }}>Was fehlt</h4>
              <div className={styles.criteriaList}>
                {missingInfo.map((mi, i) => (
                  <div key={i} className={`${styles.criteriaItem} ${styles.criteriaTeilweise}`}>
                    <span><strong>{mi.feld || ''}</strong></span>
                    <span style={{ fontSize: '.8rem' }}>Braucht: {mi.benoetigt || ''} | Hat: {mi.vorhanden || ''}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {gapItems.length > 0 && missingInfo.length === 0 && (
            <>
              <h4 className={styles.subHeading} style={{ marginTop: '1rem', color: 'var(--warning)' }}>Abweichungen</h4>
              <div className={styles.criteriaList}>
                {gapItems.map((gi, i) => {
                  const severityColor = gi.severity === 'kritisch' ? '#ef4444' : gi.severity === 'major' ? '#f59e0b' : '#eab308'
                  const v2Gap = (item._v2?.gaps?.gaps || []).find(g => (g.dimension || '').toLowerCase() === (gi.field || gi.feld || '').toLowerCase())
                  return (
                    <div key={i} className={`${styles.criteriaItem} ${styles.criteriaTeilweise}`}>
                      <span>
                        {gi.severity && (
                          <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: '4px', fontSize: '.7rem', fontWeight: 600, color: '#fff', background: severityColor, marginRight: '.4rem', verticalAlign: 'middle' }}>
                            {gi.severity}
                          </span>
                        )}
                        <strong>{gi.field || gi.feld || ''}</strong>
                      </span>
                      <span style={{ fontSize: '.8rem' }}>{gi.description || gi.detail || ''}</span>
                      {v2Gap?.kundenvorschlag && (
                        <span style={{ fontSize: '.75rem', color: 'var(--text-muted)', marginTop: '.25rem', display: 'block' }}>Vorschlag: {v2Gap.kundenvorschlag}</span>
                      )}
                      {v2Gap?.technischer_hinweis && (
                        <span style={{ fontSize: '.75rem', color: 'var(--text-faint)', display: 'block' }}>Technisch: {v2Gap.technischer_hinweis}</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {/* Adversarial Validation section */}
          {item._v2?.adversarial && (() => {
            const adv = item._v2.adversarial
            const statusBadge = {
              bestaetigt: { label: 'Bestaetigt', cls: styles.tagGreen },
              unsicher: { label: 'Unsicher', cls: styles.tagOrange },
              abgelehnt: { label: 'Abgelehnt', cls: styles.tagRed },
            }
            const badge = statusBadge[adv.validation_status] || { label: adv.validation_status, cls: '' }
            return (
              <>
                <h4 className={styles.subHeading} style={{ marginTop: '1rem' }}>Adversarial Validierung</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginBottom: '.5rem' }}>
                  <span className={`${styles.tag} ${badge.cls}`}>{badge.label}</span>
                  <span style={{ fontSize: '.8125rem', color: 'var(--text-muted)' }}>
                    Angepasste Konfidenz: {(adv.adjusted_confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {adv.resolution_reasoning && (
                  <div style={{ padding: '.5rem .75rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius)', fontSize: '.8125rem', color: 'var(--text-muted)', marginBottom: '.5rem' }}>
                    {adv.resolution_reasoning}
                  </div>
                )}
                {adv.per_dimension_cot && adv.per_dimension_cot.length > 0 && (
                  <div className={styles.detailFields}>
                    {adv.per_dimension_cot.map((dim, i) => {
                      const color = dim.score >= 0.95 ? '#22c55e' : dim.score >= 0.60 ? '#f59e0b' : '#ef4444'
                      return (
                        <div key={i} className={styles.detailField}>
                          <span className={styles.detailFieldLabel} style={{ display: 'flex', alignItems: 'center', gap: '.4rem' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
                            {dim.dimension}
                          </span>
                          <span className={styles.detailFieldValue}>
                            <span style={{ fontWeight: 600, color }}>{(dim.score * 100).toFixed(0)}%</span>
                            {dim.reasoning && <span style={{ marginLeft: '.5rem', fontSize: '.75rem', color: 'var(--text-muted)' }}>{dim.reasoning}</span>}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </>
            )
          })()}

          {/* Gap Alternatives section */}
          {item._v2?.gaps?.alternativen?.length > 0 && (
            <>
              <h4 className={styles.subHeading} style={{ marginTop: '1rem' }}>Alternative Produkte</h4>
              <div className={styles.detailFields}>
                {item._v2.gaps.alternativen.map((alt, i) => (
                  <div key={i} className={styles.detailField}>
                    <span className={styles.detailFieldLabel}>{alt.produkt_name || alt.produkt_id}</span>
                    <span className={styles.detailFieldValue}>
                      {alt.teilweise_deckung != null ? `${(alt.teilweise_deckung * 100).toFixed(0)}% Deckung` : '\u2014'}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          {item.reason && (
            <div style={{ marginTop: '.75rem', padding: '.5rem .75rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius)', fontSize: '.8125rem', color: 'var(--text-muted)' }}>
              {item.reason}
            </div>
          )}
        </div>
        <div className={styles.modalFooter}>
          <button className={`${styles.ctaBtn} ${styles.secondary} ${styles.slim}`} onClick={onClose}>Schliessen</button>
        </div>
      </div>
    </div>
  )
}

function ResultsPanel({ analysis, offer, onReset }) {
  const [detailItem, setDetailItem] = useState(null)
  const [correctionItem, setCorrectionItem] = useState(null)
  const match = analysis.matching || {}
  const summary = match.summary || {}

  const sections = [
    { items: match.matched || [], status: 'matched', label: 'Erfuellbar (Bestaetigt)', cls: 'green', icon: '\u2713' },
    { items: match.partial || [], status: 'partial', label: 'Teilweise (Unsicher)', cls: 'orange', icon: '\u26A0' },
    { items: match.unmatched || [], status: 'unmatched', label: 'Nicht erfuellbar (Abgelehnt)', cls: 'red', icon: '\u2717' },
  ]

  const stats = [
    { num: summary.total_positions || 0, label: 'Positionen gesamt', cls: 'blue' },
    { num: summary.matched_count || 0, label: 'Erfuellbar', cls: 'green' },
    { num: summary.partial_count || 0, label: 'Teilweise', cls: 'orange' },
    { num: summary.unmatched_count || 0, label: 'Nicht erfuellbar', cls: 'red' },
  ]

  const rate = summary.match_rate || 0

  return (
    <div>
      <div className={styles.resultsTopbar}>
        <button className={styles.resetBtn} onClick={onReset}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4"/>
          </svg>
          Neue Analyse starten
        </button>
      </div>

      <div className={styles.statGrid}>
        {stats.map((s, i) => (
          <div key={i} className={`${styles.statCard} ${styles[s.cls]}`} style={{ animationDelay: `${i * 80}ms` }}>
            <div className={styles.statNum}>{s.num}</div>
            <div className={styles.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className={styles.matchRateCard}>
        <div className={styles.matchRateHeader}>
          <span className={styles.matchRateLabel}>Erfuellungsrate</span>
          <span className={styles.matchRateValue}>{rate}%</span>
        </div>
        <div className={styles.matchBarBg}>
          <div className={styles.matchBarFill} style={{ width: `${rate}%` }} />
        </div>
        <p className={styles.matchRateSub}>
          {summary.matched_count || 0} erfuellbar
          {(summary.partial_count || 0) > 0 ? ` | ${summary.partial_count} teilweise` : ''}
          {(summary.unmatched_count || 0) > 0 ? ` | ${summary.unmatched_count} nicht erfuellbar` : ''}
        </p>
      </div>

      {offer?.has_result && offer.result_id && (
        <div className={styles.downloadSection}>
          <p className={styles.downloadTitle}>Dokumente herunterladen</p>
          <div className={styles.downloadGrid}>
            <div className={styles.dlGroup}>
              <div className={styles.dlGroupTitle}>Machbarkeitsanalyse + GAP-Report</div>
              <button
                className={`${styles.dlBtn} ${styles.dlExcel}`}
                onClick={() => api.downloadV2Result(offer.result_id)}
              >
                <span>Excel herunterladen</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {sections.map(({ items, status, label, cls, icon }) => {
        if (!items.length) return null
        return (
          <div key={status} className={styles.positionsSection}>
            <div className={`${styles.sectionHeader} ${styles[`header${cls.charAt(0).toUpperCase() + cls.slice(1)}`]}`}>
              <span>{icon}</span>
              <span>{label}</span>
              <span className={styles.sectionBadge}>{items.length}</span>
            </div>
            <div className={styles.tableWrap}>
              <table className={styles.dataTable}>
                <thead><tr>
                  <th>Pos.</th><th>Beschreibung</th><th>Menge</th>
                  <th>Brandschutz</th><th>FTAG Produkt</th><th>Kategorie</th><th>Begruendung</th><th>Aktion</th>
                </tr></thead>
                <tbody>
                  {items.map((item, i) => {
                    const pos = item.original_position || item
                    const products = item.matched_products || []
                    let ftag = '\u2014'
                    if (products.length > 0) {
                      const names = products.map(p =>
                        p['\u0054\u00fcrblatt / Verglasungsart / Rollkasten'] ||
                        p['Tuerblatt / Verglasungsart / Rollkasten'] || ''
                      ).filter(n => n)
                      ftag = [...new Set(names)].join(' / ') || '\u2014'
                    }
                    const missingInfo = item.missing_info || []
                    return (
                      <tr key={i} className={styles.clickableRow} onClick={() => setDetailItem({ ...item, _status: status })}>
                        <td><strong>{item.position || pos.positions_nr || pos.position || '\u2014'}</strong></td>
                        <td>
                          {item.beschreibung || pos.positions_bezeichnung || pos.beschreibung || pos.tuertyp || '\u2014'}
                          {status === 'partial' && missingInfo.length > 0 && (
                            <div style={{ marginTop: '.25rem' }}>
                              {missingInfo.map((mi, j) => (
                                <span key={j} className={styles.criteriaTagInline} title={`${mi.benoetigt || ''} vs ${mi.vorhanden || ''}`}>
                                  {mi.feld || ''}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td>{pos.menge || item.menge || 1}</td>
                        <td>{pos.brandschutz || '\u2014'}</td>
                        <td style={{ fontSize: '.8rem' }} title={ftag}>{ftag.substring(0, 60)}{ftag.length > 60 ? '...' : ''}</td>
                        <td>{item.category || '\u2014'}</td>
                        <td style={{ fontSize: '.75rem' }}>
                          {item.confidence ? <span style={{ color: 'var(--text-faint)' }}>{(item.confidence * 100).toFixed(0)}% </span> : ''}
                          {item.reason ? <span style={{ color: 'var(--text-muted)' }}>{item.reason.substring(0, 60)}</span> : ''}
                        </td>
                        <td>
                          <button
                            className={corrStyles.correctionBtn}
                            onClick={(e) => { e.stopPropagation(); setCorrectionItem({ ...item, _status: status }) }}
                          >
                            Korrigieren
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}

      {detailItem && <PositionDetailModal item={detailItem} onClose={() => setDetailItem(null)} />}

      {correctionItem && (
        <CorrectionModal
          item={correctionItem}
          onClose={() => setCorrectionItem(null)}
          onSaved={() => setCorrectionItem(null)}
        />
      )}
    </div>
  )
}

export default function AnalysePage() {
  const { showToast } = useApp()
  const { pollJob, cleanup } = useSSE()
  const [panel, setPanel] = useState('upload')
  const [currentStep, setCurrentStep] = useState(1)
  const [subtitle, setSubtitle] = useState('Bitte warten...')
  const [errorMsg, setErrorMsg] = useState('')
  const [filesData, setFilesData] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [offer, setOffer] = useState(null)
  const [positionProgress, setPositionProgress] = useState(null)
  const [steps, setSteps] = useState(
    STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' }))
  )

  const updateStep = useCallback((id, state, status) => {
    setSteps(prev => prev.map(s => s.id === id ? { ...s, state, status } : s))
  }, [])

  const startUpload = async () => {
    if (!filesData) return
    if (filesData.type === 'single') {
      if (filesData.file.size > MAX_FILE_SIZE) { showToast('Datei ist zu gross (max. 200 MB)'); return }
      await runSingleWorkflow(filesData.file)
    } else {
      const tooBig = filesData.files.find(f => f.size > MAX_FILE_SIZE)
      if (tooBig) { showToast(`Datei "${tooBig.name}" ist zu gross (max. 200 MB)`); return }
      await runFolderWorkflow(filesData.files)
    }
  }

  /** V2 progress callback shared by both workflows */
  const handleV2Progress = useCallback((progressStr) => {
    try {
      const info = JSON.parse(progressStr)
      const stageMap = { extraction: 1, matching: 2, adversarial: 2, gap_analyse: 2, plausibility: 3 }
      setCurrentStep(stageMap[info.stage] || 2)
      setSubtitle(info.message || 'Analyse laeuft...')
      if (info.positions_total) {
        setPositionProgress({ done: info.positions_done, total: info.positions_total, current: info.current_position })
      } else {
        setPositionProgress(null)
      }
      if (info.stage === 'matching' || info.stage === 'adversarial' || info.stage === 'gap_analyse') {
        updateStep('ai', 'done', 'Tuerlisten geparst')
        updateStep('match', 'running', info.message)
      }
    } catch {
      setSubtitle(progressStr || 'Analyse laeuft...')
      setPositionProgress(null)
    }
  }, [updateStep])

  const runSingleWorkflow = async (file) => {
    setPanel('processing')
    setCurrentStep(2)
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' })))
    updateStep('upload', 'running', 'Datei wird hochgeladen...')
    setSubtitle('Datei wird hochgeladen...')

    try {
      // Step 1: V2 single-file upload
      const up = await api.uploadSingleV2(file)
      if (!up.tender_id) throw new Error('Upload fehlgeschlagen: keine tender_id erhalten')
      updateStep('upload', 'done', `${up.filename} hochgeladen`)

      // Step 2: V2 analysis
      updateStep('ai', 'running', 'Tuerliste wird geparst...')
      setSubtitle('Tuerliste wird analysiert...')
      const { job_id } = await api.startV2Analysis(up.tender_id)
      const result = await pollJob(job_id, handleV2Progress, '/v2/analyze/status/')

      // Transform v2 result to display structure
      const mapped = mapV2ResultToDisplay(result)
      setAnalysis(mapped)

      const pos = mapped.matching.summary.total_positions || 0
      updateStep('ai', 'done', `${pos} Tuerpositionen erkannt`)
      const s = mapped.matching.summary
      updateStep('match', 'done', `${s.matched_count || 0} erfuellbar, ${s.partial_count || 0} teilweise, ${s.unmatched_count || 0} nicht erfuellbar`)

      // Step 3: V2 offer generation
      setSubtitle('Machbarkeitsanalyse wird erstellt...')
      updateStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...')
      const { job_id: offerJobId } = await api.generateV2Offer(mapped.analysis_id)
      const offerResult = await pollJob(offerJobId, (p) => setSubtitle(p || 'Ergebnis wird erstellt...'), '/offer/status/')
      setOffer({ ...offerResult, result_id: offerResult.result_id || mapped.analysis_id })
      updateStep('gen', 'done', offerResult.message || 'Machbarkeitsanalyse erstellt')

      setCurrentStep(3)
      setPanel('results')
    } catch (err) {
      console.error('[Workflow] Failed:', err)
      setErrorMsg(err.message)
      setPanel('error')
      setCurrentStep(1)
    }
  }

  const runFolderWorkflow = async (files) => {
    setPanel('processing')
    setCurrentStep(2)
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_FOLDER[i], state: 'pending', status: 'Warte...' })))
    updateStep('upload', 'running', `${files.length} Dateien werden hochgeladen...`)
    setSubtitle('Dateien werden hochgeladen...')

    try {
      // Step 1: V2 folder upload
      const uploadResult = await api.uploadFolderV2(files)
      const fileNames = (uploadResult.files || []).map(f => f.filename).join(', ')
      updateStep('upload', 'done', `${uploadResult.total_files} Dateien hochgeladen: ${fileNames}`)

      // Step 2: V2 analysis
      updateStep('ai', 'running', 'Tuerlisten werden geparst...')
      setSubtitle('Projekt wird analysiert...')
      const { job_id } = await api.startV2Analysis(uploadResult.tender_id)
      const result = await pollJob(job_id, handleV2Progress, '/v2/analyze/status/')

      // Transform v2 result to display structure
      const mapped = mapV2ResultToDisplay(result)
      setAnalysis(mapped)

      const pos = mapped.matching.summary.total_positions || 0
      updateStep('ai', 'done', `${pos} Tuerpositionen erkannt`)
      const s = mapped.matching.summary
      updateStep('match', 'done', `${s.matched_count || 0} erfuellbar, ${s.partial_count || 0} teilweise, ${s.unmatched_count || 0} nicht erfuellbar`)

      // Step 3: V2 offer generation
      setSubtitle('Machbarkeitsanalyse wird erstellt...')
      updateStep('gen', 'running', 'Machbarkeitsanalyse wird erstellt...')
      const { job_id: offerJobId } = await api.generateV2Offer(mapped.analysis_id)
      const offerResult = await pollJob(offerJobId, (p) => setSubtitle(p || 'Ergebnis wird erstellt...'), '/offer/status/')
      setOffer({ ...offerResult, result_id: offerResult.result_id || mapped.analysis_id })
      updateStep('gen', 'done', offerResult.message || 'Machbarkeitsanalyse erstellt')

      setCurrentStep(3)
      setPanel('results')
    } catch (err) {
      console.error('[FolderWorkflow] Failed:', err)
      setErrorMsg(err.message)
      setPanel('error')
      setCurrentStep(1)
    }
  }

  const resetAll = () => {
    cleanup()
    setPanel('upload')
    setCurrentStep(1)
    setFilesData(null)
    setAnalysis(null)
    setOffer(null)
    setErrorMsg('')
    setPositionProgress(null)
    setSteps(STEP_IDS.map((id, i) => ({ id, name: STEP_NAMES_SINGLE[i], state: 'pending', status: 'Warte...' })))
  }

  return (
    <div>
      <StepIndicator step={currentStep} />

      {panel === 'upload' && (
        <div>
          <h1 className={styles.sectionTitle}>Tuerliste hochladen</h1>
          <p className={styles.sectionDesc}>Einzelne Datei oder kompletten Projektordner hochladen und automatisch analysieren lassen.</p>
          <FileUpload onFilesReady={setFilesData} />
          <button className={styles.ctaBtn} onClick={startUpload} disabled={!filesData}>
            Hochladen &amp; Analysieren
          </button>
        </div>
      )}

      {panel === 'processing' && <ProcessingPanel steps={steps} subtitle={subtitle} positionProgress={positionProgress} />}

      {panel === 'results' && analysis && <ResultsPanel analysis={analysis} offer={offer} onReset={resetAll} />}

      {panel === 'error' && (
        <div className={styles.errorCard}>
          <div className={styles.errorIconBig}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="32" height="32">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <h2 className={styles.errorTitle}>Fehler aufgetreten</h2>
          <div className={styles.errorMsg}>{errorMsg}</div>
          <p className={styles.errorHint}>Browser-Konsole (F12) zeigt weitere Details.</p>
          <button className={`${styles.ctaBtn} ${styles.secondary}`} onClick={resetAll}>Erneut versuchen</button>
        </div>
      )}
    </div>
  )
}
