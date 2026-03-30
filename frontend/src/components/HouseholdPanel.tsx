import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Alert,
  LinearProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import HomeIcon from "@mui/icons-material/Home";
import ElectricCarIcon from "@mui/icons-material/ElectricCar";
import {
  getHouseholds,
  createHousehold,
  deleteHousehold,
  getVehicles,
  createVehicle,
  deleteVehicle,
} from "../api";

const HouseholdPanel: React.FC = () => {
  const [households, setHouseholds] = useState<any[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [addHHDialog, setAddHHDialog] = useState(false);
  const [addEVDialog, setAddEVDialog] = useState(false);
  const [selectedHH, setSelectedHH] = useState("");
  const [error, setError] = useState("");

  const [hhForm, setHHForm] = useState({
    name: "",
    latitude: "50.85",
    longitude: "4.35",
  });
  const [evForm, setEVForm] = useState({
    name: "My EV",
    capacity_kwh: "75",
    soc_kwh: "37.5",
    max_charge_kw: "11",
    max_discharge_kw: "7",
    eta: "0.9",
  });

  const loadData = async () => {
    try {
      const [h, v] = await Promise.all([getHouseholds(), getVehicles()]);
      setHouseholds(h);
      setVehicles(v);
    } catch (e) {
      setError("Failed to load data");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddHH = async () => {
    try {
      await createHousehold({
        name: hhForm.name || "New Household",
        latitude: parseFloat(hhForm.latitude),
        longitude: parseFloat(hhForm.longitude),
      });
      setAddHHDialog(false);
      loadData();
    } catch {
      setError("Failed to add household");
    }
  };

  const handleAddEV = async () => {
    if (!selectedHH) return;
    try {
      await createVehicle({
        household_id: selectedHH,
        name: evForm.name,
        capacity_kwh: parseFloat(evForm.capacity_kwh),
        soc_kwh: parseFloat(evForm.soc_kwh),
        max_charge_kw: parseFloat(evForm.max_charge_kw),
        max_discharge_kw: parseFloat(evForm.max_discharge_kw),
        eta: parseFloat(evForm.eta),
      });
      setAddEVDialog(false);
      loadData();
    } catch {
      setError("Failed to add EV");
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Households & EVs
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mt: 3, mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddHHDialog(true)}
        >
          Add Household
        </Button>
        <Button
          variant="outlined"
          startIcon={<ElectricCarIcon />}
          onClick={() => setAddEVDialog(true)}
          disabled={households.length === 0}
        >
          Add EV
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {households.map((hh) => {
          const hhVehicles = vehicles.filter(
            (v) => v.household_id === hh.household_id,
          );
          return (
            <Grid item xs={12} md={6} key={hh.household_id}>
              <Paper
                sx={{ p: 2, borderRadius: 2, border: "1px solid #e0e0e0" }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <HomeIcon color="success" />
                    <Typography variant="h6">{hh.name}</Typography>
                  </Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Chip
                      label={`${hhVehicles.length} EV${
                        hhVehicles.length !== 1 ? "s" : ""
                      }`}
                      size="small"
                      color="primary"
                    />
                    <IconButton
                      size="small"
                      color="error"
                      onClick={async () => {
                        await deleteHousehold(hh.household_id);
                        loadData();
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {hh.latitude.toFixed(4)}, {hh.longitude.toFixed(4)}
                </Typography>
                {hhVehicles.map((ev) => (
                  <Paper
                    key={ev.vehicle_id}
                    variant="outlined"
                    sx={{ mt: 1, p: 1.5, borderRadius: 2 }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <ElectricCarIcon
                        sx={{
                          fontSize: 18,
                          color: ev.status === "home" ? "#2196f3" : "#ff9800",
                        }}
                      />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {ev.name}
                      </Typography>
                      <Chip
                        label={ev.status}
                        size="small"
                        color={ev.status === "home" ? "primary" : "warning"}
                      />
                      <IconButton
                        size="small"
                        color="error"
                        onClick={async () => {
                          await deleteVehicle(ev.vehicle_id);
                          loadData();
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={
                        ev.capacity_kwh > 0
                          ? (ev.soc_kwh / ev.capacity_kwh) * 100
                          : 0
                      }
                      sx={{ mt: 0.5, height: 6, borderRadius: 3 }}
                    />
                  </Paper>
                ))}
              </Paper>
            </Grid>
          );
        })}
        {households.length === 0 && (
          <Grid item xs={12}>
            <Paper
              sx={{
                p: 4,
                textAlign: "center",
                color: "text.secondary",
                borderRadius: 2,
              }}
            >
              <HomeIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
              <Typography>
                No households yet. Add one to get started.
              </Typography>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* Add Household Dialog */}
      <Dialog
        open={addHHDialog}
        onClose={() => setAddHHDialog(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Add Household</DialogTitle>
        <DialogContent>
          <TextField
            label="Name"
            value={hhForm.name}
            onChange={(e) => setHHForm((f) => ({ ...f, name: e.target.value }))}
            fullWidth
            margin="normal"
          />
          <TextField
            label="Latitude"
            value={hhForm.latitude}
            onChange={(e) =>
              setHHForm((f) => ({ ...f, latitude: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
          <TextField
            label="Longitude"
            value={hhForm.longitude}
            onChange={(e) =>
              setHHForm((f) => ({ ...f, longitude: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddHHDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAddHH}>
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add EV Dialog */}
      <Dialog
        open={addEVDialog}
        onClose={() => setAddEVDialog(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Add Electric Vehicle</DialogTitle>
        <DialogContent>
          <TextField
            select
            label="Household"
            value={selectedHH}
            onChange={(e) => setSelectedHH(e.target.value)}
            fullWidth
            margin="normal"
            SelectProps={{ native: true }}
          >
            <option value="">Select household</option>
            {households.map((h) => (
              <option key={h.household_id} value={h.household_id}>
                {h.name}
              </option>
            ))}
          </TextField>
          <TextField
            label="Name"
            value={evForm.name}
            onChange={(e) => setEVForm((f) => ({ ...f, name: e.target.value }))}
            fullWidth
            margin="normal"
          />
          <TextField
            label="Battery Capacity (kWh)"
            value={evForm.capacity_kwh}
            onChange={(e) =>
              setEVForm((f) => ({ ...f, capacity_kwh: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
          <TextField
            label="Current SOC (kWh)"
            value={evForm.soc_kwh}
            onChange={(e) =>
              setEVForm((f) => ({ ...f, soc_kwh: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
          <TextField
            label="Max Charge Rate (kW)"
            value={evForm.max_charge_kw}
            onChange={(e) =>
              setEVForm((f) => ({ ...f, max_charge_kw: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
          <TextField
            label="Max Discharge Rate (kW)"
            value={evForm.max_discharge_kw}
            onChange={(e) =>
              setEVForm((f) => ({ ...f, max_discharge_kw: e.target.value }))
            }
            fullWidth
            margin="normal"
            type="number"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddEVDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddEV}
            disabled={!selectedHH}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default HouseholdPanel;
