import React, { useMemo, useState, useEffect, useRef } from 'react';
import { 
  Flame, 
  Droplets, 
  Activity, 
  Wind, 
  ThermometerSun,
  Gauge,
  Sparkles,
  ChevronDown
} from 'lucide-react';
import { getThermalIntensity } from '../utils/thermalColorRamp';
import charNormalWebp from '../assets/character-normal.webp';
import charHeatWebp from '../assets/character-heat.webp';
import charNightWebp from '../assets/character-night.webp';
import charNormalPng from '../assets/character-normal.png';
import charHeatPng from '../assets/character-heat.png';
import charNightPng from '../assets/character-night.png';

/**
 * Determine if current local time is night in South India (IST).
 * Night hours: 6:30 PM (18:30) or later, OR before 6:00 AM (06:00) IST.
 * Evaluates live Indian Standard Time (Asia/Kolkata).
 * Supports window.__CLIMATEGUARD_TIME_OVERRIDE__ for testing/simulation.
 */
function checkIsNightTime(customTime = null) {
  try {
    let date = new Date();

    // Support optional global devtools simulation override (e.g. window.__CLIMATEGUARD_TIME_OVERRIDE__ = '14:00')
    if (typeof window !== 'undefined' && window.__CLIMATEGUARD_TIME_OVERRIDE__) {
      customTime = window.__CLIMATEGUARD_TIME_OVERRIDE__;
    }

    if (customTime instanceof Date) {
      date = customTime;
    } else if (typeof customTime === 'string') {
      const parsed = new Date(customTime);
      if (!Number.isNaN(parsed.getTime())) {
        date = parsed;
      }
    }

    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false
    });
    const parts = formatter.formatToParts(date);
    const hour = parseInt(parts.find((p) => p.type === 'hour')?.value || '12', 10);
    const minute = parseInt(parts.find((p) => p.type === 'minute')?.value || '0', 10);
    const totalMinutes = hour * 60 + minute;
    // Night hours: 6:30 PM (18:30) or later, OR before 6:00 AM (06:00) IST
    return totalMinutes >= 18 * 60 + 30 || totalMinutes < 6 * 60;
  } catch {
    const now = new Date();
    const hour = now.getHours();
    const minute = now.getMinutes();
    const totalMinutes = hour * 60 + minute;
    return totalMinutes >= 18 * 60 + 30 || totalMinutes < 6 * 60;
  }
}

/**
 * Continuous Solar Palette & Dynamics Calculator
 * - Night Mode (after 6:30 PM or before 6:00 AM): Fixed vibrant electric blue palette (cool night mode, does NOT respond to thermal severity).
 * - Day Mode: Warm gold at Low (<28°C), amber/yellow at Caution (28-30°C), orange at Danger (30-32°C), orange-red at Extreme (32-35°C), deep crimson at Severe (>35°C).
 * Glow radius/opacity, ray intensity, and shimmer strength scale proportionally from numeric intensity (0-1).
 */
