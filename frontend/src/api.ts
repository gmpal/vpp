import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface RealTimeDataPoint {
    timestamp: string;
    value: number;
    // TODO: consider merging with historical data point
}

export interface HistoricalDataPoint {
    timestamp: string;
    value: number;
    // Other fields...
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

export interface DeviceCounts {
    solar: number;
    wind: number;
    // Add other fields if necessary
}

export async function fetchRealTimeData(source: string, source_id?: string, lastFetchedTime?: string | null): Promise<RealTimeDataPoint[]> {
    let url = `${API_BASE_URL}/realtime-data/${source}`;
    const params: string[] = [];

    // Only include source_id if source requires it
    if (source_id && source !== 'market' && source !== 'load') {
        params.push(`source_id=${encodeURIComponent(source_id)}`);
    }
    if (lastFetchedTime) {
        params.push(`since=${encodeURIComponent(lastFetchedTime)}`);
    }

    if (params.length) {
        url += '?' + params.join('&');
    }
    const response = await axios.get<RealTimeDataPoint[]>(url);
    return response.data;
}


export async function fetchHistoricalData(source: string, source_id?: string, start?: string, end?: string): Promise<HistoricalDataPoint[]> {
    let url = `${API_BASE_URL}/historical/${source}`;
    const params: string[] = [];

    // Only include source_id if source requires it
    if (source_id && source !== 'market' && source !== 'load') {
        params.push(`source_id=${encodeURIComponent(source_id)}`);
    }

    if (start) params.push(`start=${encodeURIComponent(start)}`);
    if (end) params.push(`end=${encodeURIComponent(end)}`);
    if (params.length) {
        url += '?' + params.join('&');
    }
    const response = await axios.get<HistoricalDataPoint[]>(url);
    return response.data;
}


export async function fetchForecastedData(source: string, source_id?: string, start?: string, end?: string): Promise<ForecastedDataPoint[]> {
    let url = `${API_BASE_URL}/forecasted/${source}`;
    const params: string[] = [];

    // Only include source_id if source requires it
    if (source_id && source !== 'market' && source !== 'load') {
        params.push(`source_id=${encodeURIComponent(source_id)}`);
    }

    if (start) params.push(`start=${encodeURIComponent(start)}`);
    if (end) params.push(`end=${encodeURIComponent(end)}`);
    if (params.length) {
        url += '?' + params.join('&');
    }
    const response = await axios.get<ForecastedDataPoint[]>(url);
    return response.data;
}


export async function fetchSourceIDs(source: string): Promise<string[]> {
    const response = await axios.get<string[]>(`${API_BASE_URL}/source-ids/${source}`);
    return response.data;
}


export async function fetchDeviceCounts(): Promise<DeviceCounts> {
    const response = await axios.get<DeviceCounts>(`${API_BASE_URL}/device-status`);
    return response.data;
}
