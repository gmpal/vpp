import React, { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Typography,
  Divider,
} from "@mui/material";
import {
  getSources,
  deleteSource,
  getHouseholds,
  createHousehold,
  deleteHousehold,
  updateHousehold,
  getVehicles,
  createVehicle,
  HouseholdData,
} from "../api";
import { solarIntensityFactor } from "../utils/solarPosition";

const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

// Default EV parameters when auto-creating from a community building
const DEFAULT_EV = {
  capacity_kwh: 60,
  soc_kwh: 30,
  max_charge_kw: 7.4,
  max_discharge_kw: 7.4,
  eta: 0.9,
};

const Map3D: React.FC = () => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const mapReadyRef = useRef(false);

  const [sources, setSources] = useState<any[]>([]);
  const [households, setHouseholds] = useState<HouseholdData[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);

  // Building community dialog (click on OSM building)
  const [clickedLatLng, setClickedLatLng] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [buildingDialog, setBuildingDialog] = useState(false);
  const [buildingName, setBuildingName] = useState("");
  const [buildingType, setBuildingType] = useState<"household" | "office">(
    "household",
  );
  const [solarPanels, setSolarPanels] = useState(4);
  const [numPeople, setNumPeople] = useState(3);
  const [numEvs, setNumEvs] = useState(1);

  const householdsRef = useRef<HouseholdData[]>([]);
  useEffect(() => {
    householdsRef.current = households;
  }, [households]);

  // Initialize map once
  useEffect(() => {
    if (mapRef.current || !mapContainer.current) return;
    const m = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: [4.35, 50.85],
      zoom: 14,
    });
    m.addControl(new maplibregl.NavigationControl(), "top-right");

    m.on("style.load", () => {
      mapReadyRef.current = true;
    });

    m.on("click", (e) => {
      setClickedLatLng({ lat: e.lngLat.lat, lng: e.lngLat.lng });
      setBuildingName("");
      setBuildingType("household");
      setSolarPanels(4);
      setNumPeople(3);
      setNumEvs(1);
      setBuildingDialog(true);
    });

    mapRef.current = m;
    return () => {
      m.remove();
      mapRef.current = null;
      mapReadyRef.current = false;
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [s, h, v] = await Promise.all([
        getSources(),
        getHouseholds(),
        getVehicles(),
      ]);
      setSources(s);
      setHouseholds(h);
      setVehicles(v);
    } catch (e) {
      console.error("Failed to load map data", e);
    }
  }, []);

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 10000);
    return () => clearInterval(id);
  }, [loadData]);

  // Expose delete callbacks for popup HTML buttons
  useEffect(() => {
    (window as any).__deleteSource = async (id: string) => {
      await deleteSource(id);
      loadData();
    };
    (window as any).__deleteHousehold = async (id: string) => {
      await deleteHousehold(id);
      loadData();
    };
    (window as any).__updateHouseholdPanels = async (
      id: string,
      delta: number,
    ) => {
      const hh = householdsRef.current.find((item) => item.household_id === id);
      if (!hh) return;
      const nextPanels = Math.max(0, (hh.solar_panels ?? 0) + Number(delta));
      await updateHousehold(id, { solar_panels: nextPanels });
      loadData();
    };
  }, [loadData]);

  // Rebuild markers for sources, community rooftops, and vehicles
  useEffect(() => {
    if (!mapRef.current) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const intensity = solarIntensityFactor(50.85, 4.35, new Date());

    const addMarker = (
      lng: number,
      lat: number,
      emoji: string,
      bg: string,
      border: string,
      popupHtml: string,
    ) => {
      const el = Object.assign(document.createElement("div"), {
        textContent: emoji,
        style: `width:34px;height:34px;border-radius:50%;background:${bg};border:2px solid ${border};
                display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:17px;
                box-shadow:0 2px 6px rgba(0,0,0,0.4);`,
      });
      el.addEventListener("click", (event) => event.stopPropagation());
      const popup = new maplibregl.Popup({
        offset: 25,
        maxWidth: "220px",
      }).setHTML(popupHtml);
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(mapRef.current!);
      markersRef.current.push(marker);
    };

    const addRooftopSolarMarker = (
      lng: number,
      lat: number,
      householdId: string,
      name: string,
      panels: number,
    ) => {
      const el = document.createElement("div");
      el.style.cssText = `
        width: 28px;
        height: 40px;
        cursor: pointer;
        transform: translateY(-2px);
        filter: drop-shadow(0 1px 4px rgba(0,0,0,0.45));
      `;
      el.addEventListener("click", (event) => event.stopPropagation());
      el.innerHTML = `
        <svg viewBox="0 0 28 40" width="28" height="40" aria-hidden="true">
          <circle cx="14" cy="13" r="10" fill="#1565C0" stroke="#E3F2FD" stroke-width="2"/>
          <path d="M9 10h10v6H9z" fill="#90CAF9" stroke="#E3F2FD" stroke-width="1"/>
          <path d="M11 10v6M14 10v6M17 10v6M9 13h10" stroke="#E3F2FD" stroke-width="0.8"/>
          <path d="M14 37 L8 24 L20 24 Z" fill="#1565C0" stroke="#E3F2FD" stroke-width="2"/>
        </svg>
      `;
      const popup = new maplibregl.Popup({ offset: 20, maxWidth: "220px" })
        .setHTML(`
        <b>${name}</b><br/>
        <small>Community rooftop &bull; ${panels} solar panel${panels === 1 ? "" : "s"
          }</small>
        <div style="display:flex;gap:6px;margin-top:8px;">
          <button onclick="window.__updateHouseholdPanels('${householdId}', -1)"
            style="cursor:pointer;padding:2px 8px;border-radius:4px;border:1px solid #1565C0;background:#fff;">
            - Panel
          </button>
          <button onclick="window.__updateHouseholdPanels('${householdId}', 1)"
            style="cursor:pointer;padding:2px 8px;border-radius:4px;border:1px solid #1565C0;background:#fff;">
            + Panel
          </button>
        </div>
        <button onclick="window.__deleteHousehold('${householdId}')"
          style="margin-top:8px;color:#b00020;border:1px solid #b00020;background:none;cursor:pointer;padding:2px 8px;border-radius:4px;font-size:11px">
          Remove from community
        </button>
      `);
      const marker = new maplibregl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(mapRef.current!);
      markersRef.current.push(marker);
    };

    sources
      .filter((s) => s.source_type === "solar")
      .forEach((s) => {
        const bg =
          intensity > 0
            ? `rgba(255,200,0,${(0.4 + intensity * 0.6).toFixed(2)})`
            : "rgba(120,120,120,0.5)";
        addMarker(
          s.longitude,
          s.latitude,
          "\u2600",
          bg,
          "#f0c040",
          `
        <b>${s.name || s.source_id}</b><br/>
        <small>${s.current_value != null
            ? s.current_value.toFixed(2) + " kW"
            : "No data"
          }</small><br/>
        <button onclick="window.__deleteSource('${s.source_id}')"
          style="margin-top:4px;color:red;border:1px solid red;background:none;cursor:pointer;padding:2px 8px;border-radius:4px;font-size:11px">
          Remove
        </button>`,
        );
      });

    households
      .filter((hh) => hh.latitude != null && hh.longitude != null)
      .forEach((hh) => {
        addRooftopSolarMarker(
          hh.longitude!,
          hh.latitude!,
          hh.household_id,
          hh.name,
          hh.solar_panels ?? 0,
        );
      });

    vehicles
      .filter((ev) => ev.latitude && ev.longitude)
      .forEach((ev) => {
        const isHome = ev.status === "home";
        const bg = isHome ? "rgba(33,150,243,0.7)" : "rgba(255,152,0,0.7)";
        const border = isHome ? "#2196f3" : "#ff9800";
        const soc =
          ev.capacity_kwh > 0
            ? ((ev.soc_kwh / ev.capacity_kwh) * 100).toFixed(0)
            : 0;
        addMarker(
          ev.longitude,
          ev.latitude,
          "\uD83D\uDE97",
          bg,
          border,
          `
        <b>${ev.name}</b> (${ev.status})<br/>
        <small>SOC: ${ev.soc_kwh.toFixed(1)}/${ev.capacity_kwh
          } kWh (${soc}%)</small>`,
        );
      });
  }, [sources, households, vehicles]);

  // Enroll a building in the community
  const handleAddBuilding = async () => {
    if (!clickedLatLng) return;
    try {
      const hh = await createHousehold({
        name: buildingName || "Building",
        latitude: clickedLatLng.lat,
        longitude: clickedLatLng.lng,
        solar_panels: solarPanels,
        building_type: buildingType,
        num_people: numPeople,
        num_evs: numEvs,
      });

      // Auto-create EVs
      for (let i = 0; i < numEvs; i++) {
        await createVehicle({
          household_id: hh.household_id,
          name: `${hh.name} EV ${i + 1}`,
          ...DEFAULT_EV,
        });
      }

      setBuildingDialog(false);
      setClickedLatLng(null);
      loadData();
    } catch (e) {
      console.error("Failed to add building", e);
    }
  };

  return (
    <Box sx={{ width: "100%", height: "100%", position: "relative" }}>
      <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />

      {/* Building community enrollment dialog */}
      <Dialog
        open={buildingDialog}
        onClose={() => setBuildingDialog(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Add Building to Community</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}
        >
          <TextField
            label="Building name (optional)"
            value={buildingName}
            onChange={(e) => setBuildingName(e.target.value)}
            fullWidth
          />
          <Divider />
          <FormControl fullWidth>
            <InputLabel>Building type</InputLabel>
            <Select
              value={buildingType}
              onChange={(e) => setBuildingType(e.target.value as any)}
              label="Building type"
            >
              <MenuItem value="household">Household / Residential</MenuItem>
              <MenuItem value="office">Office / Commercial</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label="Number of people"
            type="number"
            value={numPeople}
            onChange={(e) =>
              setNumPeople(Math.max(1, parseInt(e.target.value) || 1))
            }
            helperText="Acts as a consumption multiplier"
            fullWidth
            inputProps={{ min: 1 }}
          />
          <Divider />
          <TextField
            label="Solar panels"
            type="number"
            value={solarPanels}
            onChange={(e) =>
              setSolarPanels(Math.max(0, parseInt(e.target.value) || 0))
            }
            helperText="Acts as a production multiplier"
            fullWidth
            inputProps={{ min: 0 }}
          />
          <TextField
            label="Electric cars"
            type="number"
            value={numEvs}
            onChange={(e) =>
              setNumEvs(Math.max(0, parseInt(e.target.value) || 0))
            }
            helperText="Each car = 60 kWh battery (V2G capable)"
            fullWidth
            inputProps={{ min: 0 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBuildingDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            onClick={handleAddBuilding}
          >
            Add to Community
          </Button>
        </DialogActions>
      </Dialog>

      {/* Map legend */}
      <Box
        sx={{
          position: "absolute",
          bottom: 16,
          left: 16,
          zIndex: 1,
          bgcolor: "rgba(0,0,0,0.72)",
          borderRadius: 2,
          p: 1.5,
          display: "flex",
          flexDirection: "column",
          gap: 0.4,
          pointerEvents: "none",
        }}
      >
        <Typography variant="caption" color="white" fontWeight="bold">
          Click map to place a community household
        </Typography>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.2)", my: 0.5 }} />
        {[
          ["\uD83D\uDD06", "Community rooftop solar"],
          ["\uD83D\uDE97", "EV"],
        ].map(([icon, label]) => (
          <Typography key={label} variant="caption" color="white">
            {icon} {label}
          </Typography>
        ))}
      </Box>
    </Box>
  );
};

export default Map3D;
