/**
 * Continuous Thermal Color Ramp & Dynamic Dynamics Engine
 * Generates smooth, continuous HSL/RGB interpolation across district temperatures.
 * Replaces flat bucketed classifications with a continuous scalar field.
 */

// Authoritative continuous control points (WBGT in °C)
// Full-spectrum continuous gradient spanning cool hill regions (16°C) to extreme tropical heat (>35°C)
const WBGT_CONTROL_POINTS = [
  { val: 16.0, r: 13,  g: 148, b: 136 }, // #0d9488 (Cool teal/emerald - high hill stations / pleasant baseline)
  { val: 20.0, r: 16,  g: 185, b: 129 }, // #10b981 (Lush green / comfortable plateau baseline)
  { val: 23.5, r: 74,  g: 222, b: 128 }, // #4ade80 (Soft spring green)
  { val: 25.5, r: 163, g: 230, b: 53  }, // #a3e635 (Bright lime-green - mild tropical warming)
  { val: 27.0, r: 234, g: 179, b: 8   }, // #eab308 (Warm golden yellow - approaching Caution threshold)
  { val: 28.0, r: 245, g: 158, b: 11  }, // #f59e0b (Amber - official Caution threshold)
  { val: 30.0, r: 249, g: 115, b: 22  }, // #f97316 (Vivid orange - official Danger threshold)
  { val: 32.0, r: 239, g: 68,  b: 68  }, // #ef4444 (Red - official Extreme Danger threshold)
  { val: 35.0, r: 220, g: 38,  b: 38  }, // #dc2626 (Vivid red / Severe threshold)
  { val: 38.0, r: 136, g: 19,  b: 55  }  // #881337 (Deep crimson / Extreme Severe)
];

// Heat Index Control Points (°C)
// Official thresholds: <27 Normal, 27-32 Caution, 32-41 Extreme Caution, 41-54 Danger, >54 Extreme Danger
const HI_CONTROL_POINTS = [
  { val: 16.0, r: 13,  g: 148, b: 136 }, // #0d9488 (Cool teal/emerald)
  { val: 22.0, r: 16,  g: 185, b: 129 }, // #10b981 (Lush green / Normal)
  { val: 26.0, r: 132, g: 204, b: 22  }, // #84cc16 (Lime - approaching Caution)
  { val: 27.0, r: 234, g: 179, b: 8   }, // #eab308 (Yellow - official Caution threshold)
  { val: 32.0, r: 245, g: 158, b: 11  }, // #f59e0b (Amber - official Extreme Caution threshold)
  { val: 38.0, r: 249, g: 115, b: 22  }, // #f97316 (Orange - approaching Danger)
  { val: 41.0, r: 239, g: 68,  b: 68  }, // #ef4444 (Red - official Danger threshold)
  { val: 54.0, r: 185, g: 28,  b: 28  }, // #b91c1c (Dark Red - official Extreme Danger threshold)
  { val: 60.0, r: 136, g: 19,  b: 55  }  // #881337 (Deep crimson)
];

// Ambient Temperature Control Points (°C)
const TEMP_CONTROL_POINTS = [
  { val: 18.0, r: 13,  g: 148, b: 136 },
  { val: 24.0, r: 16,  g: 185, b: 129 },
  { val: 29.0, r: 234, g: 179, b: 8   },
  { val: 34.0, r: 249, g: 115, b: 22  },
  { val: 39.0, r: 239, g: 68,  b: 68  },
  { val: 44.0, r: 136, g: 19,  b: 55  }
];

