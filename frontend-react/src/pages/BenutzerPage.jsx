import { useState, useEffect, useCallback } from 'react'
import { getUsers, createUser, deleteUser } from '../services/api'
import { useApp } from '../context/AppContext'
import s from '../styles/BenutzerPage.module.css'

export default function BenutzerPage() {
  const { showToast } = useApp()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getUsers()
      setUsers(data.users || data || [])
    } catch (err) {
      setError(err.message || 'Fehler beim Laden der Benutzer')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])

  const handleDelete = async (email) => {
    if (!window.confirm(`Benutzer "${email}" wirklich entfernen?`)) return
    try {
      await deleteUser(email)
      showToast('Benutzer entfernt')
      loadUsers()
    } catch (err) {
      showToast(err.message || 'Fehler beim Entfernen')
    }
  }

  return (
    <div className={s.page}>
      <h1 className={s.sectionTitle}>Benutzerverwaltung</h1>
      <p className={s.sectionDesc}>Benutzer hinzufuegen, entfernen und Rollen verwalten</p>

      <div className={s.glassCard}>
        <div className={s.cardHeader}>
          <span className={s.cardTitle}>Benutzer</span>
          <button className={s.ctaBtn} onClick={() => setModalOpen(true)}>+ Benutzer hinzufuegen</button>
        </div>

        {loading && (
          <div className={s.loadingState}>
            <div className={s.miniSpinner} />
            <span>Benutzer werden geladen...</span>
          </div>
        )}

        {error && <div className={s.errorInline}>{error}</div>}

        {!loading && !error && users.length === 0 && (
          <div className={s.loadingState}>
            <span>Keine Benutzer vorhanden.</span>
          </div>
        )}

        {!loading && !error && users.length > 0 && (
          <div className={s.tableWrap}>
            <table className={s.dataTable}>
              <thead>
                <tr>
                  <th>E-Mail</th>
                  <th>Rolle</th>
                  <th>Erstellt</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.email}>
                    <td>{u.email}</td>
                    <td>
                      <span className={`${s.tag} ${u.role === 'admin' ? s.tagBlue : s.tagGreen}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleDateString('de-CH') : '-'}</td>
                    <td>
                      <button className={s.deleteBtn} onClick={() => handleDelete(u.email)}>Entfernen</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modalOpen && (
        <AddUserModal
          onClose={() => setModalOpen(false)}
          onCreated={() => {
            setModalOpen(false)
            showToast('Benutzer erstellt')
            loadUsers()
          }}
        />
      )}
    </div>
  )
}

function AddUserModal({ onClose, onCreated }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!email || !password) {
      setError('E-Mail und Passwort sind erforderlich.')
      return
    }
    if (password.length < 6) {
      setError('Passwort muss mindestens 6 Zeichen lang sein.')
      return
    }

    setSubmitting(true)
    try {
      await createUser(email, password, role)
      onCreated()
    } catch (err) {
      setError(err.message || 'Fehler beim Erstellen')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={s.modalOverlay} onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className={s.modalCard}>
        <div className={s.modalHeader}>
          <span className={s.modalTitle}>Benutzer hinzufuegen</span>
          <button className={s.modalCloseBtn} onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className={s.modalBody}>
            {error && <div className={s.loginError}>{error}</div>}
            <div className={s.formGroup}>
              <label className={s.formLabel}>E-Mail</label>
              <input
                className={s.formInput}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="benutzer@example.com"
                autoFocus
              />
            </div>
            <div className={s.formGroup}>
              <label className={s.formLabel}>Passwort</label>
              <input
                className={s.formInput}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
              />
            </div>
            <div className={s.formGroup}>
              <label className={s.formLabel}>Rolle</label>
              <select
                className={s.formInput}
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </div>
          </div>
          <div className={s.modalFooter}>
            <button type="button" className={s.secondaryBtn} onClick={onClose}>Abbrechen</button>
            <button type="submit" className={s.ctaBtn} disabled={submitting}>
              {submitting ? 'Erstelle...' : 'Erstellen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
