import React, { useCallback, useEffect, useState } from "react";
import { Box, Typography, Paper } from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { fetchHistoricalData, HistoricalDataPoint } from "./api.ts";
import TimeWindowSelect from "./components/TimeWindowSelect";
import {
  DEFAULT_TIME_WINDOW_MINUTES,
  formatTimeWithSeconds,
  getPointLimitForWindow,
  getTimeWindowRange,
} from "./timeWindow";

const Grid: React.FC = () => {
  const [loadData, setLoadData] = useState<HistoricalDataPoint[]>([]);
  const [marketData, setMarketData] = useState<HistoricalDataPoint[]>([]);
  const [windowMinutes, setWindowMinutes] = useState<number>(
    DEFAULT_TIME_WINDOW_MINUTES,
  );

  const fetchData = useCallback(async () => {
    const { startIso, endIso } = getTimeWindowRange(windowMinutes);
    const top = getPointLimitForWindow(windowMinutes);
    try {
      const [load, market] = await Promise.all([
        fetchHistoricalData("load", undefined, startIso, endIso, top),
        fetchHistoricalData("market", undefined, startIso, endIso, top),
      ]);
      setLoadData(load);
      setMarketData(market);
    } catch (err) {
      console.error("Error fetching grid data:", err);
    }
  }, [windowMinutes]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const loadChartData = loadData.map((p) => ({
    time: formatTimeWithSeconds(p.timestamp),
    value: p.value,
  }));

  const marketChartData = marketData.map((p) => ({
    time: formatTimeWithSeconds(p.timestamp),
    value: p.value,
  }));

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={3}>
        Grid
      </Typography>

      <Box sx={{ mb: 2 }}>
        <TimeWindowSelect value={windowMinutes} onChange={setWindowMinutes} />
      </Box>

      <Paper elevation={3} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
          Load
        </Typography>
        {loadChartData.length === 0 ? (
          <Typography color="text.secondary" align="center" py={4}>
            No data
          </Typography>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={loadChartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
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
        )}
      </Paper>

      <Paper elevation={3} sx={{ p: 2, borderRadius: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
          Market Price
        </Typography>
        {marketChartData.length === 0 ? (
          <Typography color="text.secondary" align="center" py={4}>
            No data
          </Typography>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={marketChartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#4caf50"
                name="Market Price"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Paper>
    </Box>
  );
};

export default Grid;
