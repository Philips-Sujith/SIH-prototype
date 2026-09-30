import React from 'react';
import { LayoutDashboard, Sliders, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import logoImg from '../assets/logo.png';

export default function Header({
  currentView,
  onViewChange
}) {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <header className="app-header">
      <div className="header-brand">
        <img src={logoImg} alt="Climate India Logo" className="header-logo-img" />
        <div className="brand-text">
          <div className="brand-title">
            Climate India
          </div>
          <span className="brand-subtitle">
            District Thermal Risk Early Warning • South India (TN, KL, KA)
          </span>
        </div>
      </div>

      <div className="header-actions">
        {/* Global Light/Dark Theme Switcher (Visible on both Public & Admin Views) */}
        <button
          id="theme-toggle-btn"
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
          aria-label={`Toggle theme, current is ${theme}`}
        >
          {isDark ? <Sun size={15} className="theme-icon sun" /> : <Moon size={15} className="theme-icon moon" />}
          <span>{isDark ? 'Light' : 'Dark'}</span>
        </button>

        <nav style={{ display: 'flex', gap: '8px' }}>
          <button
            id="nav-public-btn"
            className={`nav-toggle-btn ${currentView === 'public' ? 'active' : ''}`}
            onClick={() => onViewChange('public')}
            title="Switch to Public Heat Advisory Dashboard"
          >
            <LayoutDashboard size={15} />
            Public View
          </button>
          <button
            id="nav-admin-btn"
            className={`nav-toggle-btn ${currentView === 'admin' ? 'active' : ''}`}
            onClick={() => onViewChange('admin')}
            title="Switch to Municipal Admin Operations Dashboard"
          >
            <Sliders size={15} />
            Admin View
          </button>
        </nav>
      </div>
    </header>
  );
}
