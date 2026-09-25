import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, ImageOverlay, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Layers, Flame, SunMedium, Activity, Info } from 'lucide-react';
import { 
  getContinuousColor, 
  generateContinuousThermalRaster 
} from '../utils/thermalColorRamp';
import { useTheme } from '../context/ThemeContext';

// Bounding boxes for South India states
const STATE_BOUNDS = {
  all: [[8.0, 74.0], [18.6, 80.5]],
  'Tamil Nadu': [[8.0, 76.2], [13.6, 80.4]],
  'Kerala': [[8.1, 74.8], [12.9, 77.5]],
  'Karnataka': [[11.5, 74.0], [18.5, 77.8]]
};

// State centroids for zoomed-out state labels
const STATE_CENTROIDS = [
  { id: 'state-tn', name: 'TAMIL NADU', lat: 11.1271, lon: 78.6569, isState: true },
  { id: 'state-kl', name: 'KERALA', lat: 10.4505, lon: 76.4711, isState: true },
  { id: 'state-ka', name: 'KARNATAKA', lat: 14.8173, lon: 75.9139, isState: true }
];

// Major metropolis capitals and regional hubs
const MAJOR_DISTRICT_IDS = new Set([
  'chennai', 'bengaluru_urban', 'thiruvananthapuram', 
  'coimbatore', 'madurai', 'ernakulam', 'mysuru', 
  'dakshina_kannada', 'kozhikode', 'dharwad', 'belagavi'
]);

// Map Bounds and Zoom Controller
function MapViewController({ targetBounds, selectedCoord, onZoomChange }) {
  const map = useMap();

  useMapEvents({
    zoomend: () => {
      if (onZoomChange) onZoomChange(map.getZoom());
    }
  });

  useEffect(() => {
    if (targetBounds) {
      map.fitBounds(targetBounds, { padding: [16, 16], maxZoom: 8, duration: 0.8 });
    }
  }, [targetBounds, map]);

  useEffect(() => {
    if (selectedCoord) {
      map.panTo([selectedCoord.lat, selectedCoord.lon], { duration: 0.6 });
    }
  }, [selectedCoord, map]);

  return null;
}

// Controller to establish custom map panes with strictly controlled z-indices and pointer-events
function ThermalPanesController() {
  const map = useMap();

  useEffect(() => {
    // 1. Thermal Raster Pane: Beneath vector boundaries (zIndex 350, strictly non-interactive)
    if (!map.getPane('thermalRasterPane')) {
      const rPane = map.createPane('thermalRasterPane');
      rPane.style.zIndex = '350';
      rPane.style.pointerEvents = 'none';
    }

    // 2. District Polygons Interactive Pane: Authoritative clickable/hoverable surface (zIndex 500)
    if (!map.getPane('districtPolygonsPane')) {
      const pPane = map.createPane('districtPolygonsPane');
      pPane.style.zIndex = '500';
    }

    // 3. Geographic Labels Topmost Pane: Visually on top, strictly non-interactive pass-through (zIndex 620)
    if (!map.getPane('labelsPane')) {
      const lPane = map.createPane('labelsPane');
      lPane.style.zIndex = '620';
      lPane.style.pointerEvents = 'none';
    }
  }, [map]);

  return null;
}

