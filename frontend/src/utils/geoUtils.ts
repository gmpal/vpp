/** Approximate area of a closed ring (last coord == first) in square degrees. */
function ringArea(ring: number[][]): number {
  const pts = ring.slice(0, -1);
  let area = 0;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    area += (pts[j][0] + pts[i][0]) * (pts[j][1] - pts[i][1]);
  }
  return Math.abs(area / 2);
}

/** Approximate area of a Polygon or MultiPolygon in square degrees (for comparison only). */
export function geomArea(geom: GeoJSON.Geometry): number {
  if (geom.type === 'Polygon') return ringArea(geom.coordinates[0]);
  if (geom.type === 'MultiPolygon') return geom.coordinates.reduce((s, p) => s + ringArea(p[0]), 0);
  return Infinity;
}

/**
 * Max footprint in sq-degrees considered a real individual building
 * (~400 m × 400 m at Brussels latitude). Anything larger is a block,
 * neighbourhood, or tile-clipped polygon and must be rejected.
 */
export const MAX_BUILDING_AREA_SQ_DEG = 2e-5;

export interface BuildingCandidate {
  id: string | number;
  geometry: GeoJSON.Geometry;
  /** render_height or height in metres */
  height: number;
}

/**
 * From a list of map feature candidates (already filtered to polygon types with
 * a stable ID), return the best building — preferring the smallest footprint so
 * individual buildings win over block/neighbourhood polygons.
 * Height ≥ 2 m is required; there is no upper area cap here so that large-but-valid
 * buildings (hospitals, warehouses) are still clickable.
 */
export function pickBestBuilding(
  candidates: BuildingCandidate[],
): BuildingCandidate | null {
  const valid = candidates
    .filter((c) => c.height >= 2)
    .sort((a, b) => geomArea(a.geometry) - geomArea(b.geometry));
  return valid[0] ?? null;
}

/**
 * Returns true when a polygon geometry is small enough to be an individual
 * building and safe to store in the DB as a highlight overlay.
 * Polygons larger than MAX_BUILDING_AREA_SQ_DEG are block/neighbourhood/
 * tile-clipped features and must not be persisted.
 */
export function isBuildingGeometryStorable(geom: GeoJSON.Geometry): boolean {
  return geomArea(geom) < MAX_BUILDING_AREA_SQ_DEG;
}

/** Compute the centroid of a Polygon or MultiPolygon geometry. Returns [lng, lat]. */
export function geomCentroid(geom: GeoJSON.Geometry): [number, number] | null {
  let rings: number[][][] = [];
  if (geom.type === 'Polygon') rings = [geom.coordinates[0]];
  else if (geom.type === 'MultiPolygon') rings = geom.coordinates.map(p => p[0]);
  else return null;
  let sumLng = 0, sumLat = 0, count = 0;
  for (const ring of rings) {
    // GeoJSON rings are closed (last coord == first); skip the duplicate closing vertex
    const pts = ring.slice(0, -1);
    for (const [lng, lat] of pts) { sumLng += lng; sumLat += lat; count++; }
  }
  return count > 0 ? [sumLng / count, sumLat / count] : null;
}

/** Approximate distance in metres between two lat/lng points (flat-earth). */
export function distM(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const dLat = (lat2 - lat1) * 111320;
  const dLng = (lng2 - lng1) * 111320 * Math.cos(lat1 * Math.PI / 180);
  return Math.sqrt(dLat * dLat + dLng * dLng);
}
