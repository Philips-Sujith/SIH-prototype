import React, { useEffect, useState, useMemo } from 'react';
import { 
  AlertTriangle, 
  Thermometer, 
  Droplets, 
  Wind, 
  Compass, 
  UserCheck, 
  Clock, 
  RotateCw, 
  ChevronDown, 
  ShieldAlert
} from 'lucide-react';
import IndiaHeatMap from './IndiaHeatMap';
import WeatherHeatVisual from './WeatherHeatVisual';
import { useTheme } from '../context/ThemeContext';

const POPULATION_PROFILES = [
  { id: 'general_public', name: 'General Public' },
  { id: 'it_office', name: 'IT / Office Worker' },
  { id: 'outdoor_worker', name: 'Outdoor Worker (Vendors / Delivery)' },
  { id: 'construction_labor', name: 'Construction / Labor Worker' },
  { id: 'student', name: 'Student / Youth' },
  { id: 'pregnant', name: 'Pregnant Person' },
  { id: 'elderly', name: 'Elderly Person (60+ Years)' },
  { id: 'child', name: 'Infant & Young Child (Under 10)' },
  { id: 'chronic_conditions', name: 'Person with Chronic Conditions' }
];

// Profile-specific actionable directives for high-risk conditions
function getActionPlanDirectives(profileId, category) {
  const isExtreme = category === 'Extreme Danger' || category === 'Severe';
  
  switch (profileId) {
    case 'it_office':
      return [
        'Maintain scheduled desk hydration (drink water or electrolyte fluids every 45 mins) despite indoor air conditioning.',
        isExtreme 
          ? 'Mandatory travel restriction: strictly avoid two-wheeler or walking commute between 11:30 AM – 4:00 PM.' 
          : 'Limit midday outdoor lunch trips; select shaded transit routes.',
        'Beware of thermal shock when stepping from cool AC rooms directly into ambient midday heat.',
        'Verify backup office ventilation and generator power for air-circulation systems.'
      ];
    case 'outdoor_worker':
      return [
        'Enforce mandatory 15-minute shaded rest breaks for every 45 minutes of road/street movement.',
        'Carry at least 2 to 3 liters of water mixed with ORS/electrolytes; rehydrate continuously before thirst peaks.',
        isExtreme 
          ? 'EMERGENCY PROTOCOL: Suspend active delivery and strenuous street vending during peak window (12:00 PM – 3:30 PM).'
          : 'Reschedule heavy physical tasks to early morning hours (before 10:30 AM).',
        'Wear wide-brimmed caps, loose light-colored cotton attire, and protect the back of the neck.',
        'Report symptoms of dizziness, muscle cramps, or nausea immediately to emergency helpline 108.'
      ];
    case 'construction_labor':
      return [
        isExtreme
          ? 'MANDATORY DIRECTIVE: Complete cessation of open-sun heavy physical labor between 12:00 PM – 4:00 PM.'
          : 'Mandatory work stoppage for heavy masonry and roofing during peak afternoon heat.',
        'Provide covered, well-ventilated rest shelters with cold potable water and oral rehydration salts.',
        'Shift heavy work shifts to early morning (6:00 AM – 10:30 AM) and post-4:30 PM.',
        'Enforce a strict buddy system to monitor coworkers for confusion, unsteady gait, or stopped sweating.'
      ];
    case 'student':
      return [
        'Cancel all unshaded outdoor physical education, athletic drills, and sports practices.',
        'Ensure school and college classrooms have continuous cross-ventilation and functional fans.',
        'Sound hourly school hydration bells to remind students to drink water.',
        'Avoid prolonged waiting at open sun bus stops during afternoon dismissal.'
      ];
    case 'pregnant':
      return [
        'Remain strictly indoors in cooled or well-ventilated spaces during peak solar irradiance.',
        'Increase fluid and electrolyte intake to counter elevated maternal metabolic heat generation.',
        'Elevate legs during rest intervals to mitigate heat-aggravated peripheral swelling.',
        'Contact primary healthcare provider or local clinic if feeling faint, dizzy, or severely fatigued.'
      ];
    case 'elderly':
      return [
        'Remain in the coolest room of the residence; avoid any non-essential outdoor excursions.',
        'Drink water on a fixed hourly schedule; aging blunts the natural biological thirst response.',
        'Use damp washcloths on neck and wrists for gentle evaporative cooling.',
        'Ensure family members or community volunteers perform daily welfare check-ins.'
      ];
    case 'child':
      return [
        'Keep infants and young children indoors in well-ventilated, shaded rooms between 11:00 AM – 4:30 PM.',
        'NEVER leave infants or children unattended in parked vehicles under any circumstance.',
        'Offer frequent small sips of water, breast milk, or oral rehydration fluids throughout the day.',
        'Dress in light, breathable cotton; sponge with lukewarm water if skin appears flushed.'
      ];
    case 'chronic_conditions':
      return [
        'Strictly avoid direct ambient heat exposure; thermal strain heavily increases cardiac and renal workload.',
        'Monitor blood pressure and fluid balance closely; adjust prescription medications only under medical advice.',
        'Keep emergency contacts and ambulance service (108) readily accessible.',
        'Ensure temperature-sensitive medications (like insulin) are kept in cool shaded storage.'
      ];
    case 'general_public':
    default:
      return [
        'Increase fluid intake (minimum 3–4 liters daily; incorporate lemon water, tender coconut, or ORS).',
        isExtreme 
          ? 'Strictly minimize unshaded outdoor exposure between 11:30 AM – 4:00 PM.' 
          : 'Avoid continuous sun exposure during peak afternoon hours.',
        'Wear loose, light-colored cotton clothing and carry a sun umbrella or hat outdoors.',
        'Check on elderly neighbors, outdoor workers, and vulnerable household members.',
        'Access municipal cooling centres or shaded public parks if home cooling is inadequate.'
      ];
  }
}

