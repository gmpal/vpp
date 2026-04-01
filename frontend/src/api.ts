import axios, { AxiosError } from "axios";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

// Single axios instance for all API calls
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vpp_token");
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  return config;
});

// Normalize backend errors; redirect to /login on 401
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("vpp_token");
      window.location.href = "/login";
    }
    const detail = (error.response?.data as any)?.detail;
    const message = detail ?? error.message ?? "Unknown error";
    return Promise.reject(new Error(message));
  },
);

export interface RealTimeDataPoint {
  timestamp: string;
  value: number;
}

export interface HistoricalDataPoint {
  timestamp: string;
  value: number;
}

export interface ForecastedDataPoint {
  timestamp: string;
  value: number;
}

export interface DeviceCounts {
  solar: number;
  wind: number;
}

export interface EnergySource {
  source_id: string;
  source_type: "solar" | "wind";
  latitude: number;
  longitude: number;
  name: string | null;
  current_value: number | null;
  status: string;
}

export interface AddSourceRequest {
  source_type: "solar" | "wind";
  latitude: number;
  longitude: number;
  name?: string;
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
  duration_h?: number;
}

export interface HouseholdData {
  household_id: string;
  name: string;
  latitude: number;
  longitude: number;
  solar_panels: number;
  building_type: string;
  num_people: number;
  num_evs: number;
  osm_feature_id?: string | null;
  geometry?: GeoJSON.Geometry | null;
}

export interface OptimizationRecord {
  time: string;
  battery_id: string;
  charge: number;
  discharge: number;
  soc: number;
  grid_buy: number;
  grid_sell: number;
}

export interface TrainingStatus {
  last_training: string | null;
  is_training: boolean;
  last_inference: string | null;
  is_running_inference: boolean;
}

////////////////////////////////////////
// Batteries
////////////////////////////////////////

export async function fetchAllBatteries(): Promise<BatteryStatus[]> {
  const response = await api.get<BatteryStatus[]>("/batteries");
  return response.data;
}

export async function addBattery(
  capacity_kWh: number,
  current_soc_kWh: number,
  max_charge_kW: number,
  max_discharge_kW: number,
  eta: number,
): Promise<BatteryStatus> {
  const response = await api.post<BatteryStatus>("/batteries", {
    capacity_kWh,
    current_soc_kWh,
    max_charge_kW,
    max_discharge_kW,
    eta,
  });
  return response.data;
}

export async function removeBattery(battery_id: string): Promise<void> {
  await api.delete(`/batteries/${encodeURIComponent(battery_id)}`);
}

export async function chargeBattery(
  battery_id: string,
  operation: BatteryOperation,
): Promise<BatteryStatus> {
  const response = await api.post<BatteryStatus>(
    `/batteries/${encodeURIComponent(battery_id)}/charge`,
    operation,
  );
  return response.data;
}

export async function dischargeBattery(
  battery_id: string,
  operation: BatteryOperation,
): Promise<BatteryStatus> {
  const response = await api.post<BatteryStatus>(
    `/batteries/${encodeURIComponent(battery_id)}/discharge`,
    operation,
  );
  return response.data;
}

////////////////////////////////////////
// Real-time / Historical / Forecasted
////////////////////////////////////////

export async function fetchRealTimeData(
  source: string,
  source_id?: string,
  lastFetchedTime?: string | null,
): Promise<RealTimeDataPoint[]> {
  const params: Record<string, string> = {};
  if (source_id && source !== "market" && source !== "load") {
    params.source_id = source_id;
  }
  if (lastFetchedTime) {
    params.since = lastFetchedTime;
  }
  const response = await api.get<RealTimeDataPoint[]>(
    `/realtime-data/${source}`,
    { params },
  );
  return response.data;
}

export async function fetchHistoricalData(
  source: string,
  source_id?: string,
  start?: string,
  end?: string,
  top: number = 50,
): Promise<HistoricalDataPoint[]> {
  const params: Record<string, string | number> = { top };
  if (source_id && source !== "market" && source !== "load") {
    params.source_id = source_id;
  }
  if (start) params.start = start;
  if (end) params.end = end;
  const response = await api.get<HistoricalDataPoint[]>(
    `/historical/${source}`,
    { params },
  );
  return response.data;
}

export async function fetchForecastedData(
  source: string,
  source_id?: string,
  start?: string,
  end?: string,
): Promise<ForecastedDataPoint[]> {
  const params: Record<string, string> = {};
  if (source_id && source !== "market" && source !== "load") {
    params.source_id = source_id;
  }
  if (start) params.start = start;
  if (end) params.end = end;
  const response = await api.get<ForecastedDataPoint[]>(
    `/forecasted/${source}`,
    { params },
  );
  return response.data;
}

