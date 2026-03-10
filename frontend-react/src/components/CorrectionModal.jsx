import { useState, useEffect, useRef, useCallback } from 'react'
import { searchProducts, saveV2Feedback } from '../services/api'
import { useApp } from '../context/AppContext'
import styles from '../styles/CorrectionModal.module.css'

export default function CorrectionModal({ item, onClose, onSaved }) {
  const { showToast } = useApp()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [searched, setSearched] = useState(false)
  const debounceRef = useRef(null)
  const inputRef = useRef(null)

  const pos = item.original_position || item

  // Build requirement display
  const requirementDisplay = [
    pos.beschreibung || item.beschreibung,
    pos.tuertyp,
    pos.brandschutz,
    pos.einbruchschutz || pos.widerstandsklasse,
  ].filter(Boolean).join(' | ')

  // Build current product display
  const products = item.matched_products || []
  const currentProductDisplay = products.length > 0
    ? Object.entries(products[0])
        .filter(([k, v]) => v != null && v !== '' && !k.startsWith('_'))
        .slice(0, 6)
        .map(([, v]) => String(v))
        .join(' | ')
    : 'Kein Produkt zugeordnet'

  // Search function
  const doSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setResults([])
      setSearched(false)
      return
    }
    try {
      const data = await searchProducts(q.trim())
      setResults(data.products || data || [])
      setSearched(true)
    } catch (err) {
      console.error('[CorrectionModal] Search failed:', err)
      setResults([])
      setSearched(true)
    }
  }, [])

  // Auto-search on open
  useEffect(() => {
    const initial = [pos.tuertyp, pos.brandschutz].filter(Boolean).join(' ')
    if (initial) {
      setQuery(initial)
      doSearch(initial)
    }
    if (inputRef.current) inputRef.current.focus()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced search on query change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      doSearch(query)
    }, 350)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, doSearch])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Save feedback
  const handleSave = async () => {
    if (!selectedProduct || saving) return
    setSaving(true)

    const body = {
      positions_nr: item.position || pos.positions_nr || pos.position || '?',
      requirement_summary: [
        pos.positions_bezeichnung || pos.beschreibung || item.beschreibung,
        pos.tuertyp,
        pos.brandschutz,
      ].filter(Boolean).join(' | '),
      original_produkt_id: item._v2?.match?.bester_match?.produkt_id || '',
      original_konfidenz: item.confidence || 0,
      corrected_produkt_id: String(selectedProduct._row_index || ''),
      corrected_produkt_name: selectedProduct._summary || '',
      correction_reason: note || 'Manuelle Korrektur',
    }

    try {
      await saveV2Feedback(body)
      showToast('Korrektur gespeichert')
      onClose()
      if (onSaved) onSaved()
    } catch (err) {
      console.error('[CorrectionModal] Save failed:', err)
      showToast('Fehler: ' + (err.message || 'Korrektur konnte nicht gespeichert werden'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h3 className={styles.modalTitle}>Produkt-Zuordnung korrigieren</h3>
          <button className={styles.modalClose} onClick={onClose}>&times;</button>
        </div>

        <div className={styles.modalBody}>
          {/* Current requirement */}
          <div className={styles.correctionSection}>
            <div className={styles.correctionLabel}>Kundenanforderung</div>
            <div className={styles.correctionValue}>
              {requirementDisplay || '\u2014'}
            </div>
          </div>

          {/* Current product */}
          <div className={styles.correctionSection}>
            <div className={styles.correctionLabel}>Aktuelle Zuordnung</div>
            <div className={styles.correctionValue}>
              {currentProductDisplay}
            </div>
          </div>

          {/* Dimensional confidence breakdown */}
          {(() => {
            const dimScores = item._v2?.dimension_scores || item._v2?.match?.bester_match?.dimension_scores
            if (!dimScores || dimScores.length === 0) return null
            return (
              <div className={styles.correctionSection}>
                <div className={styles.correctionLabel}>Dimensionale Bewertung</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.4rem' }}>
                  {dimScores.map((d, i) => {
                    const score = typeof d.score === 'number' ? d.score : 0
                    const color = score >= 0.95 ? '#22c55e' : score >= 0.60 ? '#f59e0b' : '#ef4444'
                    const bg = score >= 0.95 ? 'rgba(34,197,94,.12)' : score >= 0.60 ? 'rgba(245,158,11,.12)' : 'rgba(239,68,68,.12)'
                    return (
                      <span
                        key={i}
                        title={d.begruendung || d.reasoning || ''}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: '.35rem',
                          padding: '.25rem .6rem', borderRadius: '999px',
                          background: bg, fontSize: '.8rem', fontWeight: 500,
                        }}
                      >
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: color, flexShrink: 0 }} />
                        <span style={{ color: 'var(--text-secondary)' }}>{d.dimension}:</span>
                        <span style={{ fontWeight: 600, color }}>{(score * 100).toFixed(0)}%</span>
                      </span>
                    )
                  })}
                </div>
              </div>
            )
          })()}

          {/* Search */}
          <div className={styles.correctionSection}>
            <div className={styles.correctionLabel}>Richtiges Produkt suchen</div>
            <div className={styles.searchWrap}>
              <span className={styles.searchIcon}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </span>
              <input
                ref={inputRef}
                type="text"
                className={styles.searchInput}
                placeholder="Produkt suchen..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            {/* Results */}
            <div className={styles.correctionResults}>
              {results.length === 0 && searched && (
                <div className={styles.noResults}>Keine Produkte gefunden</div>
              )}
              {results.length === 0 && !searched && (
                <div className={styles.noResults}>Suchbegriff eingeben...</div>
              )}
              {results.map((product, i) => {
                const isSelected = selectedProduct && selectedProduct._row_index === product._row_index
                const details = Object.entries(product)
                  .filter(([k, v]) => v != null && v !== '' && !k.startsWith('_'))
                  .slice(0, 6)
                return (
                  <div
                    key={product._row_index ?? i}
                    className={`${styles.productItem} ${isSelected ? styles.productItemSelected : ''}`}
                    onClick={() => setSelectedProduct(product)}
                  >
                    <div className={styles.productSummary}>
                      {product._summary || `Produkt ${product._row_index || i + 1}`}
                    </div>
                    {details.length > 0 && (
                      <div className={styles.productDetails}>
                        {details.map(([k, v]) => (
                          <span key={k} className={`${styles.tag} ${styles.tagBlue}`}>
                            {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Note */}
          <div className={styles.correctionSection}>
            <div className={styles.correctionLabel}>Anmerkung (optional)</div>
            <input
              type="text"
              className={styles.noteInput}
              placeholder="z.B. Grund fuer Korrektur..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
        </div>

        <div className={styles.modalFooter}>
          <button
            className={`${styles.ctaBtn} ${styles.secondary}`}
            onClick={onClose}
            disabled={saving}
          >
            Abbrechen
          </button>
          <button
            className={styles.ctaBtn}
            onClick={handleSave}
            disabled={!selectedProduct || saving}
          >
            {saving ? 'Wird gespeichert...' : 'Korrektur speichern'}
          </button>
        </div>
      </div>
    </div>
  )
}