function getSunDynamics(wbgtValue, _tempValue, isNight = false) {
  const wbgt = Number(wbgtValue ?? 29.5);
  const intensity = getThermalIntensity(wbgt); // 0.0 (<=24°C) to 1.0 (>=38°C)

  // Night Mode: fixed vibrant electric blue palette that visually reads as "cool/night mode"
  if (isNight) {
    const nightBlue = '#0284c7';     // Rich saturated electric azure blue
    const darkEdge = '#0369a1';      // Defined boundary stop
    const brightCyan = '#38bdf8';    // Vibrant cyan-blue
    const skyCore = '#bae6fd';       // Crisp radiant core stop

    return {
      intensity: 0.20,
      isNight: true,
      coreStop0: skyCore,            // Radiant core stop (#bae6fd)
      coreStop1: brightCyan,         // Vibrant electric cyan-blue (#38bdf8)
      coreStop2: nightBlue,          // Saturated azure blue (#0284c7)
      coreRim: darkEdge,             // Defined crisp boundary stop (#0369a1)
      haloColor: nightBlue,          // Soft ambient outer glow (#0284c7)
      rayPrimary: brightCyan,        // Matching coreStop1 (#38bdf8)
      raySecondary: nightBlue,       // Matching coreStop2 (#0284c7)
      accentColor: brightCyan,
      // Retain the exact same premium layered animation dynamics
      durDisk: '5.0s',
      durCorona: '5.5s',
      durRays: '38s',
      durWaves: '7.0s',
      haloMinR: '46.0',
      haloMaxR: '52.0',
      haloMinOp: '0.18',             // Softer diffuse outer glow so rays remain distinct
      haloMaxOp: '0.38',
      rayPrimaryLen: -39,
      raySecondaryLen: -31,
      rayWidthPrimary: '2.6',
      rayWidthSecondary: '1.8',
      rayOpacityPrimary: '1.0',
      rayOpacitySecondary: '0.90'
    };
  }

  // Daytime: standard continuous gold-to-crimson heat scale
  const ramp = [
    { t: 0.00, core: '#fffdf0', mid: '#fef08a', rim: '#ca8a04', halo: '#eab308', ray1: '#fef08a', ray2: '#fde047' }, // Low (warm gold)
    { t: 0.28, core: '#fef9c3', mid: '#fde047', rim: '#d97706', halo: '#f59e0b', ray1: '#fde047', ray2: '#f59e0b' }, // Caution (amber)
    { t: 0.43, core: '#fffbeb', mid: '#fbbf24', rim: '#ea580c', halo: '#f97316', ray1: '#fcd34d', ray2: '#f97316' }, // Danger (orange)
    { t: 0.57, core: '#ffedd5', mid: '#f97316', rim: '#dc2626', halo: '#ef4444', ray1: '#fb923c', ray2: '#ef4444' }, // Extreme (orange-red)
    { t: 0.78, core: '#fee2e2', mid: '#ef4444', rim: '#b91c1c', halo: '#dc2626', ray1: '#f87171', ray2: '#dc2626' }, // Severe (vivid red)
    { t: 1.00, core: '#fecdd3', mid: '#dc2626', rim: '#881337', halo: '#991b1b', ray1: '#f43f5e', ray2: '#991b1b' }  // Severe Max (deep crimson)
  ];

  // Find nearest segment for continuous interpolation
  let seg = ramp[0];
  let nextSeg = ramp[1];
  let factor = 0;

  for (let i = 0; i < ramp.length - 1; i++) {
    if (intensity >= ramp[i].t && intensity <= ramp[i + 1].t) {
      seg = ramp[i];
      nextSeg = ramp[i + 1];
      factor = (intensity - seg.t) / (nextSeg.t - seg.t);
      break;
    }
  }
  if (intensity >= 1.0) {
    seg = ramp[ramp.length - 1];
    nextSeg = seg;
    factor = 0;
  }

  // Linear color interpolation helper
  const lerpColor = (c1, c2, f) => {
    const r1 = parseInt(c1.slice(1, 3), 16), g1 = parseInt(c1.slice(3, 5), 16), b1 = parseInt(c1.slice(5, 7), 16);
    const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
    const r = Math.round(r1 + (r2 - r1) * f);
    const g = Math.round(g1 + (g2 - g1) * f);
    const b = Math.round(b1 + (b2 - b1) * f);
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
  };

  const coreStop0 = '#ffffff';
  const coreStop1 = lerpColor(seg.core, nextSeg.core, factor);
  const coreStop2 = lerpColor(seg.mid, nextSeg.mid, factor);
  const coreRim   = lerpColor(seg.rim, nextSeg.rim, factor);
  const haloColor = lerpColor(seg.halo, nextSeg.halo, factor);
  const rayPrimary = lerpColor(seg.ray1, nextSeg.ray1, factor);
  const raySecondary = lerpColor(seg.ray2, nextSeg.ray2, factor);

  return {
    intensity,
    isNight: false,
    coreStop0,
    coreStop1,
    coreStop2,
    coreRim,
    haloColor,
    rayPrimary,
    raySecondary,
    accentColor: haloColor,
    // Smooth dynamic animations driven proportionally by continuous intensity
    durDisk: `${(5.5 - intensity * 2.5).toFixed(1)}s`,
    durCorona: `${(6.0 - intensity * 2.8).toFixed(1)}s`,
    durRays: `${Math.round(44 - intensity * 24)}s`,
    durWaves: `${(7.5 - intensity * 3.5).toFixed(1)}s`,
    haloMinR: (46 + intensity * 2).toFixed(1),
    haloMaxR: (52 + intensity * 3).toFixed(1),
    haloMinOp: (0.45 + intensity * 0.25).toFixed(2),
    haloMaxOp: (0.80 + intensity * 0.20).toFixed(2),
    rayPrimaryLen: Math.round(-38 - intensity * 6),
    raySecondaryLen: Math.round(-30 - intensity * 4),
    rayWidthPrimary: '2.4',
    rayWidthSecondary: '1.6',
    rayOpacityPrimary: (0.88 + intensity * 0.10).toFixed(2),
    rayOpacitySecondary: (0.55 + intensity * 0.15).toFixed(2)
  };
}

