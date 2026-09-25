import React, { useState, useEffect, useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
  Send,
  CheckSquare,
  Square,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ArrowUpRight,
  BellRing,
  Radio,
  Database,
  ThermometerSun,
  ShieldCheck
} from 'lucide-react';
import IndiaHeatMap from './IndiaHeatMap';
import { useTheme } from '../context/ThemeContext';

// Register Chart.js modules
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Admin-Only Telegram Alert Test Profiles (Temporary testing control for daytime heat templates)
const ALERT_TEST_PROFILES = {
  caution: {
    category: 'Caution',
    temp: 34.0,
    wbgt: 28.5,
    time_window: '12:00 PM – 3:00 PM',
    peak_start: '12:00 PM',
    peak_end: '3:00 PM'
  },
  danger: {
    category: 'Danger',
    temp: 37.0,
    wbgt: 30.5,
    time_window: '12:00 PM – 4:00 PM',
    peak_start: '12:00 PM',
    peak_end: '4:00 PM'
  },
  extreme: {
    category: 'Extreme Danger',
    label: 'Extreme',
    temp: 40.0,
    wbgt: 33.0,
    time_window: '11:00 AM – 4:00 PM',
    peak_start: '11:00 AM',
    peak_end: '4:00 PM'
  },
  severe: {
    category: 'Severe',
    label: 'Severe',
    temp: 43.0,
    wbgt: 36.0,
    time_window: '10:00 AM – 5:00 PM',
    peak_start: '10:00 AM',
    peak_end: '5:00 PM'
  }
};

