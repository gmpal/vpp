// types.ts
// Note: Type definitions are primarily in api.ts for consistency.
// This file is maintained for backward compatibility but should be consolidated.

export interface HistoricalDataPoint {
  timestamp: string;
  value: number;
}

export interface ForecastedDataPoint {
  timestamp: string;
  value: number;
}

export interface CombinedDataPoint {
  timestamp: string;
  value: number;
  type: "Historical" | "Forecasted";
}