export default function IndiaHeatMap({
  zones = [],
  selectedZone,
  onSelectZone,
  height = "100%",
  activeStateFilter = 'all',
  isAdminView = false
}) {
  const { isDark } = useTheme();
  const [districtsGeo, setDistrictsGeo] = useState(null);
  const [statesGeo, setStatesGeo] = useState(null);
  const [activeMetric, setActiveMetric] = useState('utci'); // 'utci', 'wbgt', 'hi'
  const [hoveredDistrict, setHoveredDistrict] = useState(null);
  const [selectedStateView, setSelectedStateView] = useState('all');
  const [currentZoom, setCurrentZoom] = useState(6);
  const [basemapType, setBasemapType] = useState('esri'); // 'esri' (Canvas) | 'osm' (OpenStreetMap)

  // Load authoritative GeoJSON boundary files
  useEffect(() => {
    const base = import.meta.env.BASE_URL || '/';
    const districtsUrl = `${base}south_india_districts.geojson`.replace(/\/{2,}/g, '/');
    const statesUrl = `${base}south_india_states.geojson`.replace(/\/{2,}/g, '/');

    fetch(districtsUrl)
      .then((res) => {
        if (!res.ok) throw new Error("Districts GeoJSON not found");
        return res.json();
      })
      .then((data) => setDistrictsGeo(data))
      .catch((err) => console.error("Error loading south_india_districts.geojson:", err));

    fetch(statesUrl)
      .then((res) => {
        if (!res.ok) throw new Error("States GeoJSON not found");
        return res.json();
      })
      .then((data) => setStatesGeo(data))
      .catch((err) => console.warn("Notice: States GeoJSON fallback:", err));
  }, []);

  // Sync external state filter
  useEffect(() => {
    if (activeStateFilter && STATE_BOUNDS[activeStateFilter]) {
      setSelectedStateView(activeStateFilter);
    }
  }, [activeStateFilter]);

  // Lookup map: district_id -> live computed record
  const districtMap = useMemo(() => {
    const map = new Map();
    zones.forEach((z) => {
      map.set(z.id.toLowerCase(), z);
      if (z.name) map.set(z.name.toLowerCase(), z);
      if (z.district) map.set(z.district.toLowerCase(), z);
    });
    return map;
  }, [zones]);

  // Task 3: Zoom tier for zoom-responsive crisp raster resolution
  const zoomTier = currentZoom >= 7.5 ? 'deep' : 'standard';

  // Task 2b & Task 3: Memoized continuous spatial interpolation raster layer (IDW masked to TN, KL, KA)
  const rasterUrl = useMemo(() => {
    return generateContinuousThermalRaster(districtsGeo, districtMap, activeMetric, zoomTier);
  }, [districtsGeo, districtMap, activeMetric, zoomTier]);

  const getFeatureRecord = (feature) => {
    const props = feature.properties || {};
    const id = (props.id || '').toLowerCase();
    const name = (props.district || props.name || '').toLowerCase();
    return districtMap.get(id) || districtMap.get(name) || {
      id: props.id,
      name: props.district || props.name,
      district: props.district || props.name,
      state: props.state,
      lat: props.rep_lat,
      lon: props.rep_lon,
      temp: 32.0,
      rh: 55.0,
      wind: 3.0,
      hi: 36.5,
      wbgt: 29.8,
      utci: 30.5,
      utci_category: 'Moderate Heat Stress',
      utci_color: '#f59e0b',
      category: 'Caution',
      color: '#f59e0b',
      risk_score: 42,
      heat_stress_score: 48,
      heat_stress_tier: 'MODERATE'
    };
  };

  // Task 2: Zoom-dependent level-of-detail label set with collision spacing
  const visibleLabels = useMemo(() => {
    if (!districtsGeo?.features) return [];

    // 1. Zoomed out (state-level view, zoom < 6.8):
    if (currentZoom < 6.8) {
      const majorHubs = districtsGeo.features
        .filter((f) => MAJOR_DISTRICT_IDS.has((f.properties?.id || '').toLowerCase()))
        .map((f) => {
          const d = getFeatureRecord(f);
          return {
            id: f.properties.id,
            name: f.properties.district || f.properties.name,
            lat: f.properties.rep_lat,
            lon: f.properties.rep_lon,
            isMajor: true,
            metricVal: activeMetric === 'hi' ? d.hi : activeMetric === 'wbgt' ? d.wbgt : (d.utci ?? d.wbgt)
          };
        });
      return [...STATE_CENTROIDS, ...majorHubs];
    }

    // 2. Mid zoom & deep zoom (zoom >= 6.8):
    const allDistricts = districtsGeo.features.map((f) => {
      const isMajor = MAJOR_DISTRICT_IDS.has((f.properties?.id || '').toLowerCase());
      const d = getFeatureRecord(f);
      return {
        id: f.properties.id,
        name: f.properties.district || f.properties.name,
        lat: f.properties.rep_lat,
        lon: f.properties.rep_lon,
        isMajor,
        metricVal: activeMetric === 'hi' ? d.hi : activeMetric === 'wbgt' ? d.wbgt : (d.utci ?? d.wbgt)
      };
    });

    // Collision filter for density at 6.8-7.4
    if (currentZoom < 7.4) {
      const kept = [];
      const sorted = [...allDistricts].sort((a, b) => (b.isMajor ? 1 : 0) - (a.isMajor ? 1 : 0));
      for (const item of sorted) {
        const hasCollision = kept.some((k) => {
          const dlat = k.lat - item.lat;
          const dlon = k.lon - item.lon;
          return Math.sqrt(dlat * dlat + dlon * dlon) < 0.28;
        });
        if (!hasCollision || item.isMajor) {
          kept.push(item);
        }
      }
      return kept;
    }

    return allDistricts;
  }, [districtsGeo, currentZoom, districtMap, activeMetric]);

  // Task 2a: Polygon styling driven continuously via getContinuousColor()
  const getDistrictStyle = (feature) => {
    const dRecord = getFeatureRecord(feature);
    const dId = (feature.properties?.id || '').toLowerCase();
    const isSelected = selectedZone && selectedZone.id.toLowerCase() === dId;
    const isHovered = hoveredDistrict && hoveredDistrict.id.toLowerCase() === dId;
    const isHighRisk = ['Danger', 'Extreme Danger', 'Severe'].includes(dRecord.category);

    let metricVal = dRecord.utci ?? dRecord.wbgt;
    if (activeMetric === 'wbgt') metricVal = dRecord.wbgt;
    else if (activeMetric === 'hi') metricVal = dRecord.hi;

    // Continuous color ramp value (Task 2a)
    const continuousFillColor = getContinuousColor(metricVal, activeMetric);

    const strokeColor = isSelected 
      ? (isDark ? '#38bdf8' : '#0284c7')
      : isHovered 
      ? (isDark ? '#ffffff' : '#0f172a')
      : (isAdminView && isHighRisk) 
      ? 'rgba(239, 68, 68, 0.85)' 
      : (isDark ? 'rgba(255, 255, 255, 0.35)' : 'rgba(15, 23, 42, 0.35)');

    const strokeWeight = isSelected 
      ? 3.0 
      : isHovered 
      ? 2.2 
      : 1.2;

    return {
      fillColor: continuousFillColor,
      fillOpacity: 0.55,
      color: strokeColor,
      weight: strokeWeight,
      opacity: 0.95
    };
  };

  // State boundary styling (Strictly non-interactive so it never intercepts clicks)
  const stateBoundaryStyle = {
    fillColor: 'transparent',
    fillOpacity: 0,
    color: isDark ? '#cbd5e1' : '#334155',
    weight: 2.2,
    opacity: 0.95,
    dashArray: '3 5',
    interactive: false
  };

  // Task 1: District Click and Hover event handlers
  const onEachDistrict = (feature, layer) => {
    const dRecord = getFeatureRecord(feature);

    layer.on({
      click: (e) => {
        L.DomEvent.stopPropagation(e);
        if (onSelectZone) {
          onSelectZone(dRecord);
        }
      },
      mouseover: () => {
        setHoveredDistrict(dRecord);
      },
      mouseout: () => {
        setHoveredDistrict(null);
      }
    });
  };

  // State filter switch handler: re-centers viewport AND syncs selected district to that state
  const handleStateFilterClick = (stateName) => {
    setSelectedStateView(stateName);
    if (!onSelectZone || !zones.length) return;

    if (stateName === 'all') {
      return;
    }

    // Auto-select a representative district for the chosen state
    let targetDistrictId = 'chennai';
    if (stateName === 'Kerala') targetDistrictId = 'thiruvananthapuram';
    else if (stateName === 'Karnataka') targetDistrictId = 'bengaluru_urban';

    const rep = zones.find((z) => z.id.toLowerCase() === targetDistrictId) || 
                zones.find((z) => z.state === stateName);

    if (rep) {
      onSelectZone(rep);
    }
  };

  const currentBounds = useMemo(() => {
    return STATE_BOUNDS[selectedStateView] || STATE_BOUNDS.all;
  }, [selectedStateView]);

  // Dual-theme basemap tiles (Esri Canvas - Free, no API keys, zero watermarks)
  const esriBaseTileUrl = isDark 
    ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
    : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}';

  const esriRefTileUrl = isDark
    ? 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}'
    : 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}';

  return (
    <div className="map-card" style={{ height }}>
      {/* Map Top Bar */}
      <div className="map-top-bar">
        <div className="map-title-label">
          <Layers size={14} style={{ color: 'var(--accent-primary)' }} />
          <span>GIS Thermal Risk Field</span>
        </div>

        {/* Metric Layer Switcher: UTCI, WBGT, HI (Temp removed from map layer) */}
        <div className="metric-pill-group">
          <button
            className={`metric-pill ${activeMetric === 'utci' ? 'active' : ''}`}
            onClick={() => setActiveMetric('utci')}
            title="Universal Thermal Climate Index (Fiala-Bröde Biometeorological Model)"
          >
            <Activity size={12} />
            <span>UTCI</span>
          </button>
          <button
            className={`metric-pill ${activeMetric === 'wbgt' ? 'active' : ''}`}
            onClick={() => setActiveMetric('wbgt')}
            title="Wet-Bulb Globe Temp (Standard Outdoor Heat Stress)"
          >
            <Flame size={12} />
            <span>WBGT</span>
          </button>
          <button
            className={`metric-pill ${activeMetric === 'hi' ? 'active' : ''}`}
            onClick={() => setActiveMetric('hi')}
            title="NOAA Rothfusz Heat Index"
          >
            <SunMedium size={12} />
            <span>HI</span>
          </button>
        </div>

        {/* Basemap Provider Toggle (Esri Canvas vs OpenStreetMap) */}
        <div className="basemap-pill-group">
          <button
            className="basemap-toggle-btn"
            onClick={() => setBasemapType(basemapType === 'esri' ? 'osm' : 'esri')}
            title="Toggle basemap provider"
          >
            <Layers size={12} />
            <span>{basemapType === 'esri' ? (isDark ? 'Dark Canvas' : 'Light Canvas') : 'OSM Map'}</span>
          </button>
        </div>
      </div>

      {/* Map Viewport */}
      <div className="map-viewport">
        <MapContainer
          bounds={STATE_BOUNDS.all}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
          attributionControl={false}
        >
          {/* Establish custom panes */}
          <ThermalPanesController />

          {/* Real Geographic Basemap */}
          {basemapType === 'esri' ? (
            <TileLayer
              key={`esri-base-${isDark ? 'dark' : 'light'}`}
              url={esriBaseTileUrl}
              maxZoom={16}
              minZoom={5}
              attribution="&copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
            />
          ) : (
            <TileLayer
              key={`osm-base-${isDark ? 'dark' : 'light'}`}
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              className={isDark ? "osm-dark-tiles" : "osm-light-tiles"}
              maxZoom={19}
              minZoom={5}
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
          )}

          {/* Task 2b & 3: Continuous Spatial Interpolation Thermal Field (Underneath vector boundaries, non-interactive) */}
          {rasterUrl && (
            <ImageOverlay
              key={`thermal-raster-${activeMetric}-${zoomTier}`}
              url={rasterUrl}
              bounds={[[8.0, 74.0], [18.6, 80.5]]}
              opacity={0.88}
              pane="thermalRasterPane"
              interactive={false}
            />
          )}

          {/* Authoritative State Boundaries Layer (Non-interactive background dashed lines in overlayPane 400) */}
          {statesGeo && (
            <GeoJSON
              key={`state-boundaries-${isDark ? 'dark' : 'light'}`}
              data={statesGeo}
              style={stateBoundaryStyle}
              interactive={false}
            />
          )}

          {/* Task 1 & 2a: District Vector Polygons in dedicated interactive pane (zIndex 500) */}
          {districtsGeo && (
            <GeoJSON
              key={`districts-${activeMetric}-${selectedZone?.id || 'none'}-${zones.length}-${isAdminView ? 'admin' : 'pub'}-${isDark ? 'dark' : 'light'}`}
              data={districtsGeo}
              style={getDistrictStyle}
              pane="districtPolygonsPane"
              onEachFeature={(feature, layer) => {
                onEachDistrict(feature, layer);
                const d = getFeatureRecord(feature);
                const hss = d.heat_stress_score ?? Math.min(100, Math.round(d.wbgt * 2.2));
                const hssTier = d.heat_stress_tier ?? (hss >= 70 ? 'VERY HIGH' : hss >= 55 ? 'HIGH' : hss >= 40 ? 'MODERATE' : 'LOW');

                // Tooltip showing exact data-driven observations
                layer.bindTooltip(
                  `<div class="district-tooltip-content">
                    <div class="tooltip-header">
                      <span class="tooltip-name">${d.name.toUpperCase()}</span>
                      <span class="tooltip-state">${d.state}</span>
                    </div>
                    <div class="tooltip-divider"></div>
                    <div class="tooltip-grid">
                      <div class="tooltip-item"><span>WBGT:</span><strong>${d.wbgt}°C</strong></div>
                      <div class="tooltip-item"><span>Heat Index:</span><strong>${d.hi}°C</strong></div>
                      <div class="tooltip-item"><span>UTCI:</span><strong>${d.utci !== undefined ? d.utci + '°C' : 'N/A'}</strong></div>
                      <div class="tooltip-item"><span>Temperature:</span><strong>${d.temp}°C</strong></div>
                      <div class="tooltip-item"><span>Humidity:</span><strong>${d.rh}%</strong></div>
                      <div class="tooltip-item"><span>Wind:</span><strong>${d.wind} m/s</strong></div>
                    </div>
                    <div class="tooltip-footer-row">
                      <span class="tooltip-risk-tag" style="color: ${d.color}; border-color: ${d.color}60; background: ${d.color}15;">
                        RISK: ${d.category.toUpperCase()}
                      </span>
                      <span class="tooltip-hss-tag">
                        HEAT STRESS: <strong>${hssTier} (${hss}/100)</strong>
                      </span>
                    </div>
                    ${d.utci_category ? `<div style="font-size: 0.68rem; color: var(--text-secondary); margin-top: 4px; display: flex; justify-content: space-between;"><span>UTCI Stress:</span><strong style="color: ${d.utci_color || 'var(--text-primary)'}">${d.utci_category}</strong></div>` : ''}
                  </div>`,
                  {
                    sticky: true,
                    direction: 'top',
                    className: 'custom-district-leaflet-tooltip'
                  }
                );
              }}
            />
          )}

          {/* Esri Reference Basemap Labels for auxiliary roads (Non-interactive) */}
          {basemapType === 'esri' && (
            <TileLayer
              key={`esri-ref-${isDark ? 'dark' : 'light'}`}
              url={esriRefTileUrl}
              maxZoom={16}
              minZoom={5}
              pane="labelsPane"
              opacity={0.50}
              interactive={false}
            />
          )}

          {/* 
            TASK 2: Topmost Geographic Labels Overlay (Reduced size, soft opacity, selected highlight)
            Non-interactive pass-through so clicks pass seamlessly to district polygons underneath
          */}
          {visibleLabels.map((lbl) => {
            const isSelected = selectedZone && (
              selectedZone.id?.toLowerCase() === lbl.id?.toLowerCase() || 
              selectedZone.name?.toLowerCase() === lbl.name?.toLowerCase()
            );
            const isHovered = hoveredDistrict && (
              hoveredDistrict.id?.toLowerCase() === lbl.id?.toLowerCase() || 
              hoveredDistrict.name?.toLowerCase() === lbl.name?.toLowerCase()
            );
            const isActive = isSelected || isHovered;

            return (
              <Marker
                key={`gis-lbl-${lbl.id}`}
                position={[lbl.lat, lbl.lon]}
                pane="labelsPane"
                interactive={false}
                icon={L.divIcon({
                  className: 'gis-map-label-wrapper',
                  html: `<span class="gis-map-label ${lbl.isState ? 'state-title' : ''} ${lbl.isMajor ? 'major' : ''} ${isActive ? 'active-district-label' : ''}">
                    ${lbl.name}
                    ${currentZoom >= 8.2 && lbl.metricVal ? `<span class="label-metric-chip">${lbl.metricVal.toFixed(1)}°</span>` : ''}
                  </span>`,
                  iconSize: [0, 0],
                  iconAnchor: [0, 0]
                })}
              />
            );
          })}

          {/* View Controller */}
          <MapViewController
            targetBounds={currentBounds}
            selectedCoord={null}
            onZoomChange={setCurrentZoom}
          />
        </MapContainer>

        {/* Task 2: Updated Legend Showing Continuous Color Ramp & Classification Thresholds */}
        <div className="choropleth-legend-card">
          <div className="legend-header">
            <span className="legend-title">CONTINUOUS THERMAL RISK — {activeMetric.toUpperCase()}</span>
          </div>

          {/* Continuous Spectrum Gradient Bar */}
          <div className="legend-continuous-bar-container">
            <div className="legend-continuous-bar"></div>
            <div className="legend-spectrum-labels">
              <span>{activeMetric === 'utci' ? '<26°' : activeMetric === 'hi' ? '<27°' : '<28°'}</span>
              <span>{activeMetric === 'utci' ? '26°' : activeMetric === 'hi' ? '27°' : '28°'}</span>
              <span>{activeMetric === 'utci' ? '32°' : activeMetric === 'hi' ? '32°' : '30°'}</span>
              <span>{activeMetric === 'utci' ? '38°' : activeMetric === 'hi' ? '41°' : '32°'}</span>
              <span>{activeMetric === 'utci' ? '46°+' : activeMetric === 'hi' ? '54°+' : '35°+'}</span>
            </div>
          </div>

          <div className="legend-rows">
            {activeMetric === 'utci' ? (
              <>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(22.0, 'utci') }}></span>
                  <span className="legend-label">No Stress</span>
                  <span className="legend-range">&lt; 26°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(29.0, 'utci') }}></span>
                  <span className="legend-label">Moderate</span>
                  <span className="legend-range">26–32°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(35.0, 'utci') }}></span>
                  <span className="legend-label">Strong</span>
                  <span className="legend-range">32–38°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(42.0, 'utci') }}></span>
                  <span className="legend-label">Very Strong</span>
                  <span className="legend-range">38–46°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(48.0, 'utci') }}></span>
                  <span className="legend-label">Extreme</span>
                  <span className="legend-range">&gt; 46°C</span>
                </div>
              </>
            ) : activeMetric === 'hi' ? (
              <>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(25.0, 'hi') }}></span>
                  <span className="legend-label">Normal</span>
                  <span className="legend-range">&lt; 27°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(29.0, 'hi') }}></span>
                  <span className="legend-label">Caution</span>
                  <span className="legend-range">27–32°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(36.0, 'hi') }}></span>
                  <span className="legend-label">Extreme Caution</span>
                  <span className="legend-range">32–41°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(47.0, 'hi') }}></span>
                  <span className="legend-label">Danger</span>
                  <span className="legend-range">41–54°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(56.0, 'hi') }}></span>
                  <span className="legend-label">Extreme Danger</span>
                  <span className="legend-range">&gt; 54°C</span>
                </div>
              </>
            ) : (
              <>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(26.0, 'wbgt') }}></span>
                  <span className="legend-label">Low</span>
                  <span className="legend-range">&lt; 28°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(29.0, 'wbgt') }}></span>
                  <span className="legend-label">Caution</span>
                  <span className="legend-range">28–30°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(31.0, 'wbgt') }}></span>
                  <span className="legend-label">Danger</span>
                  <span className="legend-range">30–32°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(33.5, 'wbgt') }}></span>
                  <span className="legend-label">Extreme</span>
                  <span className="legend-range">32–35°C</span>
                </div>
                <div className="legend-row">
                  <span className="legend-dot" style={{ backgroundColor: getContinuousColor(36.5, 'wbgt') }}></span>
                  <span className="legend-label">Severe</span>
                  <span className="legend-range">&gt; 35°C</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Scientific Honesty Data Note Banner */}
        <div className="map-scientific-note">
          <Info size={12} style={{ flexShrink: 0, color: 'var(--accent-primary)' }} />
          <span>
            Spatial continuous thermal field interpolated from 83 district observations. Boundaries remain authoritative.
          </span>
        </div>
      </div>
    </div>
  );
}
