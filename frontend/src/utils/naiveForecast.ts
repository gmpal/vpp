/**
 * Naive 3-point weighted linear forecast.
 * Given recent values, extrapolates the next `steps` points.
 */
export function naiveForecast(values: number[], steps: number = 5): number[] {
  if (values.length < 2) return Array(steps).fill(values[values.length - 1] ?? 0);
  const result: number[] = [];
  const buf = [...values];
  for (let i = 0; i < steps; i++) {
    const n = buf.length;
    let next: number;
    if (n >= 3) {
      next = 0.5 * buf[n - 1] + 0.3 * buf[n - 2] + 0.2 * buf[n - 3];
    } else {
      next = 2 * buf[n - 1] - buf[n - 2];
    }
    next = Math.max(0, next);
    result.push(next);
    buf.push(next);
  }
  return result;
}
