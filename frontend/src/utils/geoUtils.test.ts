import { geomCentroid, distM, geomArea, pickBestBuilding, isBuildingGeometryStorable, MAX_BUILDING_AREA_SQ_DEG, BuildingCandidate } from './geoUtils';

// ---------------------------------------------------------------------------
// geomCentroid
// ---------------------------------------------------------------------------

describe('geomCentroid', () => {
  test('returns null for non-polygon geometry', () => {
    expect(geomCentroid({ type: 'Point', coordinates: [4.35, 50.85] })).toBeNull();
    expect(geomCentroid({ type: 'LineString', coordinates: [[4.35, 50.85], [4.36, 50.86]] })).toBeNull();
  });

  test('computes centroid of a simple square Polygon', () => {
    // 1° ≈ 111 km; a square with corners at (0,0),(2,0),(2,2),(0,2) has centroid (1,1)
    const geom: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
    };
    const result = geomCentroid(geom);
    expect(result).not.toBeNull();
    expect(result![0]).toBeCloseTo(1, 5); // lng
    expect(result![1]).toBeCloseTo(1, 5); // lat
  });

  test('computes centroid of a real-world building footprint', () => {
    // Small building in Brussels area
    const geom: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.3450, 50.8480],
        [4.3455, 50.8480],
        [4.3455, 50.8485],
        [4.3450, 50.8485],
        [4.3450, 50.8480],
      ]],
    };
    const result = geomCentroid(geom);
    expect(result).not.toBeNull();
    expect(result![0]).toBeCloseTo(4.3452, 3);
    expect(result![1]).toBeCloseTo(50.8482, 3);
  });

  test('averages across all outer rings of a MultiPolygon (closing vertex excluded)', () => {
    // Two unit squares: (0,0)–(1,1) and (3,3)–(4,4), each ring closed.
    // After skipping closing vertex: 4 pts each → centroids (0.5,0.5) and (3.5,3.5) → avg (2,2)
    const geom: GeoJSON.MultiPolygon = {
      type: 'MultiPolygon',
      coordinates: [
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        [[[3, 3], [4, 3], [4, 4], [3, 4], [3, 3]]],
      ],
    };
    const result = geomCentroid(geom);
    expect(result).not.toBeNull();
    expect(result![0]).toBeCloseTo(2.0, 5);
    expect(result![1]).toBeCloseTo(2.0, 5);
  });
});

// ---------------------------------------------------------------------------
// distM
// ---------------------------------------------------------------------------

describe('distM', () => {
  test('returns 0 for identical points', () => {
    expect(distM(50.85, 4.35, 50.85, 4.35)).toBe(0);
  });

  test('~111 km per degree of latitude', () => {
    // Moving 1° north at the equator ≈ 111 320 m
    const d = distM(0, 0, 1, 0);
    expect(d).toBeCloseTo(111320, -2); // within 100 m
  });

  test('longitude degrees shrink with latitude (cosine factor)', () => {
    // At 60°N, 1° of longitude ≈ 111320 * cos(60°) ≈ 55 660 m
    const d = distM(60, 0, 60, 1);
    expect(d).toBeCloseTo(55660, -2);
  });

  test('same-building clicks are within 15 m threshold', () => {
    // Two clicks on the same ~20m building polygon should both be <15m from centroid
    const centroidLat = 50.8483, centroidLng = 4.3452;
    // Click near the north edge of the building (~8 m from centroid)
    expect(distM(centroidLat, centroidLng, centroidLat + 0.00007, centroidLng)).toBeLessThan(15);
    // Click near the south edge (~8 m)
    expect(distM(centroidLat, centroidLng, centroidLat - 0.00007, centroidLng)).toBeLessThan(15);
  });

  test('neighboring building centroid is outside 15 m threshold', () => {
    // Two adjacent buildings ~30 m apart should not match
    const centroidA = { lat: 50.8483, lng: 4.3452 };
    const centroidB = { lat: 50.8485, lng: 4.3452 }; // ~22 m north
    expect(distM(centroidA.lat, centroidA.lng, centroidB.lat, centroidB.lng)).toBeGreaterThan(15);
  });
});

// ---------------------------------------------------------------------------
// geomArea
// ---------------------------------------------------------------------------

describe('geomArea', () => {
  // 1° × 1° square → area = 1 sq-deg
  const unitSquare: GeoJSON.Polygon = {
    type: 'Polygon',
    coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
  };

  test('returns correct area for a unit square', () => {
    expect(geomArea(unitSquare)).toBeCloseTo(1, 10);
  });

  test('individual building footprint is below MAX_BUILDING_AREA_SQ_DEG', () => {
    // ~50 m × 50 m building in Brussels (lat 51°): 0.00045° × 0.00072° ≈ 3.2e-7 sq-deg
    const building: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.3450, 50.8480],
        [4.3455, 50.8480],
        [4.3455, 50.8485],
        [4.3450, 50.8485],
        [4.3450, 50.8480],
      ]],
    };
    expect(geomArea(building)).toBeLessThan(MAX_BUILDING_AREA_SQ_DEG);
  });

  test('neighbourhood-scale polygon exceeds MAX_BUILDING_AREA_SQ_DEG', () => {
    // ~1 km × 1 km block: 0.009° × 0.014° ≈ 1.3e-4 sq-deg
    const block: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.34, 50.84],
        [4.35, 50.84],
        [4.35, 50.85],
        [4.34, 50.85],
        [4.34, 50.84],
      ]],
    };
    expect(geomArea(block)).toBeGreaterThan(MAX_BUILDING_AREA_SQ_DEG);
  });

  test('returns Infinity for non-polygon geometry', () => {
    expect(geomArea({ type: 'Point', coordinates: [0, 0] })).toBe(Infinity);
    expect(geomArea({ type: 'LineString', coordinates: [[0, 0], [1, 1]] })).toBe(Infinity);
  });

  test('sums outer rings of a MultiPolygon', () => {
    const multi: GeoJSON.MultiPolygon = {
      type: 'MultiPolygon',
      coordinates: [
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
      ],
    };
    expect(geomArea(multi)).toBeCloseTo(2, 10);
  });
});

