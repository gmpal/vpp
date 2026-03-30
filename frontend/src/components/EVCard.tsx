import React, { useState } from "react";
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Collapse,
  Button,
  Slider,
  Paper,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import BoltIcon from "@mui/icons-material/Bolt";
import ElectricCarIcon from "@mui/icons-material/ElectricCar";
import { deleteVehicle, chargeVehicle, dischargeVehicle } from "../api";

interface EVCardProps {
  ev: any;
  onRefresh: () => void;
}

const EVCard: React.FC<EVCardProps> = ({ ev, onRefresh }) => {
  const [expanded, setExpanded] = useState(false);
  const [power, setPower] = useState(ev.max_charge_kw / 2);
  const socPct = ev.capacity_kwh > 0 ? (ev.soc_kwh / ev.capacity_kwh) * 100 : 0;
  const socColor =
    socPct > 70 ? "#4caf50" : socPct > 30 ? "#ff9800" : "#f44336";

  return (
    <Paper variant="outlined" sx={{ mt: 1.5, p: 1.5, borderRadius: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <ElectricCarIcon
          sx={{
            color: ev.status === "home" ? "#2196f3" : "#ff9800",
            fontSize: 20,
          }}
        />
        <Typography variant="body2" fontWeight="bold" sx={{ flex: 1 }}>
          {ev.name}
        </Typography>
        <Chip
          label={ev.status}
          size="small"
          color={ev.status === "home" ? "primary" : "warning"}
          sx={{ mr: 0.5 }}
        />
        <IconButton size="small" onClick={() => setExpanded((e) => !e)}>
          {expanded ? (
            <ExpandLessIcon fontSize="small" />
          ) : (
            <ExpandMoreIcon fontSize="small" />
          )}
        </IconButton>
        <IconButton
          size="small"
          color="error"
          onClick={async () => {
            await deleteVehicle(ev.vehicle_id);
            onRefresh();
          }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box sx={{ mt: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between" }}>
          <Typography variant="caption" color="text.secondary">
            SOC
          </Typography>
          <Typography variant="caption" fontWeight="bold" color={socColor}>
            {ev.soc_kwh.toFixed(1)}/{ev.capacity_kwh} kWh ({socPct.toFixed(0)}%)
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={socPct}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: "#e0e0e0",
            "& .MuiLinearProgress-bar": { bgcolor: socColor },
          }}
        />
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ mt: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            Power (kW)
          </Typography>
          <Slider
            value={power}
            min={0}
            max={Math.max(ev.max_charge_kw, ev.max_discharge_kw)}
            step={0.5}
            onChange={(_, v) => setPower(v as number)}
            size="small"
            marks
          />
          <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
            <Button
              size="small"
              variant="contained"
              startIcon={<BoltIcon />}
              onClick={async () => {
                await chargeVehicle(ev.vehicle_id, power);
                onRefresh();
              }}
              disabled={socPct >= 100}
              color="primary"
              sx={{ flex: 1 }}
            >
              Charge {power.toFixed(1)} kW
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={async () => {
                await dischargeVehicle(ev.vehicle_id, power);
                onRefresh();
              }}
              disabled={socPct <= 0}
              color="warning"
              sx={{ flex: 1 }}
            >
              Discharge
            </Button>
          </Box>
        </Box>
      </Collapse>
    </Paper>
  );
};

export default EVCard;
