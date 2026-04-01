import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
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
  Legend,
} from "recharts";
import {
  fetchForecastedData,
  fetchSourceIDs,
  ForecastedDataPoint,
} from "../api";
import { format } from "date-fns";
import TimeWindowSelect from "./TimeWindowSelect";
import {
  DEFAULT_TIME_WINDOW_MINUTES,
  getTimeWindowRange,
} from "../timeWindow";

const SOURCE_TYPES = ["solar", "load", "market"];

const UNIT_MAP: Record<string, string> = {
  solar: " kW",
  load: " kW",
  market: " €/MWh",
};

const needsSourceId = (source: string) => source === "solar";

const formatTimestamp = (ts: string): string => {
  try {
    return format(new Date(ts), "HH:mm:ss dd/MM");
  } catch {
    return ts;
  }
};

const ForecastTab: React.FC = () => {
  const [selectedSource, setSelectedSource] = useState<string>("solar");
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [forecastData, setForecastData] = useState<ForecastedDataPoint[]>([]);
  const [error, setError] = useState<string>("");
  const [windowMinutes, setWindowMinutes] = useState<number>(
    DEFAULT_TIME_WINDOW_MINUTES,
  );

  // Fetch source IDs when source type changes
  useEffect(() => {
    if (!needsSourceId(selectedSource)) {
      setSourceIds([]);
      setSelectedSourceId("");
      return;
    }
    fetchSourceIDs(selectedSource)
      .then((ids) => {
        setSourceIds(ids);
        setSelectedSourceId(ids[0] ?? "");
      })
      .catch(() => {
        setSourceIds([]);
        setSelectedSourceId("");
      });
  }, [selectedSource]);

  // Fetch forecast data when source or sourceId changes
  useEffect(() => {
    const { startIso, endIso } = getTimeWindowRange(windowMinutes);
    const sourceIdParam = needsSourceId(selectedSource)
      ? selectedSourceId
      : undefined;

    // If source needs a source_id but none is selected yet, skip fetching
    if (needsSourceId(selectedSource) && !selectedSourceId) return;

    const load = async () => {
      setError("");
      try {
        const data = await fetchForecastedData(
          selectedSource,
          sourceIdParam,
          startIso,
          endIso,
        );
        setForecastData(data);
      } catch {
        setForecastData([]);
        setError(
          "Failed to fetch forecast data. Check that the backend is running.",
        );
      }
    };

    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [selectedSource, selectedSourceId, windowMinutes]);

  const chartData = forecastData.map((point) => ({
    timestamp: formatTimestamp(point.timestamp),
    value: point.value,
  }));

  const unit = UNIT_MAP[selectedSource] ?? "";

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Forecast Viewer
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3, borderRadius: 2, mb: 3 }}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <FormControl sx={{ minWidth: 160 }}>
            <InputLabel id="forecast-source-label">Source Type</InputLabel>
            <Select
              labelId="forecast-source-label"
              value={selectedSource}
              label="Source Type"
              onChange={(e) => setSelectedSource(e.target.value)}
            >
              {SOURCE_TYPES.map((s) => (
                <MenuItem key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {needsSourceId(selectedSource) && (
            <FormControl sx={{ minWidth: 160 }}>
              <InputLabel id="forecast-source-id-label">Source ID</InputLabel>
              <Select
                labelId="forecast-source-id-label"
                value={selectedSourceId}
                label="Source ID"
                onChange={(e) => setSelectedSourceId(e.target.value)}
              >
                {sourceIds.map((id) => (
                  <MenuItem key={id} value={id}>
                    {id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <TimeWindowSelect value={windowMinutes} onChange={setWindowMinutes} />
        </Box>
      </Paper>

      <Paper sx={{ p: 3, borderRadius: 2 }}>
        {chartData.length === 0 ? (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 300,
            }}
          >
            <Typography variant="body1" color="text.secondary">
              No forecast data available. Run inference first.
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
              <YAxis unit={unit} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#9c27b0"
                strokeDasharray="5 5"
                strokeWidth={2}
                dot={false}
                name={`${
                  selectedSource.charAt(0).toUpperCase() +
                  selectedSource.slice(1)
                } Forecast`}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Paper>
    </Box>
  );
};

export default ForecastTab;
