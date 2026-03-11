import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import StatusBadge from './StatusBadge'
import styles from '../styles/Header.module.css'

export default function Header() {
  const { user, logout } = useAuth()

  const navItems = [
    { to: '/analyse', label: 'Analyse' },
    { to: '/katalog', label: 'Katalog' },
    { to: '/historie', label: 'Historie' },
  ]
  if (user?.role === 'admin') {
    navItems.push({ to: '/benutzer', label: 'Benutzer' })
  }

  return (
    <header className={styles.header}>
      <div className={styles.brand}>Frank Tueren AG</div>
      <nav className={styles.nav}>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `${styles.navItem} ${isActive ? styles.active : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className={styles.status}>
        <StatusBadge />
        <button className={styles.logoutBtn} onClick={logout} title="Abmelden">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </header>
  )
}
