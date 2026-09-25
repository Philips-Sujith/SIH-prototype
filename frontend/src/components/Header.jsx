import React, { useState, useEffect } from 'react';
import { ShieldAlert, LayoutDashboard, Sliders, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Header({
  currentView,
  onViewChange,
  lastUpdated,
  totalDistricts = 83,
  dataState,
  cacheAgeSeconds
}) {
  const { theme, toggleTheme, isDark } = useTheme();
  const [internalStatus, setInternalStatus] = useState({
    dataState: 'CACHED',
    cacheAgeSeconds: 0
  });

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || '';
    fetch(`${apiBase}/api/districts`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data) {
          setInternalStatus({
            dataState: data.data_state || (data.districts?.length > 0 ? 'CACHED' : 'UNAVAILABLE'),
            cacheAgeSeconds: data.cache_age_seconds || 0
          });
        }
      })
      .catch(() => {
        setInternalStatus({ dataState: 'UNAVAILABLE', cacheAgeSeconds: 0 });
      });
  }, [lastUpdated]);

  const activeState = dataState || internalStatus.dataState;
  const activeAge = cacheAgeSeconds ?? internalStatus.cacheAgeSeconds;

  const renderStatus = () => {
    if (activeState === 'LIVE') {
      return (
        <div className="live-indicator">
          <span className="pulse-dot"></span>
          <span>● LIVE</span>
          {lastUpdated && <span style={{ opacity: 0.6 }}>• {lastUpdated}</span>}
        </div>
      );
    }
    if (activeState === 'CACHED') {
      const mins = Math.max(1, Math.round((activeAge || 0) / 60));
      return (
        <div className="live-indicator">
          <span style={{ color: '#f59e0b', fontSize: '0.85rem' }}>◐</span>
          <span>CACHED · Updated {mins} min ago</span>
        </div>
      );
    }
    return (
      <div className="live-indicator">
        <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>○</span>
        <span>CONNECTING / UNAVAILABLE</span>
      </div>
    );
  };

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
        {renderStatus()}

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
