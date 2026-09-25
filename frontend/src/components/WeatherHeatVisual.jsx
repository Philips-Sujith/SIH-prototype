import React, { useMemo, useState, useEffect } from 'react';
import { 
  Flame, 
  Droplets, 
  Activity, 
  Wind, 
  ThermometerSun,
  Gauge
} from 'lucide-react';
import { getThermalIntensity } from '../utils/thermalColorRamp';

/**
 * Determine if current local time is night in South India (IST).
 * Night hours: 6:30 PM (18:30) or later, OR before 6:00 AM (06:00).
 * Prioritizes district observation_time if available, with live client-clock fallback in Asia/Kolkata.
 */
function checkIsNightTime(observationTime) {
  try {
    let date = new Date();
    if (observationTime && typeof observationTime === 'string') {
      const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(observationTime);
      date = hasTimezone
        ? new Date(observationTime)
        : new Date(`${observationTime}+05:30`);
      if (Number.isNaN(date.getTime())) date = new Date();
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
function getSunDynamics(wbgtValue, tempValue, isNight = false) {
  const wbgt = Number(wbgtValue ?? 29.5);
  const temp = Number(tempValue ?? 32.0);
  const intensity = getThermalIntensity(wbgt); // 0.0 (<=24°C) to 1.0 (>=38°C)

  // Night Mode: fixed vibrant electric blue palette that visually reads as "cool/night mode"
  if (isNight) {
    const nightBlue = '#0284c7';     // Rich saturated electric azure blue
    const darkEdge = '#0369a1';      // Defined boundary stop
    const electricBlue = '#0ea5e9';  // Saturated blue
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
  const temp = Number(zone?.temperature ?? zone?.temp ?? 32.0);
  const humidity = Number(zone?.humidity ?? zone?.rh ?? 60.0);
  const wbgt = Number(zone?.wbgt ?? 30.0);
  const heatIndex = Number(zone?.heat_index ?? zone?.hi ?? 34.0);
  const windSpeed = Number(zone?.wind_speed ?? zone?.wind ?? 3.5);
  const utci = Number(zone?.utci ?? 30.0);
  const heatStressScore = Number(zone?.heat_stress_score ?? Math.min(100, Math.round(wbgt * 2.2)));

  // Automatic real-time day/night detection with 30s interval for live boundary transitions
  const [isNight, setIsNight] = useState(() => checkIsNightTime(zone?.observation_time));

  useEffect(() => {
    setIsNight(checkIsNightTime(zone?.observation_time));
    const timer = setInterval(() => {
      setIsNight(checkIsNightTime(zone?.observation_time));
    }, 30000);
    return () => clearInterval(timer);
  }, [zone?.observation_time]);

  // Continuous Sun dynamics (vibrant blue at night, gold-to-crimson heat scale in daytime)
  const dynamics = useMemo(() => {
    return getSunDynamics(wbgt, temp, isNight);
  }, [wbgt, temp, isNight]);

  // 16 evenly spaced rays (8 primary, 8 secondary) strictly at 22.5° intervals around center (0,0)
  const rays = useMemo(() => {
    return Array.from({ length: 16 }, (_, i) => ({
      deg: i * 22.5,
      isPrimary: i % 2 === 0
    }));
  }, []);

  if (!zone) return null;

  return (
    <div className="telemetry-content-wrapper">
      {/* 
        TASK 1 ARCHITECTURE:
        <SolarVisualization> (flex column, align-items: center, min-height ~195px)
          <SunGraphic />                  <!-- fixed square 128x128 bounding box, 100% symmetric -->
          <div className="solar-gap" />   <!-- deliberate 14px small gap -->
          <AmbientTemperature />          <!-- 25.9°C shared center axis -->
          <AmbientLabel />                <!-- AMBIENT TEMPERATURE -->
        </SolarVisualization>
      */}
      <div 
        className="solar-visualization temperature-section"
        style={{
          '--sun-accent': dynamics.accentColor
        }}
      >
        <div className="sun-graphic">
          <svg 
            className="sun-svg" 
            viewBox="-64 -64 128 128" 
            preserveAspectRatio="xMidYMid meet"
            aria-hidden="true"
          >
            <defs>
              {/* White-hot Solar Core to Thermal Rim Radial Gradient */}
              <radialGradient id="sunCoreGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={dynamics.coreStop0} stopOpacity="1" />
                <stop offset="35%" stopColor={dynamics.coreStop1} stopOpacity="0.96" />
                <stop offset="70%" stopColor={dynamics.coreStop2} stopOpacity="0.92" />
                <stop offset="100%" stopColor={dynamics.coreRim} stopOpacity="0.90" />
              </radialGradient>

              {/* Pulsing Solar Coronal Aura (Breathing Halo) */}
              <radialGradient id="sunAuraGradient" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={dynamics.haloColor} stopOpacity={dynamics.haloMaxOp} />
                <stop offset="45%" stopColor={dynamics.haloColor} stopOpacity={Number(dynamics.haloMaxOp) * 0.45} />
                <stop offset="80%" stopColor={dynamics.haloColor} stopOpacity={Number(dynamics.haloMaxOp) * 0.10} />
                <stop offset="100%" stopColor={dynamics.haloColor} stopOpacity="0" />
              </radialGradient>

              {/* Convection Heat Distortion Line Gradient */}
              <linearGradient id="heatHazeGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor={dynamics.coreRim} stopOpacity="0" />
                <stop offset="25%" stopColor={dynamics.coreRim} stopOpacity="0.35" />
                <stop offset="50%" stopColor={dynamics.coreRim} stopOpacity="0.75" />
                <stop offset="75%" stopColor={dynamics.coreRim} stopOpacity="0.35" />
                <stop offset="100%" stopColor={dynamics.coreRim} stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Layer 1: Outer Halo (Breathing effect strictly centered at 0, 0) */}
            <circle 
              cx="0" 
              cy="0" 
              r="49" 
              fill="url(#sunAuraGradient)"
            >
              <animate 
                attributeName="r" 
                values={`${dynamics.haloMinR};${dynamics.haloMaxR};${dynamics.haloMinR}`} 
                dur={dynamics.durCorona} 
                repeatCount="indefinite" 
              />
              <animate 
                attributeName="opacity" 
                values={`${dynamics.haloMinOp};${dynamics.haloMaxOp};${dynamics.haloMinOp}`} 
                dur={dynamics.durCorona} 
                repeatCount="indefinite" 
              />
            </circle>

            {/* Layer 2: Concentric Radiance Ring (centered at 0, 0) */}
            <circle 
              cx="0" 
              cy="0" 
              r="37" 
              fill="none" 
              stroke={dynamics.haloColor} 
              strokeWidth="1.2" 
              strokeOpacity="0.45" 
              strokeDasharray="3 4"
            >
              <animate 
                attributeName="stroke-opacity" 
                values="0.30;0.55;0.30" 
                dur={dynamics.durCorona} 
                repeatCount="indefinite" 
              />
            </circle>

            {/* Layer 3: Solar Rays (Slow continuous 360° rotation strictly centered around 0, 0) */}
            <g>
              <animateTransform 
                attributeName="transform" 
                type="rotate" 
                from="0 0 0" 
                to="360 0 0" 
                dur={dynamics.durRays} 
                repeatCount="indefinite" 
              />
              {rays.map(({ deg, isPrimary }, i) => (
                <line
                  key={i}
                  x1="0"
                  y1="-20"
                  x2="0"
                  y2={isPrimary ? dynamics.rayPrimaryLen : dynamics.raySecondaryLen}
                  stroke={isPrimary ? dynamics.rayPrimary : dynamics.raySecondary}
                  strokeWidth={isPrimary ? (dynamics.rayWidthPrimary || "2.4") : (dynamics.rayWidthSecondary || "1.6")}
                  strokeLinecap="round"
                  opacity={isPrimary ? dynamics.rayOpacityPrimary : dynamics.rayOpacitySecondary}
                  transform={`rotate(${deg})`}
                />
              ))}
            </g>

            {/* Layer 4: Solar Core Disk (Centered at 0, 0 with subtle brightness breathing and crisp boundary) */}
            <circle 
              cx="0" 
              cy="0" 
              r="20" 
              fill="url(#sunCoreGradient)"
              stroke={dynamics.coreRim}
              strokeWidth={dynamics.isNight ? "1.2" : "0.5"}
              strokeOpacity={dynamics.isNight ? "0.95" : "0.6"}
            >
              <animate 
                attributeName="opacity" 
                values="0.94;1;0.94" 
                dur={dynamics.durDisk} 
                repeatCount="indefinite" 
              />
            </circle>

            {/* Layer 5: Symmetrically Centered Heat Shimmer Lines */}
            <g className="anim-heat-shimmer">
              <path 
                className="heat-wave-line wave-1"
                d="M -36 40 Q -18 37, 0 40 T 36 40" 
                fill="none" 
                stroke="url(#heatHazeGrad)" 
                strokeWidth="1.3" 
                strokeLinecap="round"
              />
              <path 
                className="heat-wave-line wave-2"
                d="M -30 46 Q -15 49, 0 46 T 30 46" 
                fill="none" 
                stroke="url(#heatHazeGrad)" 
                strokeWidth="1.4" 
                strokeLinecap="round"
                opacity="0.85"
              />
              <path 
                className="heat-wave-line wave-3"
                d="M -24 52 Q -12 50, 0 52 T 24 52" 
                fill="none" 
                stroke="url(#heatHazeGrad)" 
                strokeWidth="1.2" 
                strokeLinecap="round"
                opacity="0.65"
              />
            </g>
          </svg>
        </div>

        {/* Visual Group: Temperature value and AMBIENT TEMPERATURE label */}
        <div className="ambient-temp-group">
          <div className="ambient-temperature">
            <span className="temp-num">{temp.toFixed(1)}</span>
            <span className="temp-unit">°C</span>
          </div>
          <div className="ambient-label">AMBIENT TEMPERATURE</div>
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
              <span className="metric-num">{utci.toFixed(1)}</span>
              <span className="metric-unit">°C</span>
            </div>
          </div>

          <div className="metric-divider" />

          <div className="metric-cell highlight-cell">
            <div className="metric-cell-top">
              <Flame size={13} style={{ color: dynamics.accentColor }} />
              <span className="metric-cell-label" style={{ color: dynamics.accentColor }}>WBGT</span>
            </div>
            <div className="metric-cell-val">
              <span className="metric-num" style={{ color: dynamics.accentColor }}>{wbgt.toFixed(1)}</span>
              <span className="metric-unit" style={{ color: dynamics.accentColor }}>°C</span>
            </div>
          </div>

          <div className="metric-divider" />

          <div className="metric-cell">
            <div className="metric-cell-top">
              <Activity size={13} style={{ color: '#f59e0b' }} />
              <span className="metric-cell-label">HEAT STRESS</span>
            </div>
            <div className="metric-cell-val">
              <span className="metric-num">{heatStressScore}</span>
              <span className="metric-unit">/100</span>
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
              <span className="sec-num">{windSpeed.toFixed(1)}</span>
              <span className="sec-unit">m/s</span>
            </span>
          </div>

          <div className="metric-divider secondary-divider" />

          <div className="secondary-cell">
            <span className="sec-label-group">
              <ThermometerSun size={12} style={{ color: 'var(--text-muted)' }} />
              <span className="sec-label">HEAT INDEX</span>
            </span>
            <span className="sec-val-group">
              <span className="sec-num">{heatIndex.toFixed(1)}</span>
              <span className="sec-unit">°C</span>
            </span>
          </div>

          <div className="metric-divider secondary-divider" />

          <div className="secondary-cell">
            <span className="sec-label-group">
              <Droplets size={12} style={{ color: 'var(--text-muted)' }} />
              <span className="sec-label">HUMIDITY</span>
            </span>
            <span className="sec-val-group">
              <span className="sec-num">{humidity.toFixed(0)}</span>
              <span className="sec-unit">%</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
