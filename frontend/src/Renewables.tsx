import React, { useEffect, useMemo, useState } from "react";
import { CommunitySummary, fetchSourceIDs, getCommunitySummary } from "./api.ts";
import useLiveSeries from "./hooks/useLiveSeries";
import {
  Alert,
  Chip,
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
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

function formatTimestamp(timestamp: string): string {
  const d = new Date(timestamp);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  return `${hh}:${mm} ${dd}/${mo}`;
}

const SOURCE_COLORS: Record<string, string> = {
  solar: "#f0c040",
  wind: "#42a5f5",
};

const SOURCES = ["solar", "wind"];

const needsSourceId = (source: string): boolean =>
  source === "solar" || source === "wind";

const Renewables: React.FC = () => {
  const [selectedSource, setSelectedSource] = useState<string>("solar");
  const [selectedSourceID, setSelectedSourceID] = useState<string>("");
  const [sourceIDs, setSourceIDs] = useState<string[]>([]);
  const [selectedTopN, setSelectedTopN] = useState<number>(120);
  const [storageSummary, setStorageSummary] = useState<CommunitySummary | null>(
    null,
  );
  const [storageError, setStorageError] = useState<string>("");

  const liveEnabled = !needsSourceId(selectedSource) || !!selectedSourceID;
  const { data: liveData, loading, error, connected } = useLiveSeries({
    source: selectedSource,
    sourceId: selectedSourceID || undefined,
    historicalPoints: selectedTopN,
    maxPoints: selectedTopN,
    enabled: liveEnabled,
  });

  const chartData = useMemo(
    () =>
      liveData.map((p) => ({
        time: formatTimestamp(p.timestamp),
        value: p.value,
      })),
    [liveData],
  );

  useEffect(() => {
    async function updateSourceIDs() {
      if (!needsSourceId(selectedSource)) {
        setSourceIDs([]);
        setSelectedSourceID("");
        return;
      }
      try {
        const ids = await fetchSourceIDs(selectedSource);
        setSourceIDs(ids);
        if (!ids.includes(selectedSourceID)) {
          setSelectedSourceID(ids[0] || "");
        }
      } catch (error) {
        console.error("Error fetching source IDs:", error);
      }
    }
    updateSourceIDs();
  }, [selectedSource, selectedSourceID]);

  useEffect(() => {
    let cancelled = false;

    async function refreshStorage() {
      try {
        const summary = await getCommunitySummary();
        if (cancelled) {
          return;
        }
        setStorageSummary(summary);
        setStorageError("");
      } catch {
        if (!cancelled) {
          setStorageError("Could not load storage summary");
        }
      }
    }

    refreshStorage();
    const interval = setInterval(refreshStorage, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const lineColor = SOURCE_COLORS[selectedSource] ?? "#8884d8";
  const totalStorage =
    (storageSummary?.ev_soc_total ?? 0) +
    (storageSummary?.battery_soc_total ?? 0);
  const totalStorageCapacity =
    (storageSummary?.ev_soc_capacity ?? 0) +
    (storageSummary?.battery_soc_capacity ?? 0);
  const storagePct =
    totalStorageCapacity > 0 ? (totalStorage / totalStorageCapacity) * 100 : 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box my={4}>
        <Typography variant="h2" component="h1" gutterBottom align="center">
          Renewables
        </Typography>

        <Stack direction="row" spacing={1} justifyContent="center" mb={2}>
          <Chip
            label={connected ? "Live connected" : "Reconnecting"}
            color={connected ? "success" : "warning"}
            size="small"
          />
          <Chip label={`${selectedTopN} points`} size="small" variant="outlined" />
        </Stack>

        {(error || storageError) && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {error || storageError}
          </Alert>
        )}

        <Grid item xs={12}>
          <Paper elevation={3} sx={{ p: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="source-select-label">Select Source</InputLabel>
              <Select
                labelId="source-select-label"
                id="source-select"
                value={selectedSource}
                label="Select Source"
                onChange={(e) => setSelectedSource(e.target.value as string)}
              >
                {SOURCES.map((source) => (
                  <MenuItem key={source} value={source}>
                    {source.charAt(0).toUpperCase() + source.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Paper>
        </Grid>

        {needsSourceId(selectedSource) && (
          <Grid item xs={12}>
            <Paper elevation={3} sx={{ p: 2 }}>
              <FormControl fullWidth>
                <InputLabel id="source-id-select-label">
                  Select Source ID
                </InputLabel>
                <Select
                  labelId="source-id-select-label"
                  id="source-id-select"
                  value={selectedSourceID}
                  label="Select Source ID"
                  onChange={(e) =>
                    setSelectedSourceID(e.target.value as string)
                  }
                >
                  {sourceIDs.map((id) => (
                    <MenuItem key={id} value={id}>
                      {id}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Paper>
          </Grid>
        )}

        <Grid item xs={12}>
          <Paper elevation={3} sx={{ p: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="top-n-select-label">Select Top N</InputLabel>
              <Select
                labelId="top-n-select-label"
                id="top-n-select"
                value={selectedTopN}
                label="Select Top N"
                onChange={(e) => setSelectedTopN(e.target.value as number)}
              >
                {[60, 120, 180, 240].map((n) => (
                  <MenuItem key={n} value={n}>
                    {n}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Paper>
        </Grid>

        <Paper elevation={3} sx={{ p: 2 }}>
          {loading && chartData.length === 0 ? (
            <Typography color="text.secondary" align="center" py={4}>
              Connecting live stream...
            </Typography>
          ) : chartData.length === 0 ? (
            <Typography color="text.secondary" align="center" py={4}>
              No data
            </Typography>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 9, angle: -30, textAnchor: "end" }}
                  height={50}
                />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={lineColor}
                  name={
                    selectedSource.charAt(0).toUpperCase() +
                    selectedSource.slice(1)
                  }
                  dot={false}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Paper>

        <Paper elevation={3} sx={{ p: 2, mt: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            Energy Storage
          </Typography>
          {totalStorageCapacity <= 0 ? (
            <Typography color="text.secondary">No storage assets detected.</Typography>
          ) : (
            <Box>
              <Typography variant="body2" color="text.secondary">
                {totalStorage.toFixed(1)} / {totalStorageCapacity.toFixed(1)} kWh ({storagePct.toFixed(0)}%)
              </Typography>
              <Box
                sx={{
                  width: "100%",
                  height: 10,
                  borderRadius: 5,
                  mt: 1,
                  bgcolor: "rgba(0,0,0,0.08)",
                  overflow: "hidden",
                }}
              >
                <Box
                  sx={{
                    width: `${Math.max(0, Math.min(100, storagePct))}%`,
                    height: "100%",
                    bgcolor: storagePct > 80 ? "#43a047" : "#1e88e5",
                    transition: "width 0.4s ease",
                  }}
                />
              </Box>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default Renewables;