export default function AdminDashboard({
  zones,
  selectedZone,
  onSelectZone,
  apiBase,
  onShowToast
}) {
  const { isDark } = useTheme();
  const [selectedState, setSelectedState] = useState('all');
  const [forecastData, setForecastData] = useState([]);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [alertsList, setAlertsList] = useState([]);
  const [alertLogs, setAlertLogs] = useState([]);
  const [isAlerting, setIsAlerting] = useState(false);
  const [processingAlertId, setProcessingAlertId] = useState(null);
  // Admin-Only Alert Test Mode ('live' by default, never persistent or applied to public telemetry)
  const [alertTestMode, setAlertTestMode] = useState('live');

  // Synthetic Mortality Analogue State
  const [mortalityAnalogue, setMortalityAnalogue] = useState(null);
  const [mortalityLoading, setMortalityLoading] = useState(false);
  const [mortalityMeta, setMortalityMeta] = useState(null);
  const [showMethodology, setShowMethodology] = useState(false);

  // Municipal action checklist
  const [actions, setActions] = useState({
    coolingCenters: false,
    shiftWorkHours: false,
    flagGridLoad: false
  });

  const toggleAction = (key) => {
    setActions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Filter districts based on state selection
  const filteredDistricts = useMemo(() => {
    if (selectedState === 'all') return zones;
    return zones.filter((z) => z.state === selectedState);
  }, [zones, selectedState]);

  // Group high-risk districts by severity tier (Section 8)
  const highRiskGroups = useMemo(() => {
    const severe = [];
    const extreme = [];
    const danger = [];

    zones.forEach((d) => {
      const cat = d.category || '';
      if (cat === 'Severe' || d.wbgt >= 35.0) severe.push(d);
      else if (cat === 'Extreme Danger' || d.wbgt >= 32.0) extreme.push(d);
      else if (cat === 'Danger' || d.wbgt >= 30.0) danger.push(d);
    });

    return { severe, extreme, danger };
  }, [zones]);

  // Load traceable alert records from backend
  const fetchAlerts = () => {
    fetch(`${apiBase}/api/alerts`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load alerts");
        return res.json();
      })
      .then((data) => {
        setAlertsList(data.alerts || []);
      })
      .catch((err) => console.warn("Notice: Local alerts fallback:", err));
  };

  useEffect(() => {
    fetchAlerts();
  }, [apiBase]);

  // Load dataset transparency metadata on mount
  useEffect(() => {
    fetch(`${apiBase}/api/mortality/status`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          setMortalityMeta(data.metadata);
        }
      })
      .catch((err) => console.warn("Notice: Mortality status check skipped:", err));
  }, [apiBase]);

  // Fetch forecast data and historical synthetic mortality analogue when selectedZone changes
  useEffect(() => {
    if (!selectedZone) return;

    let isCurrent = true;
    setForecastLoading(true);
    setMortalityLoading(true);

    fetch(`${apiBase}/api/districts/${selectedZone.id}/forecast`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load forecast");
        return res.json();
      })
      .then((data) => {
        if (isCurrent) {
          setForecastData(data.forecast || []);
          setForecastLoading(false);
        }
      })
      .catch((err) => {
        console.warn("Forecast fetch error:", err);
        if (isCurrent) setForecastLoading(false);
      });

    // Fetch multi-variable historical synthetic analogue
    fetch(`${apiBase}/api/mortality/analogue/${selectedZone.id}?top_n=5`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load mortality analogue");
        return res.json();
      })
      .then((data) => {
        if (isCurrent) {
          setMortalityAnalogue(data);
          setMortalityLoading(false);
        }
      })
      .catch((err) => {
        console.warn("Notice: Mortality analogue fetch fallback:", err);
        if (isCurrent) {
          setMortalityAnalogue(null);
          setMortalityLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedZone, apiBase]);

  // Handle State filter change
  const handleStateChange = (e) => {
    const newState = e.target.value;
    setSelectedState(newState);
    const matching = newState === 'all' ? zones : zones.filter((z) => z.state === newState);
    if (matching.length > 0) {
      const stillValid = matching.some((z) => z.id === selectedZone?.id);
      if (!stillValid) {
        onSelectZone(matching[0]);
      }
    }
  };

  // Handle District selector change
  const handleDistrictChange = (e) => {
    const dId = e.target.value;
    const match = zones.find((z) => z.id === dId);
    if (match) {
      onSelectZone(match);
      if (selectedState !== 'all' && match.state !== selectedState) {
        setSelectedState(match.state);
      }
    }
  };

  // Alert Action: Acknowledge
  const handleAcknowledgeAlert = async (alertId) => {
    setProcessingAlertId(alertId);
    try {
      const res = await fetch(`${apiBase}/api/alerts/${alertId}/acknowledge`, { method: 'POST' });
      if (!res.ok) throw new Error("Failed to acknowledge alert");
      const data = await res.json();
      setAlertsList((prev) => prev.map((a) => (a.alert_id === alertId ? data.alert : a)));
      onShowToast(`Alert ${alertId} acknowledged.`);
    } catch (err) {
      console.error("Acknowledge error:", err);
      onShowToast("Unable to acknowledge alert.");
    } finally {
      setProcessingAlertId(null);
    }
  };

  // Alert Action: Escalate
  const handleEscalateAlert = async (alertId) => {
    setProcessingAlertId(alertId);
    try {
      const res = await fetch(`${apiBase}/api/alerts/${alertId}/escalate`, { method: 'POST' });
      if (!res.ok) throw new Error("Failed to escalate alert");
      const data = await res.json();
      setAlertsList((prev) => prev.map((a) => (a.alert_id === alertId ? data.alert : a)));
      onShowToast(`⚠ Alert escalated to SDMA Commissioner.`);
    } catch (err) {
      console.error("Escalation error:", err);
      onShowToast("Unable to escalate alert.");
    } finally {
      setProcessingAlertId(null);
    }
  };

  // Alert Action: Send Public Alert
  const handleSendPublicAlert = async (alertId) => {
    setProcessingAlertId(alertId);
    try {
      const res = await fetch(`${apiBase}/api/alerts/${alertId}/send-public`, { method: 'POST' });
      if (!res.ok) throw new Error("Failed to dispatch public alert");
      const data = await res.json();
      setAlertsList((prev) => prev.map((a) => (a.alert_id === alertId ? data.alert : a)));
      onShowToast(`📢 Confirmed public alert broadcast dispatched.`);
    } catch (err) {
      console.error("Public alert dispatch error:", err);
      onShowToast("Unable to dispatch public alert.");
    } finally {
      setProcessingAlertId(null);
    }
  };

  // Broadcast real multilingual alert to Telegram channel (Live Data or Test Mode)
  const handleGenerateInstantAlert = async () => {
    if (!selectedZone || isAlerting) return;
    const districtName = selectedZone.district || selectedZone.name;
    const isTest = alertTestMode !== 'live' && ALERT_TEST_PROFILES[alertTestMode];

    // Confirmation step with distinct test-alert notice to prevent accidental live broadcasts
    const confirmMessage = isTest
      ? `[TEST ALERT — NOT LIVE WEATHER]\nSend real test alert to Telegram channel for ${districtName}?\n\nTest Level: ${ALERT_TEST_PROFILES[alertTestMode].label || ALERT_TEST_PROFILES[alertTestMode].category}\nPeak Temp: ~${ALERT_TEST_PROFILES[alertTestMode].temp}°C • WBGT: ~${ALERT_TEST_PROFILES[alertTestMode].wbgt}°C\nPeak Window: ${ALERT_TEST_PROFILES[alertTestMode].time_window}`
      : `Send real alert to Telegram channel for ${districtName}?`;

    const confirmed = window.confirm(confirmMessage);
    if (!confirmed) return;

    setIsAlerting(true);

    try {
      const response = await fetch(`${apiBase}/api/alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          district_id: selectedZone.id,
          zone_id: selectedZone.id,
          test_mode: alertTestMode
        })
      });

      const result = await response.json();
      if (response.ok && result.sent) {
        setAlertLogs((prev) => [result, ...prev]);
        const testNotice = isTest ? ` (Test Mode: ${ALERT_TEST_PROFILES[alertTestMode].label || ALERT_TEST_PROFILES[alertTestMode].category})` : '';
        onShowToast(`Telegram alert broadcast sent for ${result.district_name || districtName}${testNotice}!`);
        fetchAlerts();
      } else {
        const errorDesc = result.error || (result.detail ? (typeof result.detail === 'string' ? result.detail : JSON.stringify(result.detail)) : 'Failed to send alert to Telegram');
        const failedEntry = {
          ...result,
          sent: false,
          status: 'failed',
          is_test_mode: isTest,
          test_mode: alertTestMode,
          district_name: result.district_name || districtName,
          zone_name: districtName,
          state: selectedZone.state,
          thermal_category: isTest ? (ALERT_TEST_PROFILES[alertTestMode].label || ALERT_TEST_PROFILES[alertTestMode].category) : selectedZone.category,
          wbgt: isTest ? ALERT_TEST_PROFILES[alertTestMode].wbgt : selectedZone.wbgt,
          timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC',
          error: errorDesc,
          message: result.message || `[SEND FAILED — ${errorDesc}]`
        };
        setAlertLogs((prev) => [failedEntry, ...prev]);
        onShowToast(`Telegram broadcast failed: ${errorDesc}`);
      }
    } catch (err) {
      console.error("Alert generation error:", err);
      const failedEntry = {
        sent: false,
        status: 'failed',
        is_test_mode: isTest,
        test_mode: alertTestMode,
        district_name: districtName,
        zone_name: districtName,
        state: selectedZone.state,
        thermal_category: isTest ? (ALERT_TEST_PROFILES[alertTestMode].label || ALERT_TEST_PROFILES[alertTestMode].category) : selectedZone.category,
        wbgt: isTest ? ALERT_TEST_PROFILES[alertTestMode].wbgt : selectedZone.wbgt,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC',
        error: err.message || 'Network connection failed',
        message: `[SEND FAILED — ${err.message || 'Network failure'}]`
      };
      setAlertLogs((prev) => [failedEntry, ...prev]);
      onShowToast(`Alert error: ${err.message || 'Network failure'}`);
    } finally {
      setIsAlerting(false);
    }
  };

  // Chart configuration
  const chartLabels = forecastData.map((d) => {
    const parts = d.date.split('-');
    if (parts.length === 3) {
      const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
      return dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    }
    return d.date;
  });

  const chartData = {
    labels: chartLabels,
    datasets: [
      {
        label: 'WBGT (°C) - Wet-Bulb Globe Temp',
        data: forecastData.map((d) => d.wbgt),
        borderColor: isDark ? '#f97316' : '#ea580c',
        backgroundColor: isDark ? 'rgba(249, 115, 22, 0.12)' : 'rgba(234, 88, 12, 0.08)',
        borderWidth: 2.5,
        pointBackgroundColor: isDark ? '#f97316' : '#ea580c',
        pointRadius: 4,
        tension: 0.35,
        fill: true,
      },
      {
        label: 'Max Ambient Air Temp (°C)',
        data: forecastData.map((d) => d.temp_max),
        borderColor: isDark ? '#38bdf8' : '#0284c7',
        borderWidth: 2,
        borderDash: [4, 4],
        pointBackgroundColor: isDark ? '#38bdf8' : '#0284c7',
        pointRadius: 3.5,
        tension: 0.3,
        fill: false,
      },
      {
        label: 'UTCI (°C) - Universal Thermal Climate Index',
        data: forecastData.map((d) => d.utci ?? d.wbgt),
        borderColor: isDark ? '#c084fc' : '#7e22ce',
        borderWidth: 2,
        pointBackgroundColor: isDark ? '#c084fc' : '#7e22ce',
        pointRadius: 3.5,
        tension: 0.35,
        fill: false,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: { top: 12, bottom: 6, left: 6, right: 12 }
    },
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: {
          color: isDark ? '#94a3b8' : '#334155',
          font: { family: 'Inter', size: 11, weight: '600' },
          boxWidth: 10,
          boxHeight: 10,
          padding: 14,
          usePointStyle: true,
          pointStyle: 'circle'
        }
      },
      tooltip: {
        backgroundColor: isDark ? '#171a21' : '#ffffff',
        titleColor: isDark ? '#fff' : '#0f172a',
        bodyColor: isDark ? '#94a3b8' : '#334155',
        borderColor: isDark ? '#272d3b' : '#cbd5e1',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        bodyFont: { family: 'JetBrains Mono', size: 12 }
      }
    },
    scales: {
      x: {
        grid: { color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.06)' },
        ticks: { color: isDark ? '#94a3b8' : '#475569', font: { family: 'Inter', size: 11, weight: '500' } }
      },
      y: {
        grid: { color: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.06)' },
        ticks: { color: isDark ? '#94a3b8' : '#475569', font: { family: 'JetBrains Mono', size: 11, weight: '500' } },
        suggestedMin: 24,
        suggestedMax: 44
      }
    }
  };

  // Data-driven Thermal Outlook (Sections 35-43)
  const thermalOutlook = useMemo(() => {
    if (!selectedZone) return null;

    const currentWbgt = Number(selectedZone.wbgt ?? 30.0);
    const currentTemp = Number(selectedZone.temperature ?? selectedZone.temp ?? 32.0);
    const currentRh = Number(selectedZone.humidity ?? selectedZone.rh ?? 60.0);

    let peakDayLabel = 'Today';
    let maxTemp = currentTemp;
    let maxWbgt = currentWbgt;
    let persistenceDays = 1;
    let avgHumidity = currentRh;
    let riskTrend = '→ Stable';

    if (forecastData && forecastData.length > 0) {
      let highestWbgtDay = forecastData[0];
      let runningConsecutive = 0;
      let maxConsecutive = 0;
      let totalRh = 0;

      forecastData.forEach((day) => {
        const dWbgt = Number(day.wbgt ?? 0);
        const dTemp = Number(day.temp_max ?? 0);
        if (dWbgt > (highestWbgtDay?.wbgt ?? 0)) {
          highestWbgtDay = day;
        }
        if (dTemp > maxTemp) {
          maxTemp = dTemp;
        }
        if (dWbgt >= 28.0) { // Caution threshold or above
          runningConsecutive++;
          if (runningConsecutive > maxConsecutive) maxConsecutive = runningConsecutive;
        } else {
          runningConsecutive = 0;
        }
        totalRh += Number(day.rh_max ?? currentRh);
      });

      maxWbgt = Number(highestWbgtDay?.wbgt ?? currentWbgt);
      avgHumidity = Math.round(totalRh / forecastData.length);
      persistenceDays = Math.max(1, maxConsecutive);

      // Format peak day name
      if (highestWbgtDay?.date) {
        const parts = highestWbgtDay.date.split('-');
        if (parts.length === 3) {
          const dObj = new Date(parts[0], parts[1] - 1, parts[2]);
          peakDayLabel = dObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        } else {
          peakDayLabel = highestWbgtDay.date;
        }
      }

      // Trend: compare current WBGT to peak forecast WBGT
      if (maxWbgt >= currentWbgt + 0.6) {
        riskTrend = '↑ Increasing';
      } else if (maxWbgt <= currentWbgt - 0.6) {
        riskTrend = '↓ Improving';
      } else {
        riskTrend = '→ Stable';
      }
    }

    // Nighttime recovery indicator
    const nightRecovery = (maxTemp >= 36.0 || avgHumidity >= 68) ? 'Limited' : 'Adequate';

    // Humidity burden indicator
    const humidityBurden = avgHumidity >= 65 ? 'High' : avgHumidity >= 48 ? 'Moderate' : 'Low';

    return {
      peakHeatWindow: '1:00 PM – 4:00 PM',
      peakRiskDay: peakDayLabel,
      maxTemp: maxTemp.toFixed(1),
      maxWbgt: maxWbgt.toFixed(1),
      persistence: `${persistenceDays} day${persistenceDays > 1 ? 's' : ''}`,
      nightRecovery,
      humidityBurden,
      riskTrend,
      alertLeadTime: maxWbgt >= 32.0 ? '~24–48 hours' : 'Standing Monitor'
    };
  }, [selectedZone, forecastData]);

  if (!selectedZone) return null;

  const totalHighRiskCount = highRiskGroups.severe.length + highRiskGroups.extreme.length + highRiskGroups.danger.length;

  return (
    <div className="admin-container">
      {/* Top 2-Column Split: Left Operations (56%) & Right Map + Outlook + Forecast (44%) */}
      <div className="admin-split-grid">
        {/* Left Column: Operational Decision Support */}
        <div className="admin-left-col">
          {/* 1. District & State Selector Controls Bar */}
          <section className="dashboard-card admin-controls-card">
            <div className="filter-controls-row">
              <div className="select-group">
                <label htmlFor="state-filter-select" className="select-label">State:</label>
                <select
                  id="state-filter-select"
                  className="custom-select"
                  value={selectedState}
                  onChange={handleStateChange}
                >
                  <option value="all">All States (83 Districts)</option>
                  <option value="Tamil Nadu">Tamil Nadu (38 Districts)</option>
                  <option value="Kerala">Kerala (14 Districts)</option>
                  <option value="Karnataka">Karnataka (31 Districts)</option>
                </select>
              </div>

              <div className="select-group">
                <label htmlFor="admin-district-select" className="select-label">District:</label>
                <select
                  id="admin-district-select"
                  className="custom-select"
                  value={selectedZone.id}
                  onChange={handleDistrictChange}
                >
                  {filteredDistricts.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.district || z.name} ({z.state}) — {z.wbgt}°C ({z.category})
                    </option>
                  ))}
                </select>
              </div>

              {/* Alert Test Mode Selection (Temporary Admin Control) */}
              <div className="select-group test-mode-select-group">
                <label htmlFor="admin-test-mode-select" className="select-label">Alert Test Mode:</label>
                <select
                  id="admin-test-mode-select"
                  className={`custom-select ${alertTestMode !== 'live' ? 'active-test-mode' : ''}`}
                  value={alertTestMode}
                  onChange={(e) => setAlertTestMode(e.target.value)}
                  title="Temporary Telegram alert template test mode"
                >
                  <option value="live">Live Data</option>
                  <option value="caution">Caution</option>
                  <option value="danger">Danger</option>
                  <option value="extreme">Extreme</option>
                  <option value="severe">Severe</option>
                </select>
              </div>
            </div>

            <button
              id="admin-generate-alert-btn"
              className={`action-btn-primary ${alertTestMode !== 'live' ? 'btn-test-alert' : ''}`}
              onClick={handleGenerateInstantAlert}
              disabled={isAlerting}
              title={alertTestMode !== 'live' ? `Broadcast test ${ALERT_TEST_PROFILES[alertTestMode]?.label || ALERT_TEST_PROFILES[alertTestMode]?.category} alert to Telegram channel` : "Broadcast live multilingual alert to official Telegram channel"}
            >
              <Send size={14} />
              <span>
                {isAlerting 
                  ? 'Broadcasting...' 
                  : alertTestMode !== 'live'
                    ? `Send Test Alert (${ALERT_TEST_PROFILES[alertTestMode]?.label || ALERT_TEST_PROFILES[alertTestMode]?.category})`
                    : 'Send Telegram Alert'}
              </span>
            </button>

            {/* Admin-Only Test Mode Visual Indication */}
            {alertTestMode !== 'live' && ALERT_TEST_PROFILES[alertTestMode] && (
              <div className="admin-test-mode-indicator" role="status">
                <div className="test-indicator-left">
                  <span className="test-badge-label">TEST ALERT — NOT LIVE WEATHER</span>
                  <span className="test-tier-name" style={{
                    color: alertTestMode === 'severe' ? 'var(--risk-severe)' : alertTestMode === 'extreme' ? 'var(--risk-extreme)' : alertTestMode === 'danger' ? 'var(--risk-danger)' : 'var(--risk-caution)'
                  }}>
                    {ALERT_TEST_PROFILES[alertTestMode].label || ALERT_TEST_PROFILES[alertTestMode].category}
                  </span>
                </div>
                <div className="test-indicator-values">
                  <span>~{ALERT_TEST_PROFILES[alertTestMode].temp}°C</span>
                  <span className="indicator-sep">•</span>
                  <span>WBGT ~{ALERT_TEST_PROFILES[alertTestMode].wbgt}°C</span>
                  <span className="indicator-sep">•</span>
                  <span>Peak: {ALERT_TEST_PROFILES[alertTestMode].time_window}</span>
                </div>
              </div>
            )}
          </section>

          {/* 2. Subtle Historical Health Analysis Status Bar & Expandable Methodology */}
          <section className="admin-mortality-status-bar" aria-label="Dataset Provenance Status">
            <div className="status-bar-left">
              <Database size={13} style={{ color: 'var(--accent-primary)' }} />
              <span className="status-label">HEALTH CONTEXT:</span>
              <span className="status-val-pill">Mortality-Informed Analysis</span>
              <span className="status-divider">•</span>
              <span className="status-meta">Scope: <strong>83 Districts (TN / KL / KA)</strong></span>
            </div>
            <div className="status-bar-right">
              <button 
                type="button"
                className="status-disclaimer-pill"
                onClick={() => setShowMethodology(!showMethodology)}
                title="Click to view data methodology and provenance notes"
              >
                ⓘ Data Methodology &amp; Notes
              </button>
            </div>
          </section>

          {showMethodology && (
            <div className="methodology-drawer">
              <p>
                <strong>Scientific Analysis Notice:</strong> Heat-health burden figures shown in this dashboard are derived from historical epidemiological analogues calibrated to South Indian climatological conditions. They serve as early-warning operational benchmarks and do not represent official mortality counts (NCRB/IMD) or clinical predictions.
              </p>
            </div>
          )}

          {/* 3. High-Risk Districts Monitored */}
          <section className="dashboard-card high-risk-overview-card" aria-label="High-Risk Districts">
            <div className="card-header">
              <div className="card-title-group">
                <AlertTriangle size={16} style={{ color: '#ef4444' }} />
                <span className="card-title">⚠ HIGH-RISK DISTRICTS MONITORED</span>
              </div>
              <span className="high-risk-badge-count">{totalHighRiskCount} Districts Active</span>
            </div>

            <div className="high-risk-groups-container">
              {/* Severe Group */}
              {highRiskGroups.severe.length > 0 && (
                <div className="risk-tier-block severe-block">
                  <span className="risk-tier-title" style={{ color: 'var(--tag-severe-text)' }}>● SEVERE (&gt; 35°C WBGT)</span>
                  <div className="risk-tier-chips">
                    {highRiskGroups.severe.map((d) => (
                      <button
                        key={d.id}
                        className={`risk-chip severe ${selectedZone.id === d.id ? 'active' : ''}`}
                        onClick={() => onSelectZone(d)}
                      >
                        <span className="chip-name">{d.name}</span>
                        <span className="chip-wbgt">{d.wbgt}°C</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Extreme Group */}
              {highRiskGroups.extreme.length > 0 && (
                <div className="risk-tier-block extreme-block">
                  <span className="risk-tier-title" style={{ color: 'var(--tag-extreme-text)' }}>● EXTREME DANGER (32–35°C WBGT)</span>
                  <div className="risk-tier-chips">
                    {highRiskGroups.extreme.map((d) => (
                      <button
                        key={d.id}
                        className={`risk-chip extreme ${selectedZone.id === d.id ? 'active' : ''}`}
                        onClick={() => onSelectZone(d)}
                      >
                        <span className="chip-name">{d.name}</span>
                        <span className="chip-wbgt">{d.wbgt}°C</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Danger Group */}
              {highRiskGroups.danger.length > 0 && (
                <div className="risk-tier-block danger-block">
                  <span className="risk-tier-title" style={{ color: 'var(--tag-danger-text)' }}>● DANGER (30–32°C WBGT)</span>
                  <div className="risk-tier-chips">
                    {highRiskGroups.danger.map((d) => (
                      <button
                        key={d.id}
                        className={`risk-chip danger ${selectedZone.id === d.id ? 'active' : ''}`}
                        onClick={() => onSelectZone(d)}
                      >
                        <span className="chip-name">{d.name}</span>
                        <span className="chip-wbgt">{d.wbgt}°C</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {totalHighRiskCount === 0 && (
                <div style={{ padding: '16px', color: 'var(--text-muted)', fontSize: '0.82rem', textAlign: 'center' }}>
                  All 83 districts currently remain within Low to Caution thresholds (&lt; 30°C WBGT).
                </div>
              )}
            </div>
          </section>

          {/* 4. Historical Health Analysis & Thermal Analogue Panel */}
          <section className="dashboard-card admin-mortality-panel" aria-label="Historical Health Analysis">
            <div className="card-header">
              <div className="card-title-group">
                <Database size={16} style={{ color: 'var(--accent-primary)' }} />
                <span className="card-title">
                  HISTORICAL HEALTH ANALYSIS — {selectedZone.name.toUpperCase()}
                </span>
              </div>
              <div className="analogue-scope-badge-group">
                <span className="analogue-state-pill">Scope: {selectedZone.state}</span>
                <span className="synthetic-badge-pill" title="Mortality-informed statistical analogue model applied for early-warning health decision support.">
                  MORTALITY-INFORMED
                </span>
              </div>
            </div>

            {mortalityLoading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                Matching historical thermal analogues for {selectedZone.name}...
              </div>
            ) : mortalityAnalogue?.analogue_analysis?.available ? (
              <div className="admin-mortality-content">
                {/* Current vs Top Similar Historical Scenario Comparison */}
                <div className="analogue-comparison-block">
                  <span className="sub-panel-title">THERMAL ANALOGUE MATCH (CURRENT VS SIMILAR HISTORICAL SCENARIO)</span>
                  <div className="comparison-grid">
                    {/* Current Side */}
                    <div className="comparison-col current-col">
                      <div className="col-header-tag">CURRENT LIVE CONDITIONS</div>
                      <div className="comparison-metrics-list">
                        <div className="comp-row">
                          <span className="comp-label">Ambient Temp</span>
                          <span className="comp-val">{selectedZone.temperature ?? selectedZone.temp}°C</span>
                        </div>
                        <div className="comp-row">
                          <span className="comp-label">WBGT Thermal Stress</span>
                          <span className="comp-val highlight-val" style={{ color: selectedZone.color }}>
                            {selectedZone.wbgt}°C
                          </span>
                        </div>
                        <div className="comp-row">
                          <span className="comp-label">Heat Index</span>
                          <span className="comp-val">{selectedZone.heat_index ?? selectedZone.hi ?? '—'}°C</span>
                        </div>
                        <div className="comp-row">
                          <span className="comp-label">UTCI Biometeo</span>
                          <span className="comp-val" style={{ color: selectedZone.utci_color || 'var(--text-primary)' }}>
                            {selectedZone.utci !== undefined ? `${selectedZone.utci}°C` : '—'}
                          </span>
                        </div>
                        <div className="comp-row">
                          <span className="comp-label">Risk Category</span>
                          <span className="comp-val comp-cat-badge" style={{ color: selectedZone.color }}>
                            {selectedZone.category.toUpperCase()}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Versus Divider */}
                    <div className="comp-vs-divider">
                      <span className="vs-circle">VS</span>
                    </div>

                    {/* Historical Analogue Side */}
                    {(() => {
                      const topMatch = mortalityAnalogue.analogue_analysis.analogues?.[0];
                      return (
                        <div className="comparison-col analogue-col">
                          <div className="col-header-tag analogue-tag">
                            SIMILAR HISTORICAL SCENARIO ({topMatch?.formatted_date || topMatch?.date || '—'})
                          </div>
                          <div className="comparison-metrics-list">
                            <div className="comp-row">
                              <span className="comp-label">Historical Temp</span>
                              <span className="comp-val">{topMatch?.max_temperature_c}°C</span>
                            </div>
                            <div className="comp-row">
                              <span className="comp-label">Historical WBGT</span>
                              <span className="comp-val">{topMatch?.wbgt_c}°C</span>
                            </div>
                            <div className="comp-row">
                              <span className="comp-label">Match Similarity</span>
                              <span className="comp-val highlight-val" style={{ color: 'var(--accent-primary)' }}>
                                {topMatch?.similarity_score}%
                              </span>
                            </div>
                            <div className="comp-row">
                              <span className="comp-label">Health Burden Estimate</span>
                              <span className="comp-val comp-deaths-badge">
                                {topMatch?.heat_related_deaths_total} deaths (Estimated)
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>

                {/* Aggregate KPIs & Demographics */}
                {(() => {
                  const summary = mortalityAnalogue.analogue_analysis.summary;
                  if (!summary) return null;
                  return (
                    <div className="analogue-aggregates-section">
                      <div className="aggregate-kpis-grid">
                        <div className="kpi-mini-card">
                          <span className="kpi-label">SIMILAR SCENARIOS</span>
                          <span className="kpi-val">{summary.count} Found</span>
                          <span className="kpi-sub">Match: {summary.min_similarity}%–{summary.max_similarity}%</span>
                        </div>

                        <div className="kpi-mini-card">
                          <span className="kpi-label">AVG HISTORICAL HEALTH BURDEN</span>
                          <span className="kpi-val highlight-val">{summary.average_simulated_deaths} deaths</span>
                          <span className="kpi-sub">Median: {summary.median_simulated_deaths} (Range: {summary.min_simulated_deaths}–{summary.max_simulated_deaths})</span>
                        </div>

                        <div className="kpi-mini-card">
                          <span className="kpi-label">HISTORICAL MORTALITY RATE</span>
                          <span className="kpi-val">{summary.average_mortality_rate_per_100000}</span>
                          <span className="kpi-sub">Per 100,000 population</span>
                        </div>

                        <div className="kpi-mini-card">
                          <span className="kpi-label">MOST AFFECTED COHORT</span>
                          <span className="kpi-val cohort-val">{summary.most_affected_age_group}</span>
                          <span className="kpi-sub">Historical analogue pattern</span>
                        </div>
                      </div>

                      {/* Age & Gender Distribution */}
                      <div className="demographics-grid">
                        <div className="demographics-card">
                          <span className="demo-title">Age Distribution — Analogue Scenarios</span>
                          <div className="demo-bars-list">
                            <div className="demo-bar-item">
                              <div className="demo-label-row">
                                <span>Under 30 years</span>
                                <strong>{summary.age_distribution?.under_30_percent}%</strong>
                              </div>
                              <div className="demo-bar-track">
                                <div className="demo-bar-fill" style={{ width: `${summary.age_distribution?.under_30_percent}%`, backgroundColor: 'var(--accent-primary)' }}></div>
                              </div>
                            </div>
                            <div className="demo-bar-item">
                              <div className="demo-label-row">
                                <span>30–59 years (Workforce)</span>
                                <strong>{summary.age_distribution?.['30_59_percent']}%</strong>
                              </div>
                              <div className="demo-bar-track">
                                <div className="demo-bar-fill" style={{ width: `${summary.age_distribution?.['30_59_percent']}%`, backgroundColor: '#f97316' }}></div>
                              </div>
                            </div>
                            <div className="demo-bar-item">
                              <div className="demo-label-row">
                                <span>60+ years (Elderly)</span>
                                <strong>{summary.age_distribution?.['60_plus_percent']}%</strong>
                              </div>
                              <div className="demo-bar-track">
                                <div className="demo-bar-fill" style={{ width: `${summary.age_distribution?.['60_plus_percent']}%`, backgroundColor: '#ef4444' }}></div>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="demographics-card">
                          <span className="demo-title">Gender Distribution — Analogue Scenarios</span>
                          <div className="gender-ratio-row">
                            <div className="gender-box male-box">
                              <span className="gender-name">Male</span>
                              <span className="gender-val">{summary.gender_distribution?.male_percent}%</span>
                            </div>
                            <div className="gender-box female-box">
                              <span className="gender-name">Female</span>
                              <span className="gender-val">{summary.gender_distribution?.female_percent}%</span>
                            </div>
                          </div>
                          <p className="demographics-caption">
                            Aggregate distribution across 5 matched {selectedZone.state} days. Not an individual prediction.
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Health Decision-Support Note */}
                <div className="admin-mortality-disclaimer-box">
                  <span className="disclaimer-icon">ℹ</span>
                  <p>
                    <strong>Health Decision-Support Note:</strong> Thermal analogue figures indicate estimated historical heat burdens under comparable temperature and WBGT conditions.
                  </p>
                </div>
              </div>
            ) : (
              <div style={{ padding: '20px', color: 'var(--text-muted)', fontSize: '0.82rem', textAlign: 'center' }}>
                Historical mortality analysis unavailable. Live thermal early-warning pipeline remains fully operational.
              </div>
            )}
          </section>

          {/* 5. Early Warning & Alert Escalation Workflow */}
          <section className="dashboard-card alert-workflow-card" aria-label="Alert Escalation Workflow">
            <div className="card-header">
              <div className="card-title-group">
                <BellRing size={16} style={{ color: 'var(--accent-primary)' }} />
                <span className="card-title">EARLY WARNING & ALERT ESCALATION WORKFLOW</span>
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Civil Defense Protocol
              </span>
            </div>

            <div className="workflow-alerts-list">
              {alertsList.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  Scanning 83 districts for 48-hour projected thermal hazards...
                </div>
              ) : (
                alertsList.slice(0, 6).map((alert) => {
                  const is48h = alert.trigger_type.includes('48-Hour');
                  return (
                    <div key={alert.alert_id} className={`workflow-alert-item ${alert.status.toLowerCase()}`}>
                      <div className="alert-item-header">
                        <div className="alert-type-badge-row">
                          <span className={`trigger-type-pill ${is48h ? 'warning-48h' : 'today-alert'}`}>
                            {is48h ? '⚠ 48-HOUR EARLY WARNING' : "📢 TODAY'S HEAT ALERT"}
                          </span>
                          <span className="alert-district-name">
                            {alert.district_name} ({alert.state})
                          </span>
                          <span className="alert-risk-level" style={{ color: alert.risk_level === 'SEVERE' ? (isDark ? '#fda4af' : '#881337') : alert.risk_level === 'EXTREME' ? (isDark ? '#f87171' : '#b91c1c') : (isDark ? '#fb923c' : '#c2410c') }}>
                            {alert.risk_level} • WBGT {alert.expected_wbgt}°C
                          </span>
                        </div>

                        <div className="alert-status-pill-group">
                          <span className={`status-pill ${alert.status.toLowerCase()}`}>
                            STATUS: {alert.status}
                          </span>
                        </div>
                      </div>

                      <div className="alert-meta-row">
                        <span>Date of Risk: <strong>{alert.risk_date}</strong></span>
                        <span>Target Recipient: <strong>{alert.recipient_type}</strong></span>
                        {alert.acknowledged_by && (
                          <span>Ack By: <strong>{alert.acknowledged_by}</strong> ({alert.acknowledged_at})</span>
                        )}
                        {alert.escalated_to && (
                          <span style={{ color: '#ef4444' }}>Escalated To: <strong>{alert.escalated_to}</strong></span>
                        )}
                      </div>

                      {/* Historical Analogue for Alert */}
                      {alert.simulated_mortality_burden !== undefined && alert.simulated_mortality_burden !== null && (
                        <div className="alert-analogue-preview">
                          <span className="analogue-preview-badge">HISTORICAL ANALOGUE</span>
                          <span className="analogue-preview-text">
                            {alert.historical_analogues_count || 5} similar scenarios found • Estimated health burden: <strong>{alert.simulated_mortality_burden} deaths</strong>
                            {alert.simulated_mortality_rate_per_100000 !== null && ` (${alert.simulated_mortality_rate_per_100000} / 100k)`}
                            {alert.top_analogue_scenario && (
                              <span className="analogue-top-match-sub">
                                {' '}• Top match: {alert.top_analogue_scenario.formatted_date || alert.top_analogue_scenario.date} ({alert.top_analogue_scenario.similarity_score}% match)
                              </span>
                            )}
                          </span>
                        </div>
                      )}

                      {/* Operational Action Buttons */}
                      <div className="alert-action-btn-row">
                        {alert.status === 'PENDING' && (
                          <button
                            className="workflow-action-btn ack-btn"
                            onClick={() => handleAcknowledgeAlert(alert.alert_id)}
                            disabled={processingAlertId === alert.alert_id}
                          >
                            <CheckCircle2 size={13} />
                            <span>Acknowledge</span>
                          </button>
                        )}

                        {alert.status !== 'ESCALATED' && (
                          <button
                            className="workflow-action-btn esc-btn"
                            onClick={() => handleEscalateAlert(alert.alert_id)}
                            disabled={processingAlertId === alert.alert_id}
                          >
                            <ArrowUpRight size={13} />
                            <span>Escalate</span>
                          </button>
                        )}

                        {alert.status !== 'PUBLIC_ALERT_SENT' && (
                          <button
                            className="workflow-action-btn public-btn"
                            onClick={() => handleSendPublicAlert(alert.alert_id)}
                            disabled={processingAlertId === alert.alert_id}
                          >
                            <Radio size={13} />
                            <span>Send Public Alert</span>
                          </button>
                        )}

                        <span className="simulated-badge">CIVIL DEFENSE DISPATCH</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          {/* 6. Municipal Directive Checklist */}
          <section className="dashboard-card checklist-card">
            <div className="checklist-title-bar">
              <span className="card-title">Municipal Heat Action Plan Directive</span>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Current Threshold: {selectedZone.category}
              </span>
            </div>

            <div className="checklist-items">
              <div
                className={`checklist-row ${actions.coolingCenters ? 'checked' : ''}`}
                onClick={() => toggleAction('coolingCenters')}
              >
                <div className="custom-checkbox">
                  {actions.coolingCenters ? (
                    <CheckSquare size={17} style={{ color: 'var(--risk-low)' }} />
                  ) : (
                    <Square size={17} style={{ color: 'var(--text-muted)' }} />
                  )}
                </div>
                <div className="checklist-content">
                  <span className="checklist-text">Open municipal cooling centres and shaded water hydration points</span>
                  <span className="checklist-sub">Priority: Public transit hubs, primary health centres, and markets</span>
                </div>
              </div>

              <div
                className={`checklist-row ${actions.shiftWorkHours ? 'checked' : ''}`}
                onClick={() => toggleAction('shiftWorkHours')}
              >
                <div className="custom-checkbox">
                  {actions.shiftWorkHours ? (
                    <CheckSquare size={17} style={{ color: 'var(--risk-low)' }} />
                  ) : (
                    <Square size={17} style={{ color: 'var(--text-muted)' }} />
                  )}
                </div>
                <div className="checklist-content">
                  <span className="checklist-text">Enforce mandatory work stoppage for outdoor labor (12:00 PM – 4:00 PM)</span>
                  <span className="checklist-sub">Covers construction workers, street vendors, delivery personnel, and sanitation staff</span>
                </div>
              </div>

              <div
                className={`checklist-row ${actions.flagGridLoad ? 'checked' : ''}`}
                onClick={() => toggleAction('flagGridLoad')}
              >
                <div className="custom-checkbox">
                  {actions.flagGridLoad ? (
                    <CheckSquare size={17} style={{ color: 'var(--risk-low)' }} />
                  ) : (
                    <Square size={17} style={{ color: 'var(--text-muted)' }} />
                  )}
                </div>
                <div className="checklist-content">
                  <span className="checklist-text">Flag high power-grid demand for state electricity distribution board</span>
                  <span className="checklist-sub">Mitigate transformer blowout risk during peak afternoon cooling surge</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column: Spatial GIS Map + Thermal Outlook + 7-Day Trajectory */}
        <div className="admin-right-col">
          {/* 1. District Choropleth Map with Admin Risk Styling */}
          <section className="dashboard-card admin-map-card">
            <IndiaHeatMap
              zones={zones}
              selectedZone={selectedZone}
              onSelectZone={onSelectZone}
              height="100%"
              activeStateFilter={selectedState}
              isAdminView={true}
            />
          </section>

          {/* 2. Compact Predictive Decision Support: Thermal Outlook (Sections 35-43) */}
          {thermalOutlook && (
            <section className="dashboard-card admin-outlook-card" aria-label="Thermal Outlook">
              <div className="card-header" style={{ padding: '0 0 10px 0' }}>
                <div className="card-title-group">
                  <ThermometerSun size={16} style={{ color: 'var(--accent-primary)' }} />
                  <span className="card-title">
                    THERMAL OUTLOOK — {selectedZone.district || selectedZone.name}
                  </span>
                </div>
                <span className="outlook-trend-badge" style={{
                  color: thermalOutlook.riskTrend.includes('↑') ? (isDark ? '#ef4444' : '#dc2626') : thermalOutlook.riskTrend.includes('↓') ? (isDark ? '#10b981' : '#047857') : (isDark ? '#f59e0b' : '#b45309'),
                  borderColor: 'currentColor'
                }}>
                  {thermalOutlook.riskTrend}
                </span>
              </div>

              <div className="outlook-metrics-grid">
                <div className="outlook-cell">
                  <span className="outlook-label">PEAK HEAT WINDOW</span>
                  <span className="outlook-val highlight">{thermalOutlook.peakHeatWindow}</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">PEAK RISK DAY</span>
                  <span className="outlook-val">{thermalOutlook.peakRiskDay}</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">EXPECTED MAX TEMP</span>
                  <span className="outlook-val">{thermalOutlook.maxTemp}°C</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">EXPECTED WBGT</span>
                  <span className="outlook-val highlight-wbgt">{thermalOutlook.maxWbgt}°C</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">HEAT PERSISTENCE</span>
                  <span className="outlook-val">{thermalOutlook.persistence}</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">NIGHT RECOVERY</span>
                  <span className="outlook-val" style={{ color: thermalOutlook.nightRecovery === 'Limited' ? (isDark ? '#f59e0b' : '#b45309') : (isDark ? '#10b981' : '#047857') }}>
                    {thermalOutlook.nightRecovery}
                  </span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">HUMIDITY BURDEN</span>
                  <span className="outlook-val">{thermalOutlook.humidityBurden}</span>
                </div>
                <div className="outlook-cell">
                  <span className="outlook-label">ALERT LEAD TIME</span>
                  <span className="outlook-val">{thermalOutlook.alertLeadTime}</span>
                </div>
              </div>
            </section>
          )}

          {/* 3. 7-Day Trajectory Forecast Chart (Sections 30-34) */}
          <section className="dashboard-card chart-container-card">
            <div className="card-header" style={{ padding: '0 0 12px 0' }}>
              <div className="card-title-group">
                <TrendingUp size={16} style={{ color: 'var(--accent-primary)' }} />
                <span className="card-title">
                  7-Day Thermal Trajectory — {selectedZone.district || selectedZone.name}
                </span>
              </div>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Open-Meteo Multi-Day Feed
              </span>
            </div>

            <div className="chart-wrapper">
              {forecastLoading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                  Retrieving multi-day district forecast...
                </div>
              ) : (
                <Line data={chartData} options={chartOptions} />
              )}
            </div>
          </section>
        </div>
      </div>

      {/* Spanning Bottom Row: Telegram Public Alert & Communication Stream */}
      <div className="admin-bottom-row">
        <section className="dashboard-card admin-alert-stream-card alert-log-card" aria-label="District Communication Stream">
          <div className="card-header alert-stream-header">
            <div className="card-title-group">
              <Clock size={16} style={{ color: 'var(--accent-primary)' }} />
              <span className="card-title">Telegram Public Alert &amp; Communication Stream</span>
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Live Telegram Dispatch Log
            </span>
          </div>

          <div className="alert-log-list">
            {alertLogs.length === 0 ? (
              <div className="empty-log-state">
                <AlertCircle size={20} style={{ color: 'var(--text-dim)', marginBottom: '6px' }} />
                <p className="empty-log-title">NO ALERTS DISPATCHED</p>
                <span className="empty-log-desc">
                  Live Telegram alert broadcasts will stream here in real-time once triggered from the workflow panel.
                </span>
              </div>
            ) : (
              alertLogs.map((log, index) => (
                <div key={index} className={`alert-log-item ${log.sent === false ? 'alert-log-failed' : ''}`}>
                  <div className="log-item-header">
                    <span className="log-district">{log.district_name || log.zone_name} ({log.state})</span>
                    <span 
                      className="log-category-pill" 
                      style={{ 
                        color: log.thermal_category === 'Severe' ? '#ef4444' : (log.thermal_category === 'Extreme Danger' || log.thermal_category === 'Extreme') ? '#f97316' : '#f59e0b',
                        borderColor: 'currentColor'
                      }}
                    >
                      {log.thermal_category} (WBGT {log.wbgt}°C)
                    </span>
                    {log.is_test_mode && (
                      <span className="badge-test-dispatch">
                        TEST DISPATCH
                      </span>
                    )}
                    {log.sent ? (
                      <span className="badge-telegram-sent">
                        ● SENT
                      </span>
                    ) : (
                      <span className="badge-telegram-failed">
                        ✕ SEND FAILED
                      </span>
                    )}
                    <span className="log-timestamp">{log.timestamp}</span>
                  </div>

                  {log.sent === false && log.error && (
                    <div className="log-error-banner">
                      ⚠️ SEND FAILED — {log.error}
                    </div>
                  )}

                  <pre className="log-message-preview">{log.message}</pre>

                  <div className="log-footer">
                    <span>Channel: {log.channel_id || log.channel || '@Climate_Guard_India_Alerts'}</span>
                    {log.message_id ? <span>Telegram Msg ID: #{log.message_id}</span> : null}
                    <span>Languages: English • தமிழ் • हिन्दी</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