export default function WeatherHeatVisual({ zone }) {
  const rawTemp = zone?.temperature ?? zone?.temp;
  const rawHumidity = zone?.humidity ?? zone?.rh;
  const rawWbgt = zone?.wbgt;
  const rawHeatIndex = zone?.heat_index ?? zone?.hi;
  const rawWind = zone?.wind_speed ?? zone?.wind;
  const rawUtci = zone?.utci;
  const rawHss = zone?.heat_stress_score;

  const hasTelemetry = rawWbgt != null && rawTemp != null;

  const temp = hasTelemetry ? Number(rawTemp) : null;
  const humidity = rawHumidity != null ? Number(rawHumidity) : null;
  const wbgt = hasTelemetry ? Number(rawWbgt) : null;
  const heatIndex = rawHeatIndex != null ? Number(rawHeatIndex) : null;
  const windSpeed = rawWind != null ? Number(rawWind) : null;
  const utci = rawUtci != null ? Number(rawUtci) : null;
  const heatStressScore = rawHss != null ? Number(rawHss) : (wbgt != null ? Math.min(100, Math.round(wbgt * 2.2)) : null);

  // Automatic real-time day/night detection with recurring interval
  // Evaluates live Indian Standard Time (Asia/Kolkata) every 30s so the sun transitions smoothly at 6:30 PM & 6:00 AM
  const [isNight, setIsNight] = useState(() => checkIsNightTime());

  useEffect(() => {
    const updateNightState = () => {
      setIsNight(checkIsNightTime());
    };

    updateNightState();
    const timer = setInterval(updateNightState, 30000);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        updateNightState();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  // Continuous Sun dynamics:
  // - Real/cached data: daytime severity colors vs night electric blue
  // - Unavailable data: browser India time decides: night -> blue ambient orb, day -> neutral mild golden sun
  const dynamics = useMemo(() => {
    if (!hasTelemetry) {
      if (isNight) {
        return getSunDynamics(null, null, true);
      }
      return getSunDynamics(25.0, 28.0, false);
    }
    return getSunDynamics(wbgt, temp, isNight);
  }, [hasTelemetry, wbgt, temp, isNight]);

  // Demo Mode for presentation testing (overrides only visual character & celestial badge)
  const [demoState, setDemoState] = useState(null); // null = Live, 'normal', 'caution', 'danger', 'severe', 'night'
  const [demoOpen, setDemoOpen] = useState(false);
  const demoRef = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (demoRef.current && !demoRef.current.contains(e.target)) {
        setDemoOpen(false);
      }
    };
    if (demoOpen) {
      document.addEventListener('pointerdown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('pointerdown', handleOutsideClick);
    };
  }, [demoOpen]);

  // Determine effective night status (if demo state selected, 'night' forces night, others daytime)
  const effectiveIsNight = demoState ? demoState === 'night' : isNight;

  // Adaptive character presentation state:
  // Priority: Demo override -> Actual thermal state -> Actual day/night state
  const characterState = useMemo(() => {
    if (demoState) return demoState;
    if (isNight) return 'night';
    const cat = (zone?.category || '').toLowerCase();
    const currentWbgt = wbgt ?? 26.0;
    if (currentWbgt >= 35 || cat === 'severe' || cat === 'extreme') return 'severe';
    if (currentWbgt >= 32 || cat === 'high' || cat === 'danger') return 'danger';
    if (currentWbgt >= 28 || cat === 'caution' || cat === 'moderate') return 'caution';
    return 'normal';
  }, [demoState, isNight, zone?.category, wbgt]);

  const isHeatState = characterState === 'severe' || characterState === 'danger';

  // Contextual sun color: demo override vs live calculated dynamics
  const effectiveCelestialColor = useMemo(() => {
    if (demoState) {
      if (demoState === 'severe') return '#dc2626';
      if (demoState === 'danger') return '#ea580c';
      if (demoState === 'caution') return '#f59e0b';
      return '#eab308';
    }
    return dynamics.accentColor || '#f59e0b';
  }, [demoState, dynamics.accentColor]);

  const { characterWebp, characterPng, characterAlt } = useMemo(() => {
    if (characterState === 'night') {
      return {
        characterWebp: charNightWebp,
        characterPng: charNightPng,
        characterAlt: 'Nighttime Sleep Character in Pajamas'
      };
    }
    if (characterState === 'severe' || characterState === 'danger') {
      return {
        characterWebp: charHeatWebp,
        characterPng: charHeatPng,
        characterAlt: 'Heat-stressed Character Struggling with Thermal Fatigue'
      };
    }
    return {
      characterWebp: charNormalWebp,
      characterPng: charNormalPng,
      characterAlt: 'Comfortable Standing Character'
    };
  }, [characterState]);

  if (!zone) return null;

  return (
    <div className="telemetry-content-wrapper">
      <div 
        className="solar-visualization temperature-section"
        style={{
          '--sun-accent': dynamics.accentColor
        }}
      >
        {/* LEFT COLUMN: Temperature value and AMBIENT TEMPERATURE subtitle */}
        <div className="ambient-temp-group">
          <div className="ambient-temperature">
            <span className="temp-num">{temp != null ? temp.toFixed(1) : '—'}</span>
            {temp != null && <span className="temp-unit">°C</span>}
          </div>
          <div className="ambient-label">AMBIENT TEMPERATURE</div>
        </div>

        {/* RIGHT COLUMN: Adaptive Thermal Character & Contextual Celestial Indicator */}
        <div className="telemetry-character-scene">
          {/* Small Unobtrusive DEMO MODE Selector */}
          <div className="character-demo-control" ref={demoRef}>
            <button
              id="character-demo-btn"
              type="button"
              className={`demo-pill-btn ${demoState ? `active ${demoState}` : ''}`}
              onClick={() => setDemoOpen((prev) => !prev)}
              title="Demonstration state override for SIH presentation"
              aria-label="Character presentation demo mode"
            >
              <Sparkles size={10} className="demo-sparkle-icon" />
              <span>{demoState ? `DEMO: ${demoState === 'caution' ? 'MODERATE' : demoState === 'danger' ? 'HIGH' : demoState === 'severe' ? 'EXTREME' : demoState.toUpperCase()}` : 'DEMO'}</span>
              <ChevronDown size={10} className={`demo-chevron ${demoOpen ? 'open' : ''}`} />
            </button>

            {demoOpen && (
              <div className="demo-dropdown-menu" role="menu">
                <button
                  type="button"
                  className={`demo-opt ${!demoState ? 'selected' : ''}`}
                  onClick={() => { setDemoState(null); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">⚡</span> Live (Exit Demo)
                </button>
                <button
                  type="button"
                  className={`demo-opt ${demoState === 'normal' ? 'selected' : ''}`}
                  onClick={() => { setDemoState('normal'); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">🟢</span> Normal
                </button>
                <button
                  type="button"
                  className={`demo-opt ${demoState === 'caution' ? 'selected' : ''}`}
                  onClick={() => { setDemoState('caution'); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">🟡</span> Moderate
                </button>
                <button
                  type="button"
                  className={`demo-opt ${demoState === 'danger' ? 'selected' : ''}`}
                  onClick={() => { setDemoState('danger'); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">🟠</span> High
                </button>
                <button
                  type="button"
                  className={`demo-opt ${demoState === 'severe' ? 'selected' : ''}`}
                  onClick={() => { setDemoState('severe'); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">🔴</span> Extreme
                </button>
                <button
                  type="button"
                  className={`demo-opt ${demoState === 'night' ? 'selected' : ''}`}
                  onClick={() => { setDemoState('night'); setDemoOpen(false); }}
                >
                  <span className="demo-opt-dot">🌙</span> Night
                </button>
              </div>
            )}
          </div>

          {/* Small Contextual Celestial Indicator (Upper-Right) */}
          <div className="celestial-badge" title={effectiveIsNight ? 'Night Time Mode' : 'Live Solar & Thermal Intensity'}>
            {effectiveIsNight ? (
              <svg className="celestial-moon-svg" viewBox="0 0 24 24" width="28" height="28" fill="none" aria-hidden="true">
                <path
                  d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
                  fill="#38bdf8"
                  stroke="#7dd3fc"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="18" cy="5" r="1.2" fill="#bae6fd" className="star-twinkle" />
                <circle cx="14" cy="2.5" r="0.9" fill="#bae6fd" className="star-twinkle-delay" />
              </svg>
            ) : (
              <svg className="celestial-sun-svg" viewBox="-16 -16 32 32" width="30" height="30" aria-hidden="true">
                <circle cx="0" cy="0" r="7" fill={effectiveCelestialColor} />
                {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
                  <line
                    key={deg}
                    x1="0"
                    y1="-9"
                    x2="0"
                    y2="-13"
                    stroke={effectiveCelestialColor}
                    strokeWidth="2"
                    strokeLinecap="round"
                    transform={`rotate(${deg})`}
                  />
                ))}
              </svg>
            )}
          </div>

          {/* Full-Body Character Representation with Dynamic State */}
          <div className={`character-wrapper state-${characterState}`}>
            {/* Animated sleep Zzz effect for night state */}
            {effectiveIsNight && (
              <div className="sleep-z-container" aria-hidden="true">
                <span className="sleep-z z-1">z</span>
                <span className="sleep-z z-2">z</span>
                <span className="sleep-z z-3">Z</span>
              </div>
            )}

            {/* Animated sweat droplets for heat state */}
            {isHeatState && (
              <div className="sweat-drops-container" aria-hidden="true">
                <span className="sweat-drop drop-1">💧</span>
                <span className="sweat-drop drop-2">💧</span>
              </div>
            )}

            {/* Responsive Picture with WebP and PNG Fallback */}
            <picture className="character-picture">
              <source srcSet={characterWebp} type="image/webp" />
              <img
                src={characterPng}
                alt={characterAlt}
                className={`telemetry-character-img anim-${characterState}`}
                loading="eager"
              />
            </picture>

            {/* Soft Ground Shadow for realism */}
            <div className="character-ground-shadow" aria-hidden="true" />
          </div>
        </div>
      </div>

      {/* Metrics Grid (Remaining 50% Vertical Split) */}
      <div className="metrics-grid">
        <div className="metrics-primary-row">
          <div className="metric-cell">
            <div className="metric-cell-top">
              <Gauge size={13} style={{ color: 'var(--accent-primary)' }} />
              <span className="metric-cell-label">UTCI</span>
            </div>
            <div className="metric-cell-val">
              <span className="metric-num">{utci != null ? utci.toFixed(1) : '—'}</span>
              {utci != null && <span className="metric-unit">°C</span>}
            </div>
          </div>

          <div className="metric-divider" />

          <div className="metric-cell highlight-cell">
            <div className="metric-cell-top">
              <Flame size={13} style={{ color: dynamics.accentColor }} />
              <span className="metric-cell-label" style={{ color: dynamics.accentColor }}>WBGT</span>
            </div>
            <div className="metric-cell-val">
              <span className="metric-num" style={{ color: dynamics.accentColor }}>{wbgt != null ? wbgt.toFixed(1) : '—'}</span>
              {wbgt != null && <span className="metric-unit" style={{ color: dynamics.accentColor }}>°C</span>}
            </div>
          </div>

          <div className="metric-divider" />

          <div className="metric-cell">
            <div className="metric-cell-top">
              <Activity size={13} style={{ color: '#f59e0b' }} />
              <span className="metric-cell-label">HEAT STRESS</span>
            </div>
            <div className="metric-cell-val">
              <span className="metric-num">{heatStressScore != null ? heatStressScore : '—'}</span>
              {heatStressScore != null && <span className="metric-unit">/100</span>}
            </div>
          </div>
        </div>

        <div className="metrics-secondary-row">
          <div className="secondary-cell">
            <span className="sec-label-group">
              <Wind size={12} style={{ color: 'var(--text-muted)' }} />
              <span className="sec-label">WIND</span>
            </span>
            <span className="sec-val-group">
              <span className="sec-num">{windSpeed != null ? windSpeed.toFixed(1) : '—'}</span>
              {windSpeed != null && <span className="sec-unit">m/s</span>}
            </span>
          </div>

          <div className="metric-divider secondary-divider" />

          <div className="secondary-cell">
            <span className="sec-label-group">
              <ThermometerSun size={12} style={{ color: 'var(--text-muted)' }} />
              <span className="sec-label">HEAT INDEX</span>
            </span>
            <span className="sec-val-group">
              <span className="sec-num">{heatIndex != null ? heatIndex.toFixed(1) : '—'}</span>
              {heatIndex != null && <span className="sec-unit">°C</span>}
            </span>
          </div>

          <div className="metric-divider secondary-divider" />

          <div className="secondary-cell">
            <span className="sec-label-group">
              <Droplets size={12} style={{ color: 'var(--text-muted)' }} />
              <span className="sec-label">HUMIDITY</span>
            </span>
            <span className="sec-val-group">
              <span className="sec-num">{humidity != null ? humidity.toFixed(0) : '—'}</span>
              {humidity != null && <span className="sec-unit">%</span>}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