// Universal Thermal Climate Index (UTCI) Control Points (°C)
// Official thresholds: <26 No stress, 26-32 Moderate, 32-38 Strong, 38-46 Very strong, >46 Extreme
const UTCI_CONTROL_POINTS = [
  { val: 14.0, r: 13,  g: 148, b: 136 }, // #0d9488 (Cool teal/emerald - cool mountain baseline)
  { val: 18.0, r: 16,  g: 185, b: 129 }, // #10b981 (Green / No thermal stress baseline)
  { val: 23.0, r: 74,  g: 222, b: 128 }, // #4ade80 (Spring green)
  { val: 26.0, r: 163, g: 230, b: 53  }, // #a3e635 (Lime - No thermal stress upper boundary)
  { val: 28.5, r: 234, g: 179, b: 8   }, // #eab308 (Warm golden yellow - Moderate Heat Stress)
  { val: 32.0, r: 245, g: 158, b: 11  }, // #f59e0b (Amber - Moderate / Strong boundary)
  { val: 35.0, r: 249, g: 115, b: 22  }, // #f97316 (Strong Heat Stress)
  { val: 38.0, r: 239, g: 68,  b: 68  }, // #ef4444 (Strong / Very Strong boundary)
  { val: 42.0, r: 220, g: 38,  b: 38  }, // #dc2626 (Very Strong Heat Stress)
  { val: 46.0, r: 136, g: 19,  b: 55  }  // #881337 (Extreme Heat Stress)
];

/**
 * Continuous RGB interpolation function
 */
export function getContinuousColor(value, metric = 'wbgt') {
  const [r, g, b] = getContinuousColorRgb(value, metric);
  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Returns [r, g, b] array for a given value
 */
export function getContinuousColorRgb(value, metric = 'wbgt') {
  let points = WBGT_CONTROL_POINTS;
  if (metric === 'hi') points = HI_CONTROL_POINTS;
  else if (metric === 'temp') points = TEMP_CONTROL_POINTS;
  else if (metric === 'utci') points = UTCI_CONTROL_POINTS;

  const numVal = Number(value);
  if (isNaN(numVal) || numVal <= points[0].val) {
    return [points[0].r, points[0].g, points[0].b];
  }
  if (numVal >= points[points.length - 1].val) {
    const last = points[points.length - 1];
    return [last.r, last.g, last.b];
  }

  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    if (numVal >= p1.val && numVal <= p2.val) {
      const t = (numVal - p1.val) / (p2.val - p1.val);
      return [
        Math.round(p1.r + (p2.r - p1.r) * t),
        Math.round(p1.g + (p2.g - p1.g) * t),
        Math.round(p1.b + (p2.b - p1.b) * t)
      ];
    }
  }

  return [points[0].r, points[0].g, points[0].b];
}

/**
 * Compute normalized continuous heat intensity (0.0 to 1.0)
 * Drives sun ray rotation speed, pulse scale, glow radius, and shimmer
 */
export function getThermalIntensity(wbgtValue) {
  const wbgt = Number(wbgtValue ?? 29.0);
  const minW = 24.0;
  const maxW = 38.0;
  return Math.max(0, Math.min(1, (wbgt - minW) / (maxW - minW)));
}

/**
 * Task 2b & Task 3: Generate Continuous Spatial Interpolation Raster Layer (Off-screen Canvas)
 * Uses Inverse Distance Weighting across district centroids, masked strictly to state/district geometry.
 * Zoom-responsive resolution prevents upscaling blur and eliminates bloom on zoom.
 * Returns a PNG data URL for Leaflet ImageOverlay.
 */
