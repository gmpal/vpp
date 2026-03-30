import React, { useEffect, useState } from "react";
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

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

const Grid: React.FC = () => {
  const [loadData, setLoadData] = useState<HistoricalDataPoint[]>([]);
  const [marketData, setMarketData] = useState<HistoricalDataPoint[]>([]);

  const fetchData = async () => {
    try {
      const [load, market] = await Promise.all([
        fetchHistoricalData("load", undefined, undefined, undefined, 100),
        fetchHistoricalData("market", undefined, undefined, undefined, 100),
      ]);
      setLoadData(load);
      setMarketData(market);
    } catch (err) {
      console.error("Error fetching grid data:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadChartData = loadData.map((p) => ({
    time: formatTime(p.timestamp),
    value: p.value,
  }));

  const marketChartData = marketData.map((p) => ({
    time: formatTime(p.timestamp),
    value: p.value,
  }));

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={3}>
        Grid
      </Typography>

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
