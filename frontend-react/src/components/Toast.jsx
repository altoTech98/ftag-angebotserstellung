import { useApp } from '../context/AppContext'
import styles from '../styles/Toast.module.css'

export default function Toast() {
  const { toast } = useApp()
  if (!toast) return null
  return <div className={styles.toast}>{toast}</div>
}
