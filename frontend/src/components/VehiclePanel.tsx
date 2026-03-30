import React, { useEffect, useState } from "react";
import { Box, Typography, Paper, Grid, Alert } from "@mui/material";
import ElectricCarIcon from "@mui/icons-material/ElectricCar";
import { getHouseholds, getVehicles } from "../api";
import EVCard from "./EVCard";

const VehiclePanel: React.FC = () => {
  const [households, setHouseholds] = useState<any[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [error, setError] = useState("");

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

  const totalVehicles = vehicles.length;

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Vehicles
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {totalVehicles === 0 ? (
        <Paper
          sx={{
            p: 4,
            textAlign: "center",
            color: "text.secondary",
            borderRadius: 2,
          }}
        >
          <ElectricCarIcon sx={{ fontSize: 48, mb: 1, opacity: 0.3 }} />
          <Typography>
            No vehicles yet. Add households and EVs from the Households page.
          </Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {households.map((hh) => {
            const hhVehicles = vehicles.filter(
              (v) => v.household_id === hh.household_id,
            );
            if (hhVehicles.length === 0) return null;
            return (
              <Grid item xs={12} key={hh.household_id}>
                <Typography
                  variant="subtitle1"
                  fontWeight="bold"
                  sx={{ mb: 1, color: "text.secondary" }}
                >
                  {hh.name}
                </Typography>
                <Grid container spacing={2}>
                  {hhVehicles.map((ev) => (
                    <Grid item xs={12} sm={6} md={4} key={ev.vehicle_id}>
                      <EVCard ev={ev} onRefresh={loadData} />
                    </Grid>
                  ))}
                </Grid>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

export default VehiclePanel;
