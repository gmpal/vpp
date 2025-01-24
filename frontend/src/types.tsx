// types.ts
export interface HistoricalDataPoint {
    timestamp: string;
    value: number;
}

export interface ForecastedDataPoint {
    timestamp: string;
    trend: number;
    yhat_lower: number;
    yhat_upper: number;
    trend_lower: number;
    trend_upper: number;
    additive_terms: number;
    additive_terms_lower: number;
    additive_terms_upper: number;
    daily: number;
    daily_lower: number;
    daily_upper: number;
    multiplicative_terms: number;
    multiplicative_terms_lower: number;
    multiplicative_terms_upper: number;
    yhat: number;
}

export interface CombinedDataPoint {
    timestamp: string;
    value: number;
    type: 'Historical' | 'Forecasted';
}