export async function fetchSourceIDs(source: string): Promise<string[]> {
  const response = await api.get<string[]>(`/source-ids/${source}`);
  return response.data;
}

export async function fetchDeviceCounts(): Promise<DeviceCounts> {
  const response = await api.get<DeviceCounts>("/device-status");
  return response.data;
}

////////////////////////////////////////
// Sources
////////////////////////////////////////

export const getSources = () =>
  api.get<EnergySource[]>("/sources").then((r) => r.data);

export const createSource = (data: AddSourceRequest) =>
  api.post<EnergySource>("/sources", data).then((r) => r.data);

export const deleteSource = (sourceId: string) =>
  api.delete(`/sources/${sourceId}`).then((r) => r.data);

////////////////////////////////////////
// Optimization
////////////////////////////////////////

export async function optimizeStrategy(): Promise<OptimizationRecord[]> {
  const response = await api.post<OptimizationRecord[]>("/optimize");
  return response.data;
}

////////////////////////////////////////
// Forecasting
////////////////////////////////////////

export async function getTrainingStatus(): Promise<TrainingStatus> {
  const response = await api.get<TrainingStatus>("/forecasting/status");
  return response.data;
}

export async function triggerTraining(): Promise<{
  message: string;
  status: TrainingStatus;
}> {
  const response = await api.post("/forecasting/train");
  return response.data;
}

export async function triggerInference(): Promise<{
  message: string;
  status: TrainingStatus;
}> {
  const response = await api.post("/forecasting/inference");
  return response.data;
}

export async function generateSystemData(): Promise<{ message: string }> {
  const response = await api.post("/data/generate-system-data");
  return response.data;
}

////////////////////////////////////////
// Households
////////////////////////////////////////

export const getHouseholds = () =>
  api.get<HouseholdData[]>("/households").then((r) => r.data);

export const createHousehold = (data: {
  name: string;
  latitude: number;
  longitude: number;
  solar_panels?: number;
  building_type?: string;
  num_people?: number;
  num_evs?: number;
  osm_feature_id?: string;
  geometry?: GeoJSON.Geometry;
}) => api.post<HouseholdData>("/households", data).then((r) => r.data);

export const deleteHousehold = (householdId: string) =>
  api.delete(`/households/${householdId}`).then((r) => r.data);

export const getHouseholdSummary = (householdId: string) =>
  api.get<any>(`/households/${householdId}/summary`).then((r) => r.data);

export const getHouseholdByOsmId = (osmFeatureId: string) =>
  api
    .get<HouseholdData>(`/households/by-osm/${osmFeatureId}`)
    .then((r) => r.data);

////////////////////////////////////////
// Electric Vehicles
////////////////////////////////////////

export const getVehicles = () =>
  api.get<any[]>("/vehicles").then((r) => r.data);

export const createVehicle = (data: {
  household_id: string;
  name: string;
  capacity_kwh: number;
  soc_kwh: number;
  max_charge_kw: number;
  max_discharge_kw: number;
  eta?: number;
}) => api.post<any>("/vehicles", data).then((r) => r.data);

export const deleteVehicle = (vehicleId: string) =>
  api.delete(`/vehicles/${vehicleId}`).then((r) => r.data);

export const chargeVehicle = (
  vehicleId: string,
  power_kw: number,
  duration_h?: number,
) =>
  api
    .post<any>(`/vehicles/${vehicleId}/charge`, {
      power_kw,
      duration_h: duration_h ?? 1.0,
    })
    .then((r) => r.data);

export const dischargeVehicle = (
  vehicleId: string,
  power_kw: number,
  duration_h?: number,
) =>
  api
    .post<any>(`/vehicles/${vehicleId}/discharge`, {
      power_kw,
      duration_h: duration_h ?? 1.0,
    })
    .then((r) => r.data);

////////////////////////////////////////
// Community
////////////////////////////////////////

export const getCommunitySummary = () =>
  api.get<any>("/community/summary").then((r) => r.data);

// Community CRUD
export const getCommunities = () =>
  api.get<any[]>("/community").then((r) => r.data);

export const createCommunity = (data: {
  name: string;
  export_limit_kw?: number;
  import_limit_kw?: number;
}) => api.post<any>("/community", data).then((r) => r.data);

export const getCommunity = (communityId: string) =>
  api.get<any>(`/community/${communityId}`).then((r) => r.data);

export const deleteCommunity = (communityId: string) =>
  api.delete(`/community/${communityId}`).then((r) => r.data);

