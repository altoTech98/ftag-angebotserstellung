import { useState, useEffect, useRef } from 'react'
import { useApp } from '../context/AppContext'
import * as api from '../services/api'
import styles from '../styles/KatalogPage.module.css'

function fmtSize(b) {
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

export default function KatalogPage() {
  const { showToast } = useApp()
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  const loadInfo = async () => {
    setLoading(true)
    setError('')
    try {
      setInfo(await api.getCatalogInfo())
    } catch (err) {
      setError(`Katalog konnte nicht geladen werden: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadInfo() }, [])

  const handleUpload = async () => {
    if (!uploadFile) return
    setUploading(true)
    try {
      const result = await api.uploadCatalog(uploadFile)
      showToast(result.message)
      setUploadFile(null)
      if (fileRef.current) fileRef.current.value = ''
      loadInfo()
    } catch (err) {
      showToast(`Fehler: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f && f.name.toLowerCase().endsWith('.xlsx')) setUploadFile(f)
    else showToast('Nur .xlsx Dateien erlaubt.')
  }

  return (
    <div>
      <h1 className={styles.sectionTitle}>Produktkatalog</h1>
      <p className={styles.sectionDesc}>FTAG-Produktkatalog verwalten</p>

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Aktueller Katalog</h2>
        {loading && (
          <div className={styles.loadingState}>
            <div className={styles.miniSpinner} />
            <span>Katalog wird geladen...</span>
          </div>
        )}
        {error && <p className={styles.errorInline}>{error}</p>}
        {info && !loading && (
          <>
            <div className={styles.statGrid}>
              {[
                { num: info.total_products, label: 'Produkte gesamt', cls: styles.blue },
                { num: info.main_products, label: 'Hauptprodukte', cls: styles.green },
                { num: info.accessory_products, label: 'Zubehoer', cls: styles.orange },
                { num: info.categories, label: 'Kategorien', cls: '' },
              ].map((s, i) => (
                <div key={i} className={`${styles.statCard} ${s.cls}`}>
                  <div className={styles.statNum}>{s.num}</div>
                  <div className={styles.statLabel}>{s.label}</div>
                </div>
              ))}
            </div>
            {info.category_breakdown && (
              <div>
                <p className={styles.catLabel}>Kategorien</p>
                <div className={styles.catBadges}>
                  {Object.entries(info.category_breakdown).sort((a, b) => b[1] - a[1]).map(([name, count]) => (
                    <span key={name} className={styles.tagBlue}>{name}: {count}</span>
                  ))}
                </div>
                <p className={styles.catMeta}>
                  Datei: {info.filename} &middot; Letzte Aenderung: {info.last_modified}
                </p>
              </div>
            )}
          </>
        )}
      </div>

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Neuen Katalog hochladen</h2>
        <p className={styles.sectionDesc}>Excel-Datei (.xlsx) mit der aktuellen FTAG-Produktmatrix hochladen. Der bestehende Katalog wird ersetzt.</p>
        <div
          className={styles.dropZone}
          onDragOver={e => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <div className={styles.dropVisual}>
            <p className={styles.dropMain}>Produktkatalog (.xlsx) ablegen</p>
            <p className={styles.dropHint}>oder <span className={styles.dropLink}>auswaehlen</span></p>
          </div>
          <input ref={fileRef} type="file" accept=".xlsx" onChange={e => {
            const f = e.target.files[0]
            if (f) setUploadFile(f)
          }} hidden />
        </div>
        {uploadFile && (
          <div className={styles.filePreview}>
            <span>📗</span>
            <div className={styles.fileInfo}>
              <p className={styles.fileName}>{uploadFile.name}</p>
              <p className={styles.fileSize}>{fmtSize(uploadFile.size)}</p>
            </div>
            <button className={styles.removeBtn} onClick={() => { setUploadFile(null); if (fileRef.current) fileRef.current.value = '' }} title="Entfernen">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        )}
        <button className={styles.ctaBtn} onClick={handleUpload} disabled={!uploadFile || uploading}>
          {uploading ? 'Wird hochgeladen...' : 'Katalog hochladen'}
        </button>
      </div>
    </div>
  )
}
