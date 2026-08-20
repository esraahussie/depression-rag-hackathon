import { NavLink } from 'react-router-dom'
import LanguageToggle from './LanguageToggle'
import { useLanguage } from '../i18n'

export default function Layout({ children }) {
  const { t } = useLanguage()

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z"
                fill="currentColor"
              />
              <circle cx="12" cy="10" r="1.5" fill="white" />
            </svg>
          </div>
          <div>
            <h1 className="brand-name">MindCare</h1>
            <p className="brand-tagline">{t.tagline}</p>
          </div>
        </div>

        <LanguageToggle />

        <nav className="sidebar-nav" aria-label="Main navigation">
          <NavLink to="/chat" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M8 10h8M8 14h5M21 12c0 3.866-3.582 7-8 7-.847 0-1.654-.12-2.4-.34L3 21l1.5-5.2C3.56 14.6 3 13.35 3 12c0-3.866 3.582-7 8-7s8 3.134 8 7z"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {t.chat}
          </NavLink>
          <NavLink to="/phq9" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            PHQ-9
          </NavLink>
          <NavLink to="/gad7" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M12 11v4m0-8h.01"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            GAD-7
          </NavLink>
          <NavLink to="/epds" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 13h6M9 17h4"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            EPDS
          </NavLink>
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" aria-hidden="true" />
          {t.assistantStatus}
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="mobile-header">
          <div className="mobile-brand">
            <span className="brand-icon-sm">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M12 4c-2.8 0-4.8 2-4.8 4.8 0 3.2 2.4 4.4 4.8 7.2 2.4-2.8 4.8-4 4.8-7.2C16.8 6 14.8 4 12 4z"
                  fill="currentColor"
                />
              </svg>
            </span>
            MindCare
          </div>
          <LanguageToggle />
          <nav className="mobile-nav" aria-label="Mobile navigation">
            <NavLink to="/chat" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}>
              {t.chat}
            </NavLink>
            <NavLink to="/phq9" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}>
              PHQ-9
            </NavLink>
            <NavLink to="/gad7" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}>
              GAD-7
            </NavLink>
            <NavLink to="/epds" className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}>
              EPDS
            </NavLink>
          </nav>
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  )
}
