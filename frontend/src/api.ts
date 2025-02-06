import axios from 'axios';

// Define API_BASE_URL using environment variable
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
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

export interface Source {
    source_type: string;
    source_id: string;
}

export interface BatteryStatus {
    battery_id: string;
    capacity_kWh: number;
    soc_kWh: number;
    max_charge_kW: number;
    max_discharge_kW: number;
    eta: number;
}

export interface BatteryOperation {
    power_kW: number;
    duration_h?: number;  // Optional; default duration can be set by backend if not provided
}

export async function fetchAllBatteries(): Promise<BatteryStatus[]> {
    const response = await axios.get<BatteryStatus[]>(`${API_BASE_URL}/batteries`);
    return response.data;
}

export async function addBattery(
    capacity_kWh: number,
    current_soc_kWh: number,
    max_charge_kW: number,
    max_discharge_kW: number,
    eta: number
): Promise<BatteryStatus> {
    // POST /batteries expects a JSON body with battery parameters
    const payload = {
        capacity_kWh,
        current_soc_kWh,
        max_charge_kW,
        max_discharge_kW,
        eta,
    };
    const response = await axios.post<BatteryStatus>(`${API_BASE_URL}/batteries`, payload);
    return response.data;
}

export async function removeBattery(battery_id: string): Promise<void> {
    // DELETE /batteries/:battery_id to remove a battery
    const url = `${API_BASE_URL}/batteries/${encodeURIComponent(battery_id)}`;
    await axios.delete(url);
}

export async function chargeBattery(
    battery_id: string,
    operation: BatteryOperation
): Promise<BatteryStatus> {
    const url = `${API_BASE_URL}/batteries/${encodeURIComponent(battery_id)}/charge`;
    const response = await axios.post<BatteryStatus>(url, operation);
    return response.data;
}

export async function dischargeBattery(
    battery_id: string,
    operation: BatteryOperation
): Promise<BatteryStatus> {
    const url = `${API_BASE_URL}/batteries/${encodeURIComponent(battery_id)}/discharge`;
    const response = await axios.post<BatteryStatus>(url, operation);
    return response.data;
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

export async function addNewSource(source_type: string): Promise<Source> {
    let url = `${API_BASE_URL}/add-source`;
    const params: string[] = [];
    params.push(`source_type=${encodeURIComponent(source_type)}`);

    if (params.length) {
        url += '?' + params.join('&');
    }
    const response = await axios.get<Source>(url);
    return response.data;
}


export async function fetchHistoricalData(source: string, source_id?: string, start?: string, end?: string, top?: number | 50): Promise<HistoricalDataPoint[]> {
    let url = `${API_BASE_URL}/historical/${source}`;
    const params: string[] = [];

    // Only include source_id if source requires it
    if (source_id && source !== 'market' && source !== 'load') {
        params.push(`source_id=${encodeURIComponent(source_id)}`);
    }

    if (start) params.push(`start=${encodeURIComponent(start)}`);
    if (end) params.push(`end=${encodeURIComponent(end)}`);
    if (top) params.push(`top=${encodeURIComponent(top)}`);

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
    console.log('Device counts:', response.data);
    return response.data;
}

////////////////////////////////////////
// Optimization API
////////////////////////////////////////

export interface OptimizationRecord {
    time: string;
    battery_id: string;
    charge: number;
    discharge: number;
    soc: number;
    grid_buy: number;
    grid_sell: number;
}

export async function optimizeStrategy(
): Promise<OptimizationRecord[]> {
    const endpoint = `${API_BASE_URL}/optimize`;
    const resp = await axios.post<OptimizationRecord[]>(endpoint);
    return resp.data;
}