export default function PublicDashboard({ 
  zones, 
  selectedZone, 
  onSelectZone, 
  apiBase, 
  onRefreshTelemetry,
  lastUpdated 
}) {
  const { isDark } = useTheme();

  const getThemeRiskBadgeStyle = (category, defaultColor) => {
    const cat = (category || '').toLowerCase();
    if (isDark) {
      return {
        backgroundColor: `${defaultColor}22`,
        color: defaultColor,
        borderColor: `${defaultColor}70`
      };
    }
    if (cat.includes('low')) return { backgroundColor: 'var(--tag-low-bg)', color: 'var(--tag-low-text)', borderColor: 'var(--tag-low-border)' };
    if (cat.includes('caution')) return { backgroundColor: 'var(--tag-caution-bg)', color: 'var(--tag-caution-text)', borderColor: 'var(--tag-caution-border)' };
    if (cat.includes('danger') && !cat.includes('extreme')) return { backgroundColor: 'var(--tag-danger-bg)', color: 'var(--tag-danger-text)', borderColor: 'var(--tag-danger-border)' };
    if (cat.includes('extreme')) return { backgroundColor: 'var(--tag-extreme-bg)', color: 'var(--tag-extreme-text)', borderColor: 'var(--tag-extreme-border)' };
    if (cat.includes('severe')) return { backgroundColor: 'var(--tag-severe-bg)', color: 'var(--tag-severe-text)', borderColor: 'var(--tag-severe-border)' };
    return {
      backgroundColor: `${defaultColor}15`,
      color: defaultColor,
      borderColor: `${defaultColor}60`
    };
  };

  const getThemeImpactBadgeStyle = (level, defaultColor) => {
    const lvl = (level || '').toLowerCase();
    if (isDark) {
      return {
        backgroundColor: `${defaultColor}22`,
        color: defaultColor,
        border: `1px solid ${defaultColor}60`
      };
    }
    if (lvl.includes('low')) return { backgroundColor: 'var(--tag-low-bg)', color: 'var(--tag-low-text)', border: '1px solid var(--tag-low-border)' };
    if (lvl.includes('moderate')) return { backgroundColor: 'var(--tag-caution-bg)', color: 'var(--tag-caution-text)', border: '1px solid var(--tag-caution-border)' };
    if (lvl.includes('high') && !lvl.includes('very')) return { backgroundColor: 'var(--tag-danger-bg)', color: 'var(--tag-danger-text)', border: '1px solid var(--tag-danger-border)' };
    if (lvl.includes('very high')) return { backgroundColor: 'var(--tag-extreme-bg)', color: 'var(--tag-extreme-text)', border: '1px solid var(--tag-extreme-border)' };
    if (lvl.includes('severe')) return { backgroundColor: 'var(--tag-severe-bg)', color: 'var(--tag-severe-text)', border: '1px solid var(--tag-severe-border)' };
    return {
      backgroundColor: `${defaultColor}15`,
      color: defaultColor,
      border: `1px solid ${defaultColor}50`
    };
  };
  const [selectedProfile, setSelectedProfile] = useState('general_public');
  const [impactData, setImpactData] = useState(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState(null);

  // Fetch profile impact whenever selectedZone or selectedProfile changes
  useEffect(() => {
    if (!selectedZone) return;

    let isCurrent = true;
    setImpactLoading(true);

    fetch(`${apiBase}/api/districts/${selectedZone.id}/impact?profile_id=${selectedProfile}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load profile impact");
        return res.json();
      })
      .then((data) => {
        if (isCurrent) {
          setImpactData({
            ...data.impact,
            historical_analogue: data.historical_analogue,
            mortality_dataset_info: data.mortality_dataset_info
          });
          setImpactLoading(false);
        }
      })
      .catch((err) => {
        console.warn("Using local profile impact fallback:", err);
        if (isCurrent) {
          setImpactData({
            profile_name: POPULATION_PROFILES.find(p => p.id === selectedProfile)?.name || 'General Public',
            environmental_category: selectedZone.category,
            profile_score: selectedZone.risk_score,
            impact_level: selectedZone.category === 'Severe' ? 'CRITICAL' : selectedZone.category === 'Extreme Danger' ? 'VERY HIGH' : selectedZone.category === 'Danger' ? 'HIGH' : 'MODERATE',
            impact_color: selectedZone.color,
            bulletin: {
              exposure: selectedProfile === 'it_office' ? 'Moderate (Commute / AC transit)' : 'High (Outdoor thermal load)',
              main_concern: 'Thermal fatigue, reduced hydration retention',
              possible_effects: 'Dizziness, headache, elevated perspiration',
              recommended_action: 'Drink water regularly; schedule shade breaks during midday',
              outdoor_travel: 'Avoid direct unshaded exposure between 12 PM - 4 PM',
              peak_period: '12:00 PM – 4:00 PM'
            }
          });
          setImpactLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [selectedZone, selectedProfile, apiBase]);

  // Handle manual weather refresh
  const handleManualRefresh = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    setRefreshStatus('Refreshing live telemetry...');

    try {
      if (onRefreshTelemetry) {
        await onRefreshTelemetry();
        setRefreshStatus('Updated just now');
      } else {
        const res = await fetch(`${apiBase}/api/districts?refresh=true`);
        if (!res.ok) throw new Error("Failed to refresh");
        setRefreshStatus('Updated just now');
      }
      setTimeout(() => setRefreshStatus(null), 3500);
    } catch (err) {
      console.error("Manual refresh failed:", err);
      setRefreshStatus('Refresh failed — showing last available data');
      setTimeout(() => setRefreshStatus(null), 4500);
    } finally {
      setIsRefreshing(false);
    }
  };

  if (!selectedZone) {
    return (
      <div className="public-grid">
        <div className="left-stack">
          <div className="dashboard-card" style={{ padding: '32px', textAlign: 'center' }}>
            <Compass size={32} style={{ color: 'var(--accent-primary)', margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Loading 83 South India district telemetry...</p>
          </div>
        </div>
      </div>
    );
  }

  const bulletin = impactData?.bulletin;
  const historicalAnalogue = impactData?.historical_analogue;
  const isHighRisk = ['Danger', 'Extreme Danger', 'Severe'].includes(selectedZone.category);

  return (
    <div className="public-grid">
      {/* Left ~58% Content Stack */}
      <div className="left-stack">

        {/* 1. Essential District Identity (Compact Level 1 Priority) */}
        <section className="dashboard-card district-hero-compact">
          <div className="district-hero-header">
            <div>
              <div className="district-tag-row">
                <span className="state-badge-clean">{selectedZone.state}</span>
                <span className="coord-text-clean">
                  {Number(selectedZone.lat || 13).toFixed(2)}°N, {Number(selectedZone.lon || 80).toFixed(2)}°E
                </span>
              </div>
              <h1 className="district-title-clean" id="district-title-name">
                {selectedZone.district || selectedZone.name}
              </h1>
            </div>

            <div 
              className="risk-badge-clean"
              style={getThemeRiskBadgeStyle(selectedZone.category, selectedZone.color)}
            >
              <AlertTriangle size={15} />
              <span>{selectedZone.category.toUpperCase()}</span>
            </div>
          </div>
        </section>

        {/* Profile-Specific Heat Health Impact Card with Scrollable Bulletin */}
        <section 
          className="dashboard-card impact-bulletin-card"
          style={{ borderLeft: `4px solid ${impactData?.impact_color || selectedZone.color}` }}
          aria-label="Profile-Specific Heat Health Impact"
        >
          <div className="impact-header-row">
            <div className="impact-title-group">
              <UserCheck size={16} style={{ color: 'var(--accent-primary)' }} />
              <span className="card-title">HEAT IMPACT BULLETIN</span>
            </div>

            {impactData && (
              <div 
                className="profile-impact-badge"
                style={getThemeImpactBadgeStyle(impactData.impact_level, impactData.impact_color)}
              >
                <span>IMPACT: <strong>{impactData.impact_level}</strong></span>
              </div>
            )}
          </div>

          {/* Population Profile Dropdown */}
          <div className="profile-select-wrapper">
            <label htmlFor="population-profile-select" className="profile-select-label">
              For Profile:
            </label>
            <div className="custom-select-container">
              <select
                id="population-profile-select"
                className="profile-custom-select"
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(e.target.value)}
              >
                {POPULATION_PROFILES.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="select-arrow-icon" />
            </div>
          </div>

          {/* Fully Scrollable 5-Point Scannable Bulletin Container (Fixes Content Cropping) */}
          <div className="bulletin-scroll-wrapper">
            {impactLoading ? (
              <div style={{ padding: '24px', color: 'var(--text-muted)', textAlign: 'center' }}>
                Evaluating profile vulnerability factors for {selectedZone.name}...
              </div>
            ) : bulletin ? (
              <ul className="bulletin-list">
                <li className="bulletin-item">
                  <span className="bullet-label">● Exposure</span>
                  <span className="bullet-value">{bulletin.exposure}</span>
                </li>

                <li className="bulletin-item">
                  <span className="bullet-label">● Main Concern</span>
                  <span className="bullet-value">{bulletin.main_concern}</span>
                </li>

                <li className="bulletin-item">
                  <span className="bullet-label">● Possible Impact</span>
                  <span className="bullet-value">{bulletin.possible_effects}</span>
                </li>

                {/* Mortality-Informed Health Analysis (Sections 3, 20, 21) */}
                <li className="bulletin-item">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                    <span className="bullet-label">● Health Analysis</span>
                    <span 
                      className="mortality-informed-badge" 
                      title="Mortality-informed statistical analogue model applied for early-warning health decision support."
                    >
                      MORTALITY-INFORMED
                    </span>
                  </div>
                  <span className="bullet-value">
                    {historicalAnalogue?.concise_inference || (
                      historicalAnalogue?.available === false
                        ? 'Historical health-impact analysis temporarily unavailable.'
                        : 'Mortality-informed historical analysis indicates elevated heat-health burden under similar thermal conditions.'
                    )}
                  </span>
                </li>

                <li className="bulletin-item highlight-action">
                  <span className="bullet-label">● Recommended Action</span>
                  <span className="bullet-value action-text">{bulletin.recommended_action}</span>
                </li>

                <li className="bulletin-item peak-time">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Clock size={13} style={{ color: 'var(--risk-caution)' }} />
                    <span className="bullet-label">● Peak Period</span>
                  </div>
                  <span className="bullet-value peak-badge">
                    {bulletin.peak_period ? bulletin.peak_period.replace(/[\ufffd]/g, '–') : '12:00 PM – 4:00 PM'}
                  </span>
                </li>
              </ul>
            ) : null}
          </div>

          <div className="bulletin-footer-meta">
            <span>Environmental Base: Level {selectedZone.weight}/5</span>
            <span>Profile Index: {impactData?.profile_score || selectedZone.risk_score}</span>
          </div>
        </section>

        {/* Conditional Health Action Plan (Visible ONLY for Danger, Extreme Danger, or Severe) */}
        {isHighRisk && (
          <section 
            className="dashboard-card health-action-plan-card" 
            style={{ borderLeft: `4px solid ${selectedZone.color}` }}
            aria-label="Targeted Municipal Health Action Plan"
          >
            <div className="action-plan-header">
              <div className="action-plan-title-group">
                <ShieldAlert size={16} style={{ color: selectedZone.color }} />
                <span className="card-title">HEALTH ACTION PLAN — {selectedZone.name.toUpperCase()}</span>
              </div>
              <div 
                className="action-plan-status-badge"
                style={{ 
                  backgroundColor: `${selectedZone.color}20`, 
                  color: selectedZone.color, 
                  border: `1px solid ${selectedZone.color}60` 
                }}
              >
                <span>CURRENT RISK: <strong>{selectedZone.category.toUpperCase()}</strong></span>
              </div>
            </div>

            <div className="action-plan-subheading">
              <span>Targeted Directives for <strong>{POPULATION_PROFILES.find(p => p.id === selectedProfile)?.name}</strong> (WBGT {selectedZone.wbgt}°C):</span>
            </div>

            <ul className="action-plan-list">
              {getActionPlanDirectives(selectedProfile, selectedZone.category).map((directive, idx) => (
                <li key={idx} className="action-plan-item">
                  <span className="action-bullet-dot" style={{ backgroundColor: selectedZone.color }}></span>
                  <span className="action-directive-text">{directive}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Live Thermal Telemetry Card with Manual Refresh Button */}
        <section className="dashboard-card stat-card telemetry-card" aria-label="Thermal Stress Telemetry">
          <div className="card-header telemetry-header">
            <div className="card-title-group">
              <Thermometer size={16} style={{ color: 'var(--accent-primary)' }} />
              <span className="card-title">LIVE DISTRICT THERMAL TELEMETRY</span>
            </div>
            
            {/* Manual Refresh Button & Status Indicator */}
            <div className="telemetry-header-controls">
              {refreshStatus ? (
                <span className={`refresh-feedback-text ${refreshStatus.includes('failed') ? 'error' : 'success'}`}>
                  {refreshStatus}
                </span>
              ) : (
                <span className="telemetry-source-meta">
                  Open-Meteo Feed {lastUpdated ? `• ${lastUpdated}` : ''}
                </span>
              )}
              <button 
                id="telemetry-refresh-btn"
                className={`manual-refresh-icon-btn ${isRefreshing ? 'refreshing' : ''}`}
                onClick={handleManualRefresh}
                disabled={isRefreshing}
                title="Refresh live district telemetry from Open-Meteo"
              >
                <RotateCw size={13} className={isRefreshing ? 'spin-icon' : ''} />
              </button>
            </div>
          </div>

          {/* Dynamic Sun / Thermal Centerpiece & Weather Values */}
          <WeatherHeatVisual
            zone={selectedZone}
            compact={true}
          />
        </section>

      </div>

      {/* Right ~42% South India District Choropleth Map */}
      <section aria-label="Interactive South India Heat Map" className="right-map-stack">
        <IndiaHeatMap
          zones={zones}
          selectedZone={selectedZone}
          onSelectZone={onSelectZone}
        />
      </section>
    </div>
  );
}
