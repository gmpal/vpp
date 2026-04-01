import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Grid,
  Paper,
  LinearProgress,
  Alert,
  Tab,
  Tabs,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
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
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  getCommunitySummary,
  fetchHistoricalData,
  fetchSourceIDs,
  HistoricalDataPoint,
  getCommunities,
  createCommunity,
  deleteCommunity,
  getCommunityMembers,
  addCommunityMember,
  removeCommunityMember,
  getCommunityPolicy,
  setCommunityPolicy,
  getSettlementRuns,
  getSettlementLines,
  triggerSettlement,
  getCommunityGridLimits,
  setCommunityGridLimits,
  getCommunityBatteries,
  addCommunityBattery,
  removeCommunityBattery,
  getAllocationLedger,
} from "../api";

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
    return new Date(ts).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (e) {
      console.error(e);
    return ts;
  }
}

interface ChartDataPoint {
  time: string;
  value: number;
}

// ---------------------------------------------------------------------------
// Overview tab (original dashboard)
// ---------------------------------------------------------------------------

const OverviewTab: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [solarData, setSolarData] = useState<ChartDataPoint[]>([]);
  const [loadData, setLoadData] = useState<ChartDataPoint[]>([]);
  const [error, setError] = useState("");

  const fetchSummary = async () => {
    try {
      const s = await getCommunitySummary();
      setSummary(s);
    } catch (e) {
      console.error(e);
      setError("Could not load community data");
    }
  };

  const fetchProfiles = async () => {
    try {
      const solarIds = await fetchSourceIDs("solar");
      const firstSolarId =
        solarIds && solarIds.length > 0 ? solarIds[0] : undefined;
      const [solarRaw, loadRaw] = await Promise.all([
        firstSolarId
          ? fetchHistoricalData("solar", firstSolarId, undefined, undefined, 50)
          : Promise.resolve([] as HistoricalDataPoint[]),
        fetchHistoricalData("load", undefined, undefined, undefined, 50),
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
      console.error(e);
      setError("Could not load historical profiles");
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchProfiles();
    const summaryInterval = setInterval(fetchSummary, 30000);
    const profileInterval = setInterval(fetchProfiles, 30000);
    return () => {
      clearInterval(summaryInterval);
      clearInterval(profileInterval);
    };
  }, []);

  const actionInfo = summary
    ? ACTION_LABELS[summary.action] ?? ACTION_LABELS.self_sufficient
    : null;

  return (
    <Box>
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
      </Grid>

      {summary && summary.ev_count > 0 && (
        <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Fleet EV State of Charge
          </Typography>
          <LinearProgress
            variant="determinate"
            value={
              summary.ev_soc_capacity > 0
                ? (summary.ev_soc_total / summary.ev_soc_capacity) * 100
                : 0
            }
            sx={{ height: 12, borderRadius: 6 }}
            color="primary"
          />
          <Typography variant="caption" color="text.secondary">
            {summary.ev_soc_total.toFixed(1)} /{" "}
            {summary.ev_soc_capacity.toFixed(1)} kWh (
            {summary.ev_soc_capacity > 0
              ? (
                  (summary.ev_soc_total / summary.ev_soc_capacity) *
                  100
                ).toFixed(0)
              : 0}
            %)
          </Typography>
        </Paper>
      )}

      <Paper sx={{ p: 2, borderRadius: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Historical Power Profiles (last 50 points)
        </Typography>

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

// ---------------------------------------------------------------------------
// Setup tab: community CRUD + member management
// ---------------------------------------------------------------------------

const SetupTab: React.FC = () => {
  const [communities, setCommunities] = useState<any[]>([]);
  const [selectedCommunity, setSelectedCommunity] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [newCommunityName, setNewCommunityName] = useState("");
  const [newHouseholdId, setNewHouseholdId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const refreshCommunities = async () => {
    try {
      const data = await getCommunities();
      setCommunities(data);
    } catch (e) {
      console.error(e);
      setError("Could not load communities");
    }
  };

  const refreshMembers = async (communityId: string) => {
    try {
      const data = await getCommunityMembers(communityId);
      setMembers(data);
    } catch (e) {
      console.error(e);
      setError("Could not load members");
    }
  };

  useEffect(() => {
    refreshCommunities();
  }, []);

  useEffect(() => {
    if (selectedCommunity) {
      refreshMembers(selectedCommunity.community_id);
    }
  }, [selectedCommunity]);

  const handleCreateCommunity = async () => {
    if (!newCommunityName.trim()) return;
    setLoading(true);
    try {
      const c = await createCommunity({ name: newCommunityName.trim() });
      await refreshCommunities();
      setSelectedCommunity(c);
      setNewCommunityName("");
    } catch (e) {
      console.error(e);
      setError("Failed to create community");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCommunity = async (communityId: string) => {
    try {
      await deleteCommunity(communityId);
      await refreshCommunities();
      if (selectedCommunity?.community_id === communityId) {
        setSelectedCommunity(null);
        setMembers([]);
      }
    } catch (e) {
      console.error(e);
      setError("Failed to delete community");
    }
  };

  const handleAddMember = async () => {
    if (!selectedCommunity || !newHouseholdId.trim()) return;
    setLoading(true);
    try {
      await addCommunityMember(selectedCommunity.community_id, {
        household_id: newHouseholdId.trim(),
      });
      await refreshMembers(selectedCommunity.community_id);
      setNewHouseholdId("");
    } catch (e) {
      console.error(e);
      setError("Failed to add member");
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!selectedCommunity) return;
    try {
      await removeCommunityMember(selectedCommunity.community_id, memberId);
      await refreshMembers(selectedCommunity.community_id);
    } catch (e) {
      console.error(e);
      setError("Failed to remove member");
    }
  };

  return (
    <Box>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {/* Community list */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1}>
              Communities
            </Typography>
            <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
              <TextField
                size="small"
                label="New community name"
                value={newCommunityName}
                onChange={(e) => setNewCommunityName(e.target.value)}
                fullWidth
              />
              <Button
                variant="contained"
                onClick={handleCreateCommunity}
                disabled={loading || !newCommunityName.trim()}
                startIcon={<AddIcon />}
                size="small"
              >
                Create
              </Button>
            </Box>
            {communities.map((c) => (
              <Box
                key={c.community_id}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  p: 1,
                  mb: 0.5,
                  borderRadius: 1,
                  cursor: "pointer",
                  bgcolor:
                    selectedCommunity?.community_id === c.community_id
                      ? "action.selected"
                      : "transparent",
                  "&:hover": { bgcolor: "action.hover" },
                }}
                onClick={() => setSelectedCommunity(c)}
              >
                <Typography variant="body2" flexGrow={1}>
                  {c.name}
                </Typography>
                <Chip
                  label={`Export: ${c.export_limit_kw} kW`}
                  size="small"
                  sx={{ mr: 1, fontSize: 10 }}
                />
                <Button
                  size="small"
                  color="error"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteCommunity(c.community_id);
                  }}
                >
                  <DeleteIcon fontSize="small" />
                </Button>
              </Box>
            ))}
            {communities.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No communities yet. Create one above.
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Members */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1}>
              {selectedCommunity
                ? `Members — ${selectedCommunity.name}`
                : "Select a community"}
            </Typography>
            {selectedCommunity && (
              <>
                <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                  <TextField
                    size="small"
                    label="Household ID"
                    value={newHouseholdId}
                    onChange={(e) => setNewHouseholdId(e.target.value)}
                    fullWidth
                  />
                  <Button
                    variant="contained"
                    onClick={handleAddMember}
                    disabled={loading || !newHouseholdId.trim()}
                    startIcon={<AddIcon />}
                    size="small"
                  >
                    Add
                  </Button>
                </Box>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Member ID</TableCell>
                      <TableCell>Household ID</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell>Joined</TableCell>
                      <TableCell />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {members.map((m) => (
                      <TableRow key={m.member_id}>
                        <TableCell sx={{ fontSize: 11 }}>
                          {m.member_id}
                        </TableCell>
                        <TableCell sx={{ fontSize: 11 }}>
                          {m.household_id}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={m.role}
                            size="small"
                            color={m.role === "admin" ? "primary" : "default"}
                          />
                        </TableCell>
                        <TableCell sx={{ fontSize: 11 }}>
                          {m.joined_at
                            ? new Date(m.joined_at).toLocaleDateString()
                            : "—"}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="small"
                            color="error"
                            onClick={() => handleRemoveMember(m.member_id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    {members.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            py={2}
                          >
                            No members yet
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Policy & Allocation tab
// ---------------------------------------------------------------------------

const PolicyTab: React.FC = () => {
  const [communities, setCommunities] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [currentPolicy, setCurrentPolicy] = useState<any>(null);
  const [newPolicy, setNewPolicy] = useState("equal_share");
  const [ledger, setLedger] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCommunities().then(setCommunities).catch(() => {});
  }, []);

  const loadPolicyAndLedger = async (communityId: string) => {
    try {
      const p = await getCommunityPolicy(communityId).catch(() => null);
      setCurrentPolicy(p);
    } catch (e) {
      console.error(e);
      setCurrentPolicy(null);
    }
    try {
      const l = await getAllocationLedger(communityId, 50);
      setLedger(l);
    } catch (e) {
      console.error(e);
      setLedger([]);
    }
  };

  const handleSelectCommunity = (id: string) => {
    setSelectedId(id);
    loadPolicyAndLedger(id);
  };

  const handleSetPolicy = async () => {
    if (!selectedId) return;
    setLoading(true);
    try {
      const p = await setCommunityPolicy(selectedId, { policy: newPolicy });
      setCurrentPolicy(p);
    } catch (e) {
      console.error(e);
      setError("Failed to set policy");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1}>
              Select Community
            </Typography>
            <FormControl fullWidth size="small">
              <InputLabel>Community</InputLabel>
              <Select
                value={selectedId}
                label="Community"
                onChange={(e) => handleSelectCommunity(e.target.value)}
              >
                {communities.map((c) => (
                  <MenuItem key={c.community_id} value={c.community_id}>
                    {c.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {selectedId && (
              <Box mt={2}>
                <Typography variant="subtitle2" mb={1}>
                  Active Policy
                </Typography>
                {currentPolicy ? (
                  <Chip
                    label={currentPolicy.policy}
                    color="primary"
                    sx={{ mb: 2 }}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary" mb={1}>
                    No policy set
                  </Typography>
                )}

                <FormControl fullWidth size="small" sx={{ mb: 1 }}>
                  <InputLabel>New Policy</InputLabel>
                  <Select
                    value={newPolicy}
                    label="New Policy"
                    onChange={(e) => setNewPolicy(e.target.value)}
                  >
                    <MenuItem value="equal_share">Equal Share</MenuItem>
                    <MenuItem value="proportional">Proportional</MenuItem>
                    <MenuItem value="priority">Priority</MenuItem>
                  </Select>
                </FormControl>
                <Button
                  variant="contained"
                  onClick={handleSetPolicy}
                  disabled={loading}
                  fullWidth
                  size="small"
                >
                  {loading ? <CircularProgress size={18} /> : "Set Policy"}
                </Button>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1}>
              Allocation Ledger (last 50 transfers)
            </Typography>
            {ledger.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No allocation records yet. Allocations are created when the
                community runs a surplus distribution.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Interval</TableCell>
                    <TableCell>From</TableCell>
                    <TableCell>To</TableCell>
                    <TableCell align="right">kWh</TableCell>
                    <TableCell>Policy</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {ledger.map((e) => (
                    <TableRow key={e.ledger_id}>
                      <TableCell sx={{ fontSize: 11 }}>
                        {e.interval_start
                          ? new Date(e.interval_start).toLocaleString()
                          : "—"}
                      </TableCell>
                      <TableCell sx={{ fontSize: 11 }}>
                        {e.from_household_id}
                      </TableCell>
                      <TableCell sx={{ fontSize: 11 }}>
                        {e.to_household_id}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 11 }}>
                        {e.amount_kwh.toFixed(3)}
                      </TableCell>
                      <TableCell>
                        <Chip label={e.policy} size="small" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Settlement tab
// ---------------------------------------------------------------------------

const SettlementTab: React.FC = () => {
  const [communities, setCommunities] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [runs, setRuns] = useState<any[]>([]);
  const [lines, setLines] = useState<any[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getCommunities().then(setCommunities).catch(() => {});
  }, []);

  const loadRuns = async (communityId: string) => {
    try {
      const r = await getSettlementRuns(communityId);
      setRuns(r);
    } catch (e) {
      console.error(e);
      setRuns([]);
    }
  };

  const handleSelectCommunity = (id: string) => {
    setSelectedId(id);
    setSelectedRunId("");
    setLines([]);
    loadRuns(id);
  };

  const handleSettle = async () => {
    if (!selectedId || !periodStart || !periodEnd) return;
    setLoading(true);
    try {
      await triggerSettlement(selectedId, {
        period_start: periodStart,
        period_end: periodEnd,
      });
      await loadRuns(selectedId);
    } catch (e) {
      console.error(e);
      setError("Settlement failed");
    } finally {
      setLoading(false);
    }
  };

  const handleViewLines = async (runId: string) => {
    setSelectedRunId(runId);
    try {
      const l = await getSettlementLines(selectedId, runId);
      setLines(l);
    } catch (e) {
      console.error(e);
      setError("Could not load settlement lines");
    }
  };

  return (
    <Box>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <FormControl fullWidth size="small" sx={{ mb: 2 }}>
              <InputLabel>Community</InputLabel>
              <Select
                value={selectedId}
                label="Community"
                onChange={(e) => handleSelectCommunity(e.target.value)}
              >
                {communities.map((c) => (
                  <MenuItem key={c.community_id} value={c.community_id}>
                    {c.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {selectedId && (
              <>
                <Typography variant="subtitle2" mb={1}>
                  New Settlement Run
                </Typography>
                <TextField
                  size="small"
                  label="Period Start"
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  sx={{ mb: 1 }}
                />
                <TextField
                  size="small"
                  label="Period End"
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  sx={{ mb: 1 }}
                />
                <Button
                  variant="contained"
                  onClick={handleSettle}
                  disabled={loading || !periodStart || !periodEnd}
                  fullWidth
                  size="small"
                >
                  {loading ? <CircularProgress size={18} /> : "Run Settlement"}
                </Button>
              </>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" mb={1}>
              Settlement Runs
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Run ID</TableCell>
                  <TableCell>Period</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {runs.map((r) => (
                  <TableRow key={r.run_id}>
                    <TableCell sx={{ fontSize: 11 }}>{r.run_id}</TableCell>
                    <TableCell sx={{ fontSize: 11 }}>
                      {r.period_start?.slice(0, 10)} →{" "}
                      {r.period_end?.slice(0, 10)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={r.status}
                        size="small"
                        color={
                          r.status === "completed"
                            ? "success"
                            : r.status === "failed"
                              ? "error"
                              : "default"
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        onClick={() => handleViewLines(r.run_id)}
                        disabled={r.status !== "completed"}
                      >
                        View Lines
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {runs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        py={2}
                      >
                        No settlement runs
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            {lines.length > 0 && (
              <Box mt={2}>
                <Typography variant="subtitle2" mb={1}>
                  Lines for run: {selectedRunId}
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Household</TableCell>
                      <TableCell align="right">Net kWh</TableCell>
                      <TableCell align="right">Cost ($)</TableCell>
                      <TableCell align="right">Savings ($)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {lines.map((l) => (
                      <TableRow key={l.line_id}>
                        <TableCell sx={{ fontSize: 11 }}>
                          {l.household_id}
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            color: l.net_kwh >= 0 ? "#4caf50" : "#f44336",
                            fontSize: 11,
                          }}
                        >
                          {l.net_kwh.toFixed(2)}
                        </TableCell>
                        <TableCell align="right" sx={{ fontSize: 11 }}>
                          {l.cost.toFixed(4)}
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{ color: "#4caf50", fontSize: 11 }}
                        >
                          {l.savings.toFixed(4)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Grid & Battery tab
// ---------------------------------------------------------------------------

const GridBatteryTab: React.FC = () => {
  const [communities, setCommunities] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [gridLimit, setGridLimit] = useState<any>(null);
  const [batteries, setBatteries] = useState<any[]>([]);
  const [exportKw, setExportKw] = useState("100");
  const [importKw, setImportKw] = useState("100");
  const [newBattery, setNewBattery] = useState({
    household_id: "",
    name: "",
    capacity_kwh: "",
    soc_kwh: "",
    max_charge_kw: "",
    max_discharge_kw: "",
    eta: "0.95",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [batteryDialogOpen, setBatteryDialogOpen] = useState(false);

  useEffect(() => {
    getCommunities().then(setCommunities).catch(() => {});
  }, []);

  const loadData = async (communityId: string) => {
    try {
      const gl = await getCommunityGridLimits(communityId).catch(() => null);
      setGridLimit(gl);
      if (gl) {
        setExportKw(String(gl.export_limit_kw));
        setImportKw(String(gl.import_limit_kw));
      }
    } catch (e) {
      console.error(e);
      setGridLimit(null);
    }
    try {
      const b = await getCommunityBatteries(communityId);
      setBatteries(b);
    } catch (e) {
      console.error(e);
      setBatteries([]);
    }
  };

  const handleSelectCommunity = (id: string) => {
    setSelectedId(id);
    loadData(id);
  };

  const handleSetGridLimit = async () => {
    if (!selectedId) return;
    setLoading(true);
    try {
      const gl = await setCommunityGridLimits(selectedId, {
        export_limit_kw: parseFloat(exportKw),
        import_limit_kw: parseFloat(importKw),
      });
      setGridLimit(gl);
    } catch (e) {
      console.error(e);
      setError("Failed to set grid limit");
    } finally {
      setLoading(false);
    }
  };

  const handleAddBattery = async () => {
    if (!selectedId) return;
    setLoading(true);
    try {
      await addCommunityBattery(selectedId, {
        household_id: newBattery.household_id,
        name: newBattery.name,
        capacity_kwh: parseFloat(newBattery.capacity_kwh),
        soc_kwh: parseFloat(newBattery.soc_kwh),
        max_charge_kw: parseFloat(newBattery.max_charge_kw),
        max_discharge_kw: parseFloat(newBattery.max_discharge_kw),
        eta: parseFloat(newBattery.eta),
      });
      await loadData(selectedId);
      setBatteryDialogOpen(false);
      setNewBattery({
        household_id: "",
        name: "",
        capacity_kwh: "",
        soc_kwh: "",
        max_charge_kw: "",
        max_discharge_kw: "",
        eta: "0.95",
      });
    } catch (e) {
      console.error(e);
      setError("Failed to add battery");
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveBattery = async (batteryId: string) => {
    if (!selectedId) return;
    try {
      await removeCommunityBattery(selectedId, batteryId);
      await loadData(selectedId);
    } catch (e) {
      console.error(e);
      setError("Failed to remove battery");
    }
  };

  return (
    <Box>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <FormControl fullWidth size="small" sx={{ mb: 2, maxWidth: 300 }}>
        <InputLabel>Community</InputLabel>
        <Select
          value={selectedId}
          label="Community"
          onChange={(e) => handleSelectCommunity(e.target.value)}
        >
          {communities.map((c) => (
            <MenuItem key={c.community_id} value={c.community_id}>
              {c.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedId && (
        <Grid container spacing={2}>
          {/* Grid limits */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight="bold" mb={1}>
                Grid Connection Limits
              </Typography>

              {gridLimit ? (
                <Box mb={2}>
                  <Chip
                    label={`Export: ${gridLimit.export_limit_kw} kW`}
                    color="warning"
                    sx={{ mr: 1 }}
                  />
                  <Chip
                    label={`Import: ${gridLimit.import_limit_kw} kW`}
                    color="info"
                  />
                </Box>
              ) : (
                <Alert severity="info" sx={{ mb: 1 }}>
                  No grid limit set — unconstrained
                </Alert>
              )}

              <TextField
                size="small"
                label="Export Limit (kW)"
                value={exportKw}
                onChange={(e) => setExportKw(e.target.value)}
                type="number"
                fullWidth
                sx={{ mb: 1 }}
              />
              <TextField
                size="small"
                label="Import Limit (kW)"
                value={importKw}
                onChange={(e) => setImportKw(e.target.value)}
                type="number"
                fullWidth
                sx={{ mb: 1 }}
              />
              <Button
                variant="contained"
                onClick={handleSetGridLimit}
                disabled={loading}
                fullWidth
                size="small"
              >
                {loading ? <CircularProgress size={18} /> : "Set Limits"}
              </Button>
            </Paper>
          </Grid>

          {/* Batteries */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1,
                }}
              >
                <Typography variant="subtitle1" fontWeight="bold">
                  Stationary Batteries
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => setBatteryDialogOpen(true)}
                >
                  Add Battery
                </Button>
              </Box>

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Household</TableCell>
                    <TableCell align="right">Cap (kWh)</TableCell>
                    <TableCell align="right">SOC (kWh)</TableCell>
                    <TableCell align="right">Max (kW)</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {batteries.map((b) => (
                    <TableRow key={b.battery_id}>
                      <TableCell sx={{ fontSize: 11 }}>{b.name}</TableCell>
                      <TableCell sx={{ fontSize: 11 }}>
                        {b.household_id}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 11 }}>
                        {b.capacity_kwh}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 11 }}>
                        {b.soc_kwh}
                      </TableCell>
                      <TableCell align="right" sx={{ fontSize: 11 }}>
                        {b.max_charge_kw}/{b.max_discharge_kw}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          color="error"
                          onClick={() => handleRemoveBattery(b.battery_id)}
                        >
                          <DeleteIcon fontSize="small" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {batteries.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          py={2}
                        >
                          No batteries registered
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Add battery dialog */}
      <Dialog
        open={batteryDialogOpen}
        onClose={() => setBatteryDialogOpen(false)}
      >
        <DialogTitle>Add Stationary Battery</DialogTitle>
        <DialogContent>
          {(
            [
              ["household_id", "Household ID", "text"],
              ["name", "Battery Name", "text"],
              ["capacity_kwh", "Capacity (kWh)", "number"],
              ["soc_kwh", "Initial SOC (kWh)", "number"],
              ["max_charge_kw", "Max Charge (kW)", "number"],
              ["max_discharge_kw", "Max Discharge (kW)", "number"],
              ["eta", "Efficiency (η)", "number"],
            ] as [keyof typeof newBattery, string, string][]
          ).map(([field, label, type]) => (
            <TextField
              key={field}
              size="small"
              label={label}
              type={type}
              value={newBattery[field]}
              onChange={(e) =>
                setNewBattery((prev) => ({ ...prev, [field]: e.target.value }))
              }
              fullWidth
              sx={{ mt: 1 }}
            />
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatteryDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddBattery}
            variant="contained"
            disabled={loading}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

// ---------------------------------------------------------------------------
// Main component with tabs
// ---------------------------------------------------------------------------

const CommunityDashboard: React.FC = () => {
  const [tab, setTab] = useState(0);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Community Dashboard
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3 }}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label="Overview" />
        <Tab label="Community Setup" />
        <Tab label="Policy & Allocation" />
        <Tab label="Settlement" />
        <Tab label="Grid & Batteries" />
      </Tabs>

      {tab === 0 && <OverviewTab />}
      {tab === 1 && <SetupTab />}
      {tab === 2 && <PolicyTab />}
      {tab === 3 && <SettlementTab />}
      {tab === 4 && <GridBatteryTab />}
    </Box>
  );
};

export default CommunityDashboard;
