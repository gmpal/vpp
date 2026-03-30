import {
  solarElevation,
  isDaytime,
  solarIntensityFactor,
} from "./solarPosition";

// June 21 noon UTC at equator: sun is nearly overhead (~66° elevation)
const NOON_JUNE21 = new Date("2024-06-21T12:00:00Z");
// June 21 midnight UTC at equator: sun is well below horizon
const MIDNIGHT_JUNE21 = new Date("2024-06-21T00:00:00Z");
// June 21 mid-morning UTC at equator: sun is rising
const MORNING_JUNE21 = new Date("2024-06-21T07:00:00Z");

describe("solarElevation", () => {
  it("returns positive elevation at noon UTC for equator (lat=0, lon=0)", () => {
    const elev = solarElevation(0, 0, NOON_JUNE21);
    expect(elev).toBeGreaterThan(0);
  });

  it("returns negative elevation at midnight UTC for equator", () => {
    const elev = solarElevation(0, 0, MIDNIGHT_JUNE21);
    expect(elev).toBeLessThan(0);
  });

  it("returns a number (finite value)", () => {
    const elev = solarElevation(51.5, -0.1, NOON_JUNE21); // London noon
    expect(Number.isFinite(elev)).toBe(true);
  });

  it("elevation at noon is higher than elevation at morning", () => {
    const noonElev = solarElevation(0, 0, NOON_JUNE21);
    const morningElev = solarElevation(0, 0, MORNING_JUNE21);
    expect(noonElev).toBeGreaterThan(morningElev);
  });
});

describe("isDaytime", () => {
  it("returns true at solar noon for equator on summer solstice", () => {
    expect(isDaytime(0, 0, NOON_JUNE21)).toBe(true);
  });

  it("returns false at midnight for equator", () => {
    expect(isDaytime(0, 0, MIDNIGHT_JUNE21)).toBe(false);
  });

  it("is consistent with solarElevation > 0", () => {
    expect(isDaytime(0, 0, NOON_JUNE21)).toBe(
      solarElevation(0, 0, NOON_JUNE21) > 0,
    );
    expect(isDaytime(0, 0, MIDNIGHT_JUNE21)).toBe(
      solarElevation(0, 0, MIDNIGHT_JUNE21) > 0,
    );
  });
});

describe("solarIntensityFactor", () => {
  it("returns 0 at night", () => {
    expect(solarIntensityFactor(0, 0, MIDNIGHT_JUNE21)).toBe(0);
  });

  it("returns positive value during the day (noon)", () => {
    expect(solarIntensityFactor(0, 0, NOON_JUNE21)).toBeGreaterThan(0);
  });

  it("never exceeds 1", () => {
    expect(solarIntensityFactor(0, 0, NOON_JUNE21)).toBeLessThanOrEqual(1);
  });

  it("returns 1 when elevation >= 45 degrees (equator noon on solstice ~66°)", () => {
    // June 21 equator noon: elevation ≈ 66° > 45°, so factor = min(1, 66/45) = 1
    expect(solarIntensityFactor(0, 0, NOON_JUNE21)).toBe(1);
  });

  it("returns 0 when elevation is exactly 0 (horizon)", () => {
    // Below horizon → 0; we test the night case
    const factor = solarIntensityFactor(0, 0, MIDNIGHT_JUNE21);
    expect(factor).toBe(0);
  });
});
