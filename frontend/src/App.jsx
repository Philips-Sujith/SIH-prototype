import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PublicDashboard from './components/PublicDashboard';
import AdminDashboard from './components/AdminDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { ThemeProvider } from './context/ThemeContext';

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000';

function AppContent() {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [districtsMeta, setDistrictsMeta] = useState(null);
  const basePath = import.meta.env.BASE_URL || '/';
  const getAdminPath = () => `${basePath}admin`.replace(/\/{2,}/g, '/');
  const getRootPath = () => basePath;

  const [currentView, setCurrentView] = useState(() => {
    return window.location.pathname.includes('/admin') || window.location.hash.includes('admin') ? 'admin' : 'public';
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [toastMessage, setToastMessage] = useState(null);

  // Sync URL changes
  useEffect(() => {
    const handlePopState = () => {
      setCurrentView(window.location.pathname.includes('/admin') || window.location.hash.includes('admin') ? 'admin' : 'public');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleViewChange = (view) => {
    setCurrentView(view);
    const newPath = view === 'admin' ? getAdminPath() : getRootPath();
    if (window.location.pathname !== newPath) {
      window.history.pushState({}, '', newPath);
    }
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // Fetch initial live 83-district data
  useEffect(() => {
    fetch(`${API_BASE}/api/districts`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to retrieve districts`);
        return res.json();
      })
      .then((data) => {
        const loadedDistricts = data.districts || data.zones || [];
        setZones(loadedDistricts);
        setDistrictsMeta({
          total: data.total || loadedDistricts.length,
          states: data.states || { 'Tamil Nadu': 38, 'Kerala': 14, 'Karnataka': 31 },
          weatherSource: data.weather_source || 'Open-Meteo',
          boundarySource: data.boundary_source || 'Government Geospatial Datasets'
        });

        // Default to Chennai, or Bengaluru Urban, or highest risk
        const defaultDistrict = 
          loadedDistricts.find((z) => z.id === 'chennai') || 
          loadedDistricts.find((z) => z.id === 'bengaluru_urban') || 
          loadedDistricts[0];

        setSelectedZone(defaultDistrict);
        setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
        setLoading(false);
      })
      .catch((err) => {
        console.error("Districts fetch failed:", err);
        setError("Unable to connect to ClimateGuard India backend feed. Ensure the backend server is running and accessible.");
        setLoading(false);
      });
  }, []);

  const handleRefreshTelemetry = async () => {
    const res = await fetch(`${API_BASE}/api/districts?refresh=true`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const loadedDistricts = data.districts || data.zones || [];
    setZones(loadedDistricts);
    if (selectedZone) {
      const updatedSelected = loadedDistricts.find((d) => d.id === selectedZone.id) || loadedDistricts[0];
      setSelectedZone(updatedSelected);
    }
    setLastUpdated('Updated just now');
    return true;
  };

  return (
    <div className="app-container">
      {/* Sleek App Header with Route Toggle & Live Status */}
      <Header
        currentView={currentView}
        onViewChange={handleViewChange}
        lastUpdated={lastUpdated}
        totalDistricts={districtsMeta?.total || zones.length}
      />

      {/* Main Content Area */}
      <main className="main-layout">
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '16px' }}>
            <div className="pulse-dot" style={{ width: '20px', height: '20px' }}></div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Retrieving live telemetry for 83 districts across Tamil Nadu, Kerala, and Karnataka...
            </div>
          </div>
        ) : error ? (
          <div className="dashboard-card" style={{ padding: '36px', textAlign: 'center', maxWidth: '600px', margin: '40px auto' }}>
            <AlertTriangle size={36} style={{ color: 'var(--risk-danger)', margin: '0 auto 12px' }} />
            <h2 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Telemetry Stream Unavailable</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px' }}>{error}</p>
            <button 
              className="action-btn-primary" 
              onClick={() => window.location.reload()}
              style={{ margin: '0 auto' }}
            >
              Retry Connection
            </button>
          </div>
        ) : (
          <>
            {currentView === 'public' ? (
              <ErrorBoundary>
                <PublicDashboard
                  zones={zones}
                  selectedZone={selectedZone}
                  onSelectZone={setSelectedZone}
                  apiBase={API_BASE}
                  districtsMeta={districtsMeta}
                  onRefreshTelemetry={handleRefreshTelemetry}
                  lastUpdated={lastUpdated}
                />
              </ErrorBoundary>
            ) : (
              <ErrorBoundary>
                <AdminDashboard
                  zones={zones}
                  selectedZone={selectedZone}
                  onSelectZone={setSelectedZone}
                  apiBase={API_BASE}
                  onShowToast={showToast}
                  districtsMeta={districtsMeta}
                  onRefreshTelemetry={handleRefreshTelemetry}
                  lastUpdated={lastUpdated}
                />
              </ErrorBoundary>
            )}
          </>
        )}
      </main>

      {/* Toast Notification Container */}
      {toastMessage && (
        <div className="toast-container">
          <div className="toast">
            <CheckCircle2 size={18} style={{ color: 'var(--risk-low)' }} />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

