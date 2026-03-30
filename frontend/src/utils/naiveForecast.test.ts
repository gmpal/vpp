import { naiveForecast } from "./naiveForecast";

describe("naiveForecast", () => {
  test("3-point weighted forecast: [1,2,3] step1 = 2.3", () => {
    const result = naiveForecast([1, 2, 3], 1);
    // 0.5*3 + 0.3*2 + 0.2*1 = 1.5 + 0.6 + 0.2 = 2.3
    expect(result[0]).toBeCloseTo(2.3);
  });

  test("steps parameter controls output length", () => {
    expect(naiveForecast([1, 2, 3], 5)).toHaveLength(5);
    expect(naiveForecast([1, 2, 3], 3)).toHaveLength(3);
    expect(naiveForecast([1, 2, 3], 1)).toHaveLength(1);
  });

  test("default steps = 5", () => {
    expect(naiveForecast([1, 2, 3])).toHaveLength(5);
  });

  test("2 points: linear extrapolation 2*y[n-1] - y[n-2]", () => {
    const result = naiveForecast([1, 2], 1);
    // 2 * 2 - 1 = 3
    expect(result[0]).toBeCloseTo(3);
  });

  test("1 point: repeats that value", () => {
    const result = naiveForecast([5], 3);
    expect(result).toEqual([5, 5, 5]);
  });

  test("clamps negative outputs to 0 (descending linear case)", () => {
    // [3, 0] → linear: 2*0 - 3 = -3, clamped to 0
    const result = naiveForecast([3, 0], 1);
    expect(result[0]).toBe(0);
  });

  test("all outputs are >= 0", () => {
    const result = naiveForecast([10, 5, 0], 5);
    result.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
  });

  test("each step is fed back into the buffer (multi-step)", () => {
    const result = naiveForecast([1, 2, 3], 2);
    // step1 = 0.5*3 + 0.3*2 + 0.2*1 = 2.3
    // step2 uses [2, 3, 2.3]: 0.5*2.3 + 0.3*3 + 0.2*2 = 1.15 + 0.9 + 0.4 = 2.45
    expect(result[0]).toBeCloseTo(2.3);
    expect(result[1]).toBeCloseTo(2.45);
  });

  test("empty array edge case returns array of zeros", () => {
    // values[values.length - 1] ?? 0 = undefined ?? 0 = 0
    const result = naiveForecast([], 3);
    expect(result).toHaveLength(3);
    result.forEach((v) => expect(v).toBe(0));
  });
});
