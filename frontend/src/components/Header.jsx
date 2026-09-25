import React from 'react';
import { ShieldAlert, LayoutDashboard, Sliders, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Header({ currentView, onViewChange, lastUpdated, totalDistricts = 83 }) {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="logo-badge">
          <ShieldAlert size={22} />
        </div>
        <div className="brand-text">
          <div className="brand-title">
            ClimateGuard
            <span className="country-tag">India</span>
          </div>
          <span className="brand-subtitle">
            District Thermal Risk Early Warning • South India (TN, KL, KA)
          </span>
        </div>
      </div>

      <div className="header-actions">
        <div className="live-indicator">
          <span className="pulse-dot"></span>
          <span>LIVE METEO FEED • {totalDistricts} DISTRICTS</span>
          {lastUpdated && <span style={{ opacity: 0.6 }}>• {lastUpdated}</span>}
        </div>

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
