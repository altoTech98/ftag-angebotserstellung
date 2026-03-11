import { useState, useRef, useCallback } from 'react'
import styles from '../styles/FileUpload.module.css'

const ALLOWED_EXTS = ['xlsx','xls','xlsm','pdf','docx','doc','txt','jpg','jpeg','png','bmp','tif','tiff','dwg','dxf']
const FILE_ICONS = {
  pdf: '\u{1F4D5}', xlsx: '\u{1F4D7}', xls: '\u{1F4D7}', xlsm: '\u{1F4D7}',
  docx: '\u{1F4D8}', doc: '\u{1F4D8}', txt: '\u{1F4C4}',
  jpg: '\u{1F5BC}', jpeg: '\u{1F5BC}', png: '\u{1F5BC}', bmp: '\u{1F5BC}',
  tif: '\u{1F5BC}', tiff: '\u{1F5BC}', dwg: '\u{1F4D0}', dxf: '\u{1F4D0}',
}

function fmtSize(b) {
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

function getExt(name) { return name.split('.').pop().toLowerCase() }
function getIcon(name) { return FILE_ICONS[getExt(name)] || '\u{1F4C4}' }

function readDirectory(dirEntry) {
  return new Promise(resolve => {
    const files = []
    const reader = dirEntry.createReader()
    function readBatch() {
      reader.readEntries(entries => {
        if (entries.length === 0) { resolve(files); return }
        const promises = []
        for (const entry of entries) {
          if (entry.isFile) {
            promises.push(new Promise(res => entry.file(f => { files.push(f); res() })))
          } else if (entry.isDirectory) {
            promises.push(readDirectory(entry).then(sub => files.push(...sub)))
          }
        }
        Promise.all(promises).then(readBatch)
      })
    }
    readBatch()
  })
}

export default function FileUpload({ onFilesReady }) {
  const [singleFile, setSingleFile] = useState(null)
  const [multiFiles, setMultiFiles] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)

  const filterValid = (files) =>
    files.filter(f => ALLOWED_EXTS.includes(getExt(f.name)))

  const processFiles = useCallback((files) => {
    const valid = filterValid(files)
    if (valid.length === 0) return
    if (valid.length === 1) {
      setSingleFile(valid[0])
      setMultiFiles([])
      onFilesReady?.({ type: 'single', file: valid[0] })
    } else {
      setMultiFiles(valid)
      setSingleFile(null)
      onFilesReady?.({ type: 'multi', files: valid })
    }
  }, [onFilesReady])

  const handleDrop = useCallback(async (e) => {
    e.preventDefault()
    setDragOver(false)
    const items = e.dataTransfer.items
    const directFiles = []

    if (items && items.length > 0) {
      const folderPromises = []
      for (let i = 0; i < items.length; i++) {
        const entry = items[i].webkitGetAsEntry?.() || items[i].getAsEntry?.()
        if (entry?.isDirectory) {
          folderPromises.push(readDirectory(entry))
        } else if (items[i].kind === 'file') {
          const f = items[i].getAsFile()
          if (f) directFiles.push(f)
        }
      }
      if (folderPromises.length > 0) {
        const results = await Promise.all(folderPromises)
        processFiles(directFiles.concat(results.flat()))
        return
      }
    }

    if (directFiles.length === 0) {
      directFiles.push(...Array.from(e.dataTransfer.files))
    }
    processFiles(directFiles)
  }, [processFiles])

  const clearAll = () => {
    setSingleFile(null)
    setMultiFiles([])
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
    onFilesReady?.(null)
  }

  return (
    <div>
      <div
        className={`${styles.dropZone} ${dragOver ? styles.dragOver : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div className={styles.dropVisual}>
          <div className={styles.dropCircle}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <p className={styles.dropMain}>Dateien oder Ordner hier ablegen</p>
          <p className={styles.dropHint}>Excel, PDF, Word &middot; max. 500 MB</p>
          <div className={styles.uploadButtons}>
            <button
              type="button"
              className={styles.uploadBtnFolder}
              onClick={e => { e.stopPropagation(); folderInputRef.current?.click() }}
            >
              Ordner auswaehlen
            </button>
            <button
              type="button"
              className={styles.uploadBtnFile}
              onClick={e => { e.stopPropagation(); fileInputRef.current?.click() }}
            >
              Dateien auswaehlen
            </button>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.xlsm,.pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.tif,.tiff,.dwg,.dxf"
          multiple
          onChange={e => processFiles(Array.from(e.target.files))}
          hidden
        />
        <input
          ref={folderInputRef}
          type="file"
          webkitdirectory=""
          directory=""
          onChange={e => processFiles(Array.from(e.target.files))}
          hidden
        />
      </div>

      {singleFile && (
        <div className={styles.filePreview}>
          <span className={styles.fileIcon}>{getIcon(singleFile.name)}</span>
          <div className={styles.fileInfo}>
            <p className={styles.fileName}>{singleFile.name}</p>
            <p className={styles.fileSize}>{fmtSize(singleFile.size)}</p>
          </div>
          <button className={styles.removeBtn} onClick={clearAll} title="Entfernen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      )}

      {multiFiles.length > 0 && (
        <div className={styles.filesPreview}>
          <div className={styles.filesHeader}>
            <span className={styles.filesCount}>{multiFiles.length} Dateien</span>
            <span className={styles.filesTotalSize}>{fmtSize(multiFiles.reduce((s, f) => s + f.size, 0))}</span>
            <button className={styles.removeBtn} onClick={clearAll} title="Alle entfernen">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="14" height="14">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div className={styles.filesList}>
            {multiFiles.map((f, i) => (
              <div key={i} className={styles.fileItem}>
                <span className={styles.fileItemIcon}>{getIcon(f.name)}</span>
                <span className={styles.fileItemName} title={f.name}>{f.name}</span>
                <span className={styles.fileItemSize}>{fmtSize(f.size)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
