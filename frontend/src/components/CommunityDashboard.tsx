import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Grid,
  Paper,
  LinearProgress,
  Alert,
} from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import BoltIcon from "@mui/icons-material/Bolt";
import WbSunnyIcon from "@mui/icons-material/WbSunny";
import HomeIcon from "@mui/icons-material/Home";
import ElectricCarIcon from "@mui/icons-material/ElectricCar";
import BatteryChargingFullIcon from "@mui/icons-material/BatteryChargingFull";
import {
  getCommunitySummary,
  fetchHistoricalData,
  fetchSourceIDs,
  HistoricalDataPoint,
} from "../api";
import TimeWindowSelect from "./TimeWindowSelect";
import {
  DEFAULT_TIME_WINDOW_MINUTES,
  formatTimeWithSeconds,
  getPointLimitForWindow,
  getTimeWindowRange,
} from "../timeWindow";

const ACTION_LABELS: Record<
  string,
  { label: string; color: string; description: string }
> = {
  selling: {
    label: "Selling to Grid",
    color: "#4caf50",
    description: "Excess energy is being sold to the grid",
  },
  buying: {
    label: "Buying from Grid",
    color: "#ff9800",
    description: "Consuming more than producing",
  },
  charging_evs: {
    label: "Charging EVs",
    color: "#2196f3",
    description: "Excess energy directed to EV charging",
  },
  self_sufficient: {
    label: "Self-Sufficient",
    color: "#9c27b0",
    description: "Production matches consumption",
  },
};

const StatCard: React.FC<{
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
}> = ({ title, value, icon, color }) => (
  <Paper sx={{ p: 2, borderRadius: 2, borderLeft: `4px solid ${color}` }}>
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <Box>
        <Typography variant="caption" color="text.secondary">
          {title}
        </Typography>
        <Typography variant="h5" fontWeight="bold">
          {value}
        </Typography>
      </Box>
      <Box sx={{ color }}>{icon}</Box>
    </Box>
  </Paper>
);

function formatTimestamp(ts: string): string {
  try {
    return formatTimeWithSeconds(ts);
  } catch {
    return ts;
  }
}

interface ChartDataPoint {
  time: string;
  value: number;
}

