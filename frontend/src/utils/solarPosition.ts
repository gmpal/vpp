/**
 * Compute solar elevation angle (degrees) for a given lat/lon and Date.
 * Positive = above horizon (daytime), negative = below (night).
 */
export function solarElevation(lat: number, lon: number, date: Date): number {
  const dayOfYear = Math.floor(
    (date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / 86400000,
  );
  const hour = date.getUTCHours() + lon / 15; // approximate solar time
  const declination =
    23.45 * Math.sin((Math.PI / 180) * ((360 / 365) * (dayOfYear - 81)));
  const hourAngle = 15 * (hour - 12);
  const latR = (Math.PI / 180) * lat;
  const decR = (Math.PI / 180) * declination;
  const haR = (Math.PI / 180) * hourAngle;
  const sinElevation =
    Math.sin(latR) * Math.sin(decR) +
    Math.cos(latR) * Math.cos(decR) * Math.cos(haR);
  return (Math.asin(sinElevation) * 180) / Math.PI;
}

export function isDaytime(
  lat: number,
  lon: number,
  date: Date = new Date(),
): boolean {
  return solarElevation(lat, lon, date) > 0;
}

export function solarIntensityFactor(
  lat: number,
  lon: number,
  date: Date = new Date(),
): number {
  const elev = solarElevation(lat, lon, date);
  if (elev <= 0) return 0;
  return Math.min(1, elev / 45); // ramps from 0 at sunrise to 1 at 45-degree elevation
}