// Members
export const getCommunityMembers = (communityId: string) =>
  api.get<any[]>(`/community/${communityId}/members`).then((r) => r.data);

export const addCommunityMember = (
  communityId: string,
  data: { household_id: string; role?: string },
) => api.post<any>(`/community/${communityId}/members`, data).then((r) => r.data);

export const removeCommunityMember = (
  communityId: string,
  memberId: string,
) =>
  api
    .delete(`/community/${communityId}/members/${memberId}`)
    .then((r) => r.data);

// Participation policy
export const getCommunityPolicy = (communityId: string) =>
  api.get<any>(`/community/${communityId}/policy`).then((r) => r.data);

export const setCommunityPolicy = (
  communityId: string,
  data: { policy: string; priority_order?: string[] },
) => api.post<any>(`/community/${communityId}/policy`, data).then((r) => r.data);

// Allocation
export const allocateSurplus = (
  communityId: string,
  data: {
    interval_start: string;
    surplus_by_household: Record<string, number>;
    demand_by_household: Record<string, number>;
  },
) =>
  api
    .post<any>(`/community/${communityId}/allocate`, data)
    .then((r) => r.data);

export const getAllocationLedger = (
  communityId: string,
  limit?: number,
) =>
  api
    .get<any[]>(`/community/${communityId}/allocation-ledger`, {
      params: limit ? { limit } : {},
    })
    .then((r) => r.data);

// Tariffs
export const getCommunityTariffs = (communityId: string) =>
  api.get<any[]>(`/community/${communityId}/tariffs`).then((r) => r.data);

export const createCommunityTariff = (
  communityId: string,
  data: {
    name: string;
    import_rate: number;
    export_rate: number;
    feed_in_rate?: number;
  },
) =>
  api
    .post<any>(`/community/${communityId}/tariffs`, data)
    .then((r) => r.data);

// Settlement
export const triggerSettlement = (
  communityId: string,
  data: { period_start: string; period_end: string },
) =>
  api.post<any>(`/community/${communityId}/settle`, data).then((r) => r.data);

export const getSettlementRuns = (communityId: string) =>
  api.get<any[]>(`/community/${communityId}/settlement`).then((r) => r.data);

export const getSettlementLines = (communityId: string, runId: string) =>
  api
    .get<any[]>(`/community/${communityId}/settlement/${runId}/lines`)
    .then((r) => r.data);

// Battery assets (stationary)
export const getCommunityBatteries = (communityId: string) =>
  api.get<any[]>(`/community/${communityId}/batteries`).then((r) => r.data);

export const addCommunityBattery = (
  communityId: string,
  data: {
    household_id: string;
    name: string;
    capacity_kwh: number;
    soc_kwh: number;
    max_charge_kw: number;
    max_discharge_kw: number;
    eta?: number;
  },
) =>
  api
    .post<any>(`/community/${communityId}/batteries`, data)
    .then((r) => r.data);

export const removeCommunityBattery = (
  communityId: string,
  batteryId: string,
) =>
  api
    .delete(`/community/${communityId}/batteries/${batteryId}`)
    .then((r) => r.data);

// Grid limits
export const getCommunityGridLimits = (communityId: string) =>
  api.get<any>(`/community/${communityId}/grid-limits`).then((r) => r.data);

export const setCommunityGridLimits = (
  communityId: string,
  data: { export_limit_kw: number; import_limit_kw: number },
) =>
  api
    .post<any>(`/community/${communityId}/grid-limits`, data)
    .then((r) => r.data);

////////////////////////////////////////
// Weather
////////////////////////////////////////

export const getCurrentWeather = (lat: number, lon: number) =>
  api
    .get<any>("/weather/current", { params: { lat, lon } })
    .then((r) => r.data);

////////////////////////////////////////
// Admin
////////////////////////////////////////

export async function initDb(): Promise<{
  message: string;
  load_points_seeded: number;
  market_points_seeded: number;
}> {
  const response = await api.post("/admin/init-db");
  return response.data;
}

export type InitStepStatus = "running" | "done" | "error";

export interface InitStepEvent {
  step: string;
  status: InitStepStatus;
  count?: number;
  message?: string;
}

export async function initDbStream(
  onStep: (event: InitStepEvent) => void,
): Promise<void> {
  const token = localStorage.getItem("vpp_token");
  const response = await fetch(`${API_BASE_URL}/admin/init-db-stream`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.body) throw new Error("No response body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          onStep(JSON.parse(line.slice(6)));
        } catch {
          /* ignore malformed events */
        }
      }
    }
  }
}

export async function resetDb(): Promise<{ message: string }> {
  const response = await api.post("/admin/reset-db", null, { timeout: 60000 });
  return response.data;
}