const CommunityDashboard: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [solarData, setSolarData] = useState<ChartDataPoint[]>([]);
  const [loadData, setLoadData] = useState<ChartDataPoint[]>([]);
  const [error, setError] = useState("");
  const [windowMinutes, setWindowMinutes] = useState<number>(
    DEFAULT_TIME_WINDOW_MINUTES,
  );

  const fetchSummary = async () => {
    try {
      const s = await getCommunitySummary();
      setSummary(s);
    } catch (e) {
      setError("Could not load community data");
    }
  };

  const fetchProfiles = async () => {
    try {
      const solarIds = await fetchSourceIDs("solar");
      const { startIso, endIso } = getTimeWindowRange(windowMinutes);
      const top = getPointLimitForWindow(windowMinutes);

      const firstSolarId =
        solarIds && solarIds.length > 0 ? solarIds[0] : undefined;

      const [solarRaw, loadRaw] = await Promise.all([
        firstSolarId
          ? fetchHistoricalData("solar", firstSolarId, startIso, endIso, top)
          : Promise.resolve([] as HistoricalDataPoint[]),
        fetchHistoricalData("load", undefined, startIso, endIso, top),
      ]);

      setSolarData(
        solarRaw.map((p) => ({
          time: formatTimestamp(p.timestamp),
          value: p.value,
        })),
      );
      setLoadData(
        loadRaw.map((p) => ({
          time: formatTimestamp(p.timestamp),
          value: p.value,
        })),
      );
    } catch (e) {
      setError("Could not load historical profiles");
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchProfiles();
    const summaryInterval = setInterval(fetchSummary, 30000);
    const profileInterval = setInterval(fetchProfiles, 5000);
    return () => {
      clearInterval(summaryInterval);
      clearInterval(profileInterval);
    };
  }, [windowMinutes]);

  const actionInfo = summary
    ? ACTION_LABELS[summary.action] ?? ACTION_LABELS.self_sufficient
    : null;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Community Dashboard
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {actionInfo && (
        <Paper
          sx={{
            p: 2,
            mb: 3,
            bgcolor: actionInfo.color + "22",
            borderRadius: 2,
            border: `1px solid ${actionInfo.color}`,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <BoltIcon sx={{ color: actionInfo.color, fontSize: 32 }} />
            <Box>
              <Typography
                variant="h6"
                fontWeight="bold"
                color={actionInfo.color}
              >
                {actionInfo.label}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {actionInfo.description}
              </Typography>
            </Box>
            <Box sx={{ ml: "auto", textAlign: "right" }}>
              <Typography
                variant="h4"
                fontWeight="bold"
                color={summary.net >= 0 ? "#4caf50" : "#f44336"}
              >
                {summary.net >= 0 ? "+" : ""}
                {summary.net.toFixed(2)} kW
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Net power
              </Typography>
            </Box>
          </Box>
        </Paper>
      )}

      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Production"
            value={summary ? `${summary.total_production.toFixed(2)} kW` : "—"}
            icon={<WbSunnyIcon sx={{ fontSize: 32 }} />}
            color="#f0c040"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Consumption"
            value={summary ? `${summary.total_consumption.toFixed(2)} kW` : "—"}
            icon={<HomeIcon sx={{ fontSize: 32 }} />}
            color="#ef5350"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Households"
            value={summary ? String(summary.household_count) : "—"}
            icon={<HomeIcon sx={{ fontSize: 32 }} />}
            color="#4caf50"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="EVs"
            value={summary ? String(summary.ev_count) : "—"}
            icon={<ElectricCarIcon sx={{ fontSize: 32 }} />}
            color="#2196f3"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Energy Storage"
            value={
              summary
                ? `${(summary.ev_soc_total + summary.battery_soc_total).toFixed(1)} kWh`
                : "—"
            }
            icon={<BatteryChargingFullIcon sx={{ fontSize: 32 }} />}
            color="#1e88e5"
          />
        </Grid>
      </Grid>

      {summary && (summary.ev_count > 0 || summary.battery_count > 0) && (
        <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Total Storage State of Charge
          </Typography>
          <LinearProgress
            variant="determinate"
            value={
              summary.ev_soc_capacity + summary.battery_soc_capacity > 0
                ?
                    ((summary.ev_soc_total + summary.battery_soc_total) /
                      (summary.ev_soc_capacity + summary.battery_soc_capacity)) *
                    100
                : 0
            }
            sx={{ height: 12, borderRadius: 6 }}
            color="primary"
          />
          <Typography variant="caption" color="text.secondary">
            {(summary.ev_soc_total + summary.battery_soc_total).toFixed(1)} /{" "}
            {(summary.ev_soc_capacity + summary.battery_soc_capacity).toFixed(1)} kWh (
            {summary.ev_soc_capacity + summary.battery_soc_capacity > 0
              ? (
                  ((summary.ev_soc_total + summary.battery_soc_total) /
                    (summary.ev_soc_capacity + summary.battery_soc_capacity)) *
                  100
                ).toFixed(0)
              : 0}
            %)
          </Typography>
        </Paper>
      )}

      <Paper sx={{ p: 2, borderRadius: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Historical Power Profiles
        </Typography>

        <Box sx={{ mb: 1.5 }}>
          <TimeWindowSelect value={windowMinutes} onChange={setWindowMinutes} />
        </Box>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mb: 0.5 }}
        >
          Solar Production
        </Typography>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={solarData}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis unit=" kW" tick={{ fontSize: 10 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#f0c040"
              name="Solar"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mt: 2, mb: 0.5 }}
        >
          Load
        </Typography>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={loadData}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis unit=" kW" tick={{ fontSize: 10 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#ef5350"
              name="Load"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </Paper>
    </Box>
  );
};

export default CommunityDashboard;