export function generateContinuousThermalRaster(districtsGeo, districtMap, activeMetric, zoomTier = 'standard') {
  if (typeof document === 'undefined') return null;
  if (!districtsGeo || !districtsGeo.features || !districtMap) return null;

  // Bounding box for South India (Tamil Nadu, Kerala, Karnataka)
  const bounds = {
    minLat: 8.0,
    maxLat: 18.6,
    minLon: 74.0,
    maxLon: 80.5
  };

  const points = [];
  districtsGeo.features.forEach((feature) => {
    const props = feature.properties || {};
    const id = (props.id || '').toLowerCase();
    const name = (props.district || props.name || '').toLowerCase();
    const rec = districtMap.get(id) || districtMap.get(name);

    let val = 29.5;
    if (rec) {
      if (activeMetric === 'hi') val = Number(rec.hi ?? 34.0);
      else if (activeMetric === 'temp') val = Number(rec.temp ?? 32.0);
      else if (activeMetric === 'utci') val = Number(rec.utci ?? 30.0);
      else val = Number(rec.wbgt ?? 29.5);
    }

    const lat = Number(props.rep_lat || feature.geometry?.coordinates?.[0]?.[0]?.[1] || 13.0);
    const lon = Number(props.rep_lon || feature.geometry?.coordinates?.[0]?.[0]?.[0] || 78.0);
    if (!isNaN(lat) && !isNaN(lon)) {
      points.push({ lat, lon, val });
    }
  });

  if (points.length === 0) return null;

  // Task 3: Higher resolution grid prevents upscaling blur
  // Standard zoom: 280x360 (~100k px), Deep zoom (zoom >= 7.5): 380x490 (~186k px)
  const isDeep = zoomTier === 'deep';
  const width = isDeep ? 380 : 280;
  const height = isDeep ? 490 : 360;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return null;
  ctx.imageSmoothingEnabled = false;

  // Coordinate projections to canvas pixels
  const toCanvasX = (lon) => ((lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * width;
  const toCanvasY = (lat) => ((bounds.maxLat - lat) / (bounds.maxLat - bounds.minLat)) * height;

  // 1. Establish clipping mask to strictly keep thermal field inside state/district landmass
  ctx.save();
  ctx.beginPath();

  districtsGeo.features.forEach((feature) => {
    const geom = feature.geometry;
    if (!geom) return;

    const processPolygon = (rings) => {
      rings.forEach((ring) => {
        if (!ring || ring.length === 0) return;
        ctx.moveTo(toCanvasX(ring[0][0]), toCanvasY(ring[0][1]));
        for (let i = 1; i < ring.length; i++) {
          ctx.lineTo(toCanvasX(ring[i][0]), toCanvasY(ring[i][1]));
        }
        ctx.closePath();
      });
    };

    if (geom.type === 'Polygon') {
      processPolygon(geom.coordinates);
    } else if (geom.type === 'MultiPolygon') {
      geom.coordinates.forEach((poly) => processPolygon(poly));
    }
  });

  ctx.clip(); // Mask is locked strictly to landmass (no glow outside TN/KL/KA)

  // 2. Optimized IDW Interpolation over the grid with clean meteorological contours
  const imgData = ctx.createImageData(width, height);
  const data = imgData.data;

  const latSpan = bounds.maxLat - bounds.minLat;
  const lonSpan = bounds.maxLon - bounds.minLon;
  const pCount = points.length;

  for (let y = 0; y < height; y++) {
    const lat = bounds.maxLat - (y / height) * latSpan;
    const yOffset = y * width * 4;

    for (let x = 0; x < width; x++) {
      const lon = bounds.minLon + (x / width) * lonSpan;

      let num = 0;
      let denom = 0;
      let exact = false;
      let exactVal = 0;

      for (let i = 0; i < pCount; i++) {
        const p = points[i];
        const dLat = lat - p.lat;
        const dLon = lon - p.lon;
        const distSq = dLat * dLat + dLon * dLon;

        if (distSq < 0.0001) {
          exact = true;
          exactVal = p.val;
          break;
        }

        // Power of 2 IDW produces smooth scalar gradient without bloom
        const w = 1.0 / (distSq + 0.0002);
        num += w * p.val;
        denom += w;
      }

      const interpVal = exact ? exactVal : (denom > 0 ? num / denom : 29.0);
      const [r, g, b] = getContinuousColorRgb(interpVal, activeMetric);

      const idx = yOffset + x * 4;
      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = 230; // ~90% opacity, masked cleanly to landmass
    }
  }

  // Draw the interpolated field onto the clipped canvas
  const tempCanvas = document.createElement('canvas');
  tempCanvas.width = width;
  tempCanvas.height = height;
  const tempCtx = tempCanvas.getContext('2d');
  tempCtx.imageSmoothingEnabled = false;
  tempCtx.putImageData(imgData, 0, 0);

  ctx.drawImage(tempCanvas, 0, 0);
  ctx.restore();

  return canvas.toDataURL('image/png');
}