// ---------------------------------------------------------------------------
// pickBestBuilding — the neighbourhood-selection bug
// ---------------------------------------------------------------------------

function makeCandidate(
  id: number,
  lngMin: number, latMin: number,
  lngMax: number, latMax: number,
  height = 10,
): BuildingCandidate {
  return {
    id,
    height,
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [lngMin, latMin], [lngMax, latMin],
        [lngMax, latMax], [lngMin, latMax],
        [lngMin, latMin],
      ]],
    },
  };
}

describe('pickBestBuilding', () => {
  test('returns null for empty list', () => {
    expect(pickBestBuilding([])).toBeNull();
  });

  test('rejects features with height < 2 m', () => {
    const flat = makeCandidate(1, 4.345, 50.848, 4.3455, 50.8485, 1);
    expect(pickBestBuilding([flat])).toBeNull();
  });

  test('selects a valid small building', () => {
    const building = makeCandidate(1, 4.3450, 50.8480, 4.3455, 50.8485, 8);
    expect(pickBestBuilding([building])).toBe(building);
  });

  test('picks the SMALLEST valid building when multiple candidates exist', () => {
    const small = makeCandidate(1, 4.3450, 50.8480, 4.3453, 50.8483, 8);
    const large = makeCandidate(2, 4.3440, 50.8475, 4.3460, 50.8495, 8);
    expect(pickBestBuilding([large, small])).toBe(small);
  });

  test('neighbourhood polygon does not win over an individual building (the bug)', () => {
    const neighbourhood = makeCandidate(99, 4.34, 50.84, 4.36, 50.86, 8);
    const building      = makeCandidate(1,  4.3450, 50.8480, 4.3455, 50.8485, 8);
    expect(pickBestBuilding([neighbourhood, building])).toBe(building);
  });

  test('neighbourhood polygon alone is still clickable (but its geometry wont be stored)', () => {
    // Detection should succeed so the user can enroll any building-tagged polygon.
    // Geometry storage is guarded separately by isBuildingGeometryStorable.
    const neighbourhood = makeCandidate(99, 4.34, 50.84, 4.35, 50.85, 8);
    expect(pickBestBuilding([neighbourhood])).toBe(neighbourhood);
  });
});

// ---------------------------------------------------------------------------
// isBuildingGeometryStorable — prevents large yellow squares in the DB
// ---------------------------------------------------------------------------

describe('isBuildingGeometryStorable', () => {
  test('individual building footprint is storable', () => {
    const building: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.3450, 50.8480], [4.3455, 50.8480],
        [4.3455, 50.8485], [4.3450, 50.8485],
        [4.3450, 50.8480],
      ]],
    };
    expect(isBuildingGeometryStorable(building)).toBe(true);
  });

  test('neighbourhood-scale polygon is NOT storable', () => {
    const block: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.34, 50.84], [4.35, 50.84],
        [4.35, 50.85], [4.34, 50.85],
        [4.34, 50.84],
      ]],
    };
    expect(isBuildingGeometryStorable(block)).toBe(false);
  });

  test('tile-clipped square boundary is NOT storable', () => {
    const tile: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[
        [4.33, 50.83], [4.35, 50.83],
        [4.35, 50.85], [4.33, 50.85],
        [4.33, 50.83],
      ]],
    };
    expect(isBuildingGeometryStorable(tile)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Matching logic (the bug scenario)
// ---------------------------------------------------------------------------

describe('building identification matching', () => {
  const THRESHOLD = 15;

  function findMatch(
    households: Array<{ latitude: number; longitude: number }>,
    centroid: { lat: number; lng: number }
  ) {
    return households.find(
      hh => distM(hh.latitude, hh.longitude, centroid.lat, centroid.lng) < THRESHOLD
    ) ?? null;
  }

  test('clicking the same building finds the enrolled household', () => {
    const hh = { latitude: 50.8483, longitude: 4.3452 };
    // Centroid computed from geometry will be very close to stored centroid
    const centroid = { lat: 50.84831, lng: 4.34521 }; // <2 m away
    expect(findMatch([hh], centroid)).toBe(hh);
  });

  test('clicking a neighboring building does NOT match an enrolled household', () => {
    const hh = { latitude: 50.8483, longitude: 4.3452 };
    const neighborCentroid = { lat: 50.8485, lng: 4.3452 }; // ~22 m away
    expect(findMatch([hh], neighborCentroid)).toBeNull();
  });

  test('the old 150 m threshold would have incorrectly matched the neighbor', () => {
    const hh = { latitude: 50.8483, longitude: 4.3452 };
    const neighborCentroid = { lat: 50.8485, lng: 4.3452 }; // ~22 m away
    const d = distM(hh.latitude, hh.longitude, neighborCentroid.lat, neighborCentroid.lng);
    // Demonstrates the bug: the old threshold (150 m) would have matched a neighboring building
    expect(d).toBeLessThan(150);
    expect(d).toBeGreaterThan(15); // but our new threshold correctly rejects it
  });
});
