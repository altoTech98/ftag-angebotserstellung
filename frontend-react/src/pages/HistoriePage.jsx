import { useState, useEffect, useCallback } from 'react'
import { getHistory, getHistoryDetail, rematchHistory as apiRematch, deleteHistory as apiDelete } from '../services/api'
import { useApp } from '../context/AppContext'
import styles from '../styles/HistoriePage.module.css'

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleDateString('de-CH', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function rateColor(rate) {
  if (rate >= 70) return 'Green'
  if (rate >= 40) return 'Orange'
  return 'Red'
}

function CriteriaTag({ criterion }) {
  const { status, kriterium, detail } = criterion
  let cls = styles.criteriaOk
  let icon = '\u2713'
  if (status === 'fehlt') { cls = styles.criteriaFehlt; icon = '\u2717' }
  else if (status === 'teilweise') { cls = styles.criteriaTeilweise; icon = '~' }

  return (
    <span className={`${styles.criteriaTag} ${cls}`} title={detail || ''}>
      {icon} {kriterium}
    </span>
  )
}

function PositionSection({ title, positions, colorCls }) {
  if (!positions || positions.length === 0) return null
  return (
    <div className={styles.positionsSection}>
      <div className={`${styles.sectionHeader} ${colorCls}`}>{title} ({positions.length})</div>
      <table className={styles.posTable}>
        <thead>
          <tr>
            <th>Pos.</th>
            <th>Beschreibung</th>
            <th>Menge</th>
            <th>Tuertyp</th>
            <th>Kriterien</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((item, i) => {
            const pos = item.original_position || item
            const criteria = item.match_criteria || item.kriterien || item.criteria || []
            return (
              <tr key={i}>
                <td><strong>{item.position || pos.position || i + 1}</strong></td>
                <td>{item.beschreibung || pos.beschreibung || '-'}</td>
                <td>{String(pos.menge || item.menge || 1)} {pos.einheit || 'Stk'}</td>
                <td>{pos.tuertyp || '-'}</td>
                <td>
                  <div className={styles.criteriaList}>
                    {criteria.map((c, j) => (
                      <CriteriaTag key={j} criterion={c} />
                    ))}
                    {item.reason && criteria.length === 0 && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '.8rem' }}>{item.reason}</span>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function DetailPanel({ detail, onClose }) {
  if (!detail) return null

  const match = detail.matching || {}
  const summary = match.summary || {}
  const matched = match.matched || []
  const partial = match.partial || []
  const unmatched = match.unmatched || []
  const total = summary.total_positions || (matched.length + partial.length + unmatched.length)

  return (
    <div className={styles.detailPanel}>
      <div className={styles.detailHeader}>
        <div>
          <div className={styles.detailTitle}>Analyse: {detail.filename || detail.id || 'Details'}</div>
          <div className={styles.detailSubtitle}>{detail.timestamp ? formatDate(detail.timestamp) : detail.date ? formatDate(detail.date) : ''}</div>
        </div>
        <button className={styles.closeBtn} onClick={onClose}>Schliessen</button>
      </div>

      <div className={styles.statGrid}>
        <div className={`${styles.statCard} ${styles.blue}`}>
          <div className={styles.statNum}>{total}</div>
          <div className={styles.statLabel}>Positionen</div>
        </div>
        <div className={`${styles.statCard} ${styles.green}`}>
          <div className={styles.statNum}>{matched.length}</div>
          <div className={styles.statLabel}>Erfuellbar</div>
        </div>
        <div className={`${styles.statCard} ${styles.orange}`}>
          <div className={styles.statNum}>{partial.length}</div>
          <div className={styles.statLabel}>Teilweise</div>
        </div>
        <div className={`${styles.statCard} ${styles.red}`}>
          <div className={styles.statNum}>{unmatched.length}</div>
          <div className={styles.statLabel}>Nicht erfuellbar</div>
        </div>
      </div>

      <PositionSection title="Erfuellbar" positions={matched} colorCls={styles.sectionHeaderGreen} />
      <PositionSection title="Teilweise erfuellbar" positions={partial} colorCls={styles.sectionHeaderOrange} />
      <PositionSection title="Nicht erfuellbar" positions={unmatched} colorCls={styles.sectionHeaderRed} />
    </div>
  )
}

export default function HistoriePage() {
  const { showToast } = useApp()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const loadHistory = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getHistory()
      setHistory(Array.isArray(data) ? data : data.analyses || data.history || [])
    } catch (err) {
      setError(`Historie konnte nicht geladen werden: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadHistory() }, [loadHistory])

  const handleDetail = async (id) => {
    setDetailLoading(true)
    try {
      const data = await getHistoryDetail(id)
      setDetail(data)
    } catch (err) {
      showToast(`Fehler beim Laden der Details: ${err.message}`)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleRematch = async (id) => {
    if (!window.confirm('Analyse erneut durchfuehren? Dies kann einige Minuten dauern.')) return
    try {
      await apiRematch(id)
      showToast('Neu-Matching gestartet')
      loadHistory()
    } catch (err) {
      showToast(`Fehler beim Neu-Matching: ${err.message}`)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Diesen Eintrag wirklich loeschen?')) return
    try {
      await apiDelete(id)
      showToast('Eintrag geloescht')
      if (detail && detail.id === id) setDetail(null)
      loadHistory()
    } catch (err) {
      showToast(`Fehler beim Loeschen: ${err.message}`)
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.sectionTitle}>Analyse-Historie</h1>
      <p className={styles.sectionDesc}>Vergangene Analysen einsehen, Details anzeigen oder erneut matchen</p>

      {loading && (
        <div className={styles.loadingState}>
          <div className={styles.miniSpinner} />
          <span>Historie wird geladen...</span>
        </div>
      )}

      {error && <div className={styles.errorInline}>{error}</div>}

      {!loading && !error && history.length === 0 && (
        <div className={styles.infoInline}>Noch keine Analysen vorhanden. Starten Sie eine neue Analyse auf der Analyse-Seite.</div>
      )}

      {!loading && !error && history.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Datum</th>
                <th>Datei</th>
                <th>Projekt</th>
                <th>Positionen</th>
                <th>Rate</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => {
                const matched = entry.matched_count || entry.matched || 0
                const partial = entry.partial_count || entry.partial || 0
                const unmatched = entry.unmatched_count || entry.unmatched || 0
                const rate = entry.match_rate != null ? entry.match_rate : (
                  (matched + partial + unmatched) > 0 ? Math.round((matched / (matched + partial + unmatched)) * 100) : 0
                )
                const rc = rateColor(rate)

                return (
                  <tr key={entry.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{entry.timestamp ? formatDate(entry.timestamp) : entry.date ? formatDate(entry.date) : '-'}</td>
                    <td>{entry.filename || entry.id || '-'}</td>
                    <td>{entry.filename || '-'}</td>
                    <td>
                      <div className={styles.tagGroup}>
                        {matched > 0 && <span className={`${styles.tag} ${styles.tagGreen}`}>{matched} erfuellt</span>}
                        {partial > 0 && <span className={`${styles.tag} ${styles.tagOrange}`}>{partial} teilweise</span>}
                        {unmatched > 0 && <span className={`${styles.tag} ${styles.tagRed}`}>{unmatched} offen</span>}
                      </div>
                    </td>
                    <td>
                      <span className={`${styles.tag} ${styles[`tag${rc}`]}`}>{rate}%</span>
                    </td>
                    <td>
                      <div className={styles.actionCell}>
                        <button className={styles.correctionBtn} onClick={() => handleDetail(entry.id)} disabled={detailLoading}>
                          Details
                        </button>
                        <button className={styles.correctionBtn} onClick={() => handleRematch(entry.id)}>
                          Neu matchen
                        </button>
                        <button className={styles.deleteBtn} onClick={() => handleDelete(entry.id)}>
                          Loeschen
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {detail && <DetailPanel detail={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}
