import React, { useState, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
  Circle,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  Box,
  Typography,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Paper,
  Card,
  CardContent,
  Grid,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import SolarPowerIcon from "@mui/icons-material/SolarPower";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import BatteryChargingFullIcon from "@mui/icons-material/BatteryChargingFull";
import TuneIcon from "@mui/icons-material/Tune";
import MenuIcon from "@mui/icons-material/Menu";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import {
  createSource,
  getSources,
  deleteSource,
  getTrainingStatus,
  triggerTraining,
  triggerInference,
  generateSystemData,
  TrainingStatus,
} from "./api";
import { useNavigate } from "react-router-dom";

// Fix Leaflet default marker icon issue
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom icons for energy sources
const solarIcon = new L.Icon({
  iconUrl:
    "data:image/svg+xml;base64," +
    btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FFA500" width="48" height="48">
      <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"/>
      <circle cx="12" cy="12" r="3" fill="#FFD700"/>
    </svg>
  `),
  iconSize: [48, 48],
  iconAnchor: [24, 48],
  popupAnchor: [0, -48],
});

interface EnergySource {
  source_id: string;
  source_type: "solar";
  latitude: number;
  longitude: number;
  name: string | null;
  current_value: number | null;
  status: string;
}

interface AddSourceDialogProps {
  open: boolean;
  position: [number, number] | null;
  onClose: () => void;
  onAdd: (sourceType: "solar", name: string) => void;
}

const AddSourceDialog: React.FC<AddSourceDialogProps> = ({
  open,
  position,
  onClose,
  onAdd,
}) => {
  const [sourceType] = useState<"solar">("solar");
  const [name, setName] = useState("");

  const handleAdd = () => {
    onAdd(sourceType, name);
    setName("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Add Energy Source</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Location:{" "}
          {position
            ? `${position[0].toFixed(4)}, ${position[1].toFixed(4)}`
            : "N/A"}
        </Typography>
        <Box display="flex" alignItems="center" gap={1} sx={{ mt: 1, mb: 1 }}>
          <SolarPowerIcon style={{ color: "#FFA500" }} />
          <Typography>Solar Source</Typography>
        </Box>
        <TextField
          fullWidth
          margin="normal"
          label="Name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={`${sourceType.charAt(0).toUpperCase() + sourceType.slice(1)
            } Source`}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleAdd} variant="contained" color="primary">
          Add Source
        </Button>
      </DialogActions>
    </Dialog>
  );
};

const MapClickHandler: React.FC<{
  onMapClick: (lat: number, lng: number) => void;
}> = ({ onMapClick }) => {
  useMapEvents({
    click: (e) => {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

const MapView: React.FC = () => {
  const navigate = useNavigate();
  const [sources, setSources] = useState<EnergySource[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<
    [number, number] | null
  >(null);
  const [loading, setLoading] = useState(false);
  const [leftDrawerOpen, setLeftDrawerOpen] = useState(true);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(true);
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus>({
    last_training: null,
    is_training: false,
    last_inference: null,
    is_running_inference: false,
  });

  // Default center: Ixelles, Brussels
  const defaultCenter: [number, number] = [50.8333, 4.3667]; // Ixelles, Brussels
  const defaultZoom = 12;

  useEffect(() => {
    loadSources();
    loadTrainingStatus();
    // Refresh sources every 30 seconds to update current_value
    const interval = setInterval(() => {
      loadSources();
      loadTrainingStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSources = async () => {
    try {
      const data = await getSources();
      setSources(data);
    } catch (error) {
      console.error("Failed to load sources:", error);
    }
  };

  const loadTrainingStatus = async () => {
    try {
      const status = await getTrainingStatus();
      setTrainingStatus(status);
    } catch (error) {
      console.error("Failed to load training status:", error);
    }
  };

  const handleTraining = async () => {
    try {
      await triggerTraining();
      alert("Training started! This may take several minutes.");
      loadTrainingStatus();
    } catch (error) {
      console.error("Failed to start training:", error);
      alert("Failed to start training. Please try again.");
    }
  };

  const handleInference = async () => {
    try {
      await triggerInference();
      alert("Inference started!");
      loadTrainingStatus();
    } catch (error) {
      console.error("Failed to start inference:", error);
      alert("Failed to start inference. Please try again.");
    }
  };

  const handleGenerateSystemData = async () => {
    try {
      await generateSystemData();
      alert(
        "System data generation started! Load and market data will be available shortly.",
      );
    } catch (error) {
      console.error("Failed to generate system data:", error);
      alert("Failed to generate system data. Please try again.");
    }
  };

  const handleMapClick = (lat: number, lng: number) => {
    setSelectedPosition([lat, lng]);
    setDialogOpen(true);
  };

  const handleAddSource = async (sourceType: "solar", name: string) => {
    if (!selectedPosition) return;

    setLoading(true);
    try {
      const newSource = await createSource({
        source_type: sourceType,
        latitude: selectedPosition[0],
        longitude: selectedPosition[1],
        name: name || undefined,
      });
      setSources([...sources, newSource]);
    } catch (error) {
      console.error("Failed to add source:", error);
      alert("Failed to add energy source. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!window.confirm("Are you sure you want to delete this energy source?"))
      return;

    try {
      await deleteSource(sourceId);
      setSources(sources.filter((s) => s.source_id !== sourceId));
    } catch (error) {
      console.error("Failed to delete source:", error);
      alert("Failed to delete energy source. Please try again.");
    }
  };

  const drawerWidth = 320;
  const totalProduction = sources.reduce(
    (sum, s) => sum + (s.current_value || 0),
    0,
  );
  const solarCount = sources.filter((s) => s.source_type === "solar").length;

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Left Drawer - Sources List */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={leftDrawerOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={2}
          >
            <Typography variant="h6">Energy Sources</Typography>
            <IconButton onClick={() => setLeftDrawerOpen(false)} size="small">
              <ChevronLeftIcon />
            </IconButton>
          </Box>

          {/* Statistics Cards */}
          <Grid container spacing={2} mb={2}>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="body2" color="textSecondary">
                    Total Production
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {totalProduction.toFixed(2)} kW
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1}>
                    <SolarPowerIcon style={{ color: "#FFA500" }} />
                    <Typography variant="h5">{solarCount}</Typography>
                  </Box>
                  <Typography variant="caption" color="textSecondary">
                    Solar
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Divider sx={{ my: 2 }} />

          {/* Sources List */}
          <Typography variant="subtitle2" gutterBottom>
            Active Sources ({sources.length})
          </Typography>
          <List sx={{ maxHeight: "calc(100vh - 400px)", overflow: "auto" }}>
            {sources.map((source) => (
              <ListItem
                key={source.source_id}
                sx={{
                  border: "1px solid #e0e0e0",
                  borderRadius: 1,
                  mb: 1,
                  flexDirection: "column",
                  alignItems: "flex-start",
                }}
              >
                <Box
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                  width="100%"
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    <SolarPowerIcon style={{ color: "#FFA500" }} />
                    <Typography variant="body2" fontWeight="bold">
                      {source.name ||
                        `${source.source_type} ${source.source_id.substring(
                          0,
                          6,
                        )}`}
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteSource(source.source_id)}
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
                <Typography variant="caption" color="textSecondary">
                  {source.latitude.toFixed(4)}, {source.longitude.toFixed(4)}
                </Typography>
                {source.current_value !== null && (
                  <Typography variant="body2" color="primary" fontWeight="bold">
                    {source.current_value.toFixed(2)} kW
                  </Typography>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* Main Map Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          position: "relative",
          transition: "margin 0.3s",
          marginLeft: leftDrawerOpen ? 0 : `-${drawerWidth}px`,
          marginRight: rightDrawerOpen ? 0 : `-${drawerWidth}px`,
        }}
      >
        {/* Toggle buttons for drawers */}
        {!leftDrawerOpen && (
          <IconButton
            onClick={() => setLeftDrawerOpen(true)}
            sx={{
              position: "absolute",
              left: 16,
              top: 16,
              zIndex: 1001,
              backgroundColor: "white",
              "&:hover": { backgroundColor: "#f5f5f5" },
            }}
          >
            <ChevronRightIcon />
          </IconButton>
        )}

        {!rightDrawerOpen && (
          <IconButton
            onClick={() => setRightDrawerOpen(true)}
            sx={{
              position: "absolute",
              right: 16,
              top: 16,
              zIndex: 1001,
              backgroundColor: "white",
              "&:hover": { backgroundColor: "#f5f5f5" },
            }}
          >
            <ChevronLeftIcon />
          </IconButton>
        )}

        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          style={{ height: "100%", width: "100%" }}
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapClickHandler onMapClick={handleMapClick} />

          {sources.map((source) => (
            <React.Fragment key={source.source_id}>
              <Marker
                position={[source.latitude, source.longitude]}
                icon={solarIcon}
              >
                <Popup>
                  <Box sx={{ minWidth: 200 }}>
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      mb={1}
                    >
                      <Box display="flex" alignItems="center" gap={1}>
                        <SolarPowerIcon style={{ color: "#FFA500" }} />
                        <Typography variant="h6">
                          {source.name ||
                            `${source.source_type} ${source.source_id}`}
                        </Typography>
                      </Box>
                    </Box>

                    <Chip
                      label={source.source_type.toUpperCase()}
                      size="small"
                      color="warning"
                      sx={{ mb: 1 }}
                    />

                    <Typography variant="body2" color="textSecondary">
                      <strong>ID:</strong> {source.source_id}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      <strong>Location:</strong> {source.latitude.toFixed(4)},{" "}
                      {source.longitude.toFixed(4)}
                    </Typography>
                    {source.current_value !== null && (
                      <Typography
                        variant="body2"
                        color="primary"
                        sx={{ mt: 1 }}
                      >
                        <strong>Current Production:</strong>{" "}
                        {source.current_value.toFixed(2)} kW
                      </Typography>
                    )}
                  </Box>
                </Popup>
              </Marker>

              {/* Production visualization circle */}
              {source.current_value !== null && source.current_value > 0 && (
                <Circle
                  center={[source.latitude, source.longitude]}
                  radius={Math.sqrt(source.current_value) * 100}
                  pathOptions={{
                    color: "#FFA500",
                    fillColor: "#FFD700",
                    fillOpacity: 0.3,
                  }}
                />
              )}
            </React.Fragment>
          ))}
        </MapContainer>
      </Box>

      {/* Right Drawer - Navigation */}
      <Drawer
        variant="persistent"
        anchor="right"
        open={rightDrawerOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={2}
          >
            <Typography variant="h6">Quick Access</Typography>
            <IconButton onClick={() => setRightDrawerOpen(false)} size="small">
              <ChevronRightIcon />
            </IconButton>
          </Box>

          <Typography
            variant="caption"
            color="textSecondary"
            display="block"
            mb={2}
          >
            Click anywhere on the map to add a new energy source
          </Typography>

          <Divider sx={{ my: 2 }} />

          <List>
            <ListItemButton onClick={() => navigate("/dashboard")}>
              <ListItemIcon>
                <DashboardIcon />
              </ListItemIcon>
              <ListItemText primary="Dashboard" secondary="Manage resources" />
            </ListItemButton>

            <ListItemButton onClick={() => navigate("/grid")}>
              <ListItemIcon>
                <BatteryChargingFullIcon />
              </ListItemIcon>
              <ListItemText
                primary="Grid & Batteries"
                secondary="Control energy systems"
              />
            </ListItemButton>

            <ListItemButton onClick={() => navigate("/optimization")}>
              <ListItemIcon>
                <TuneIcon />
              </ListItemIcon>
              <ListItemText
                primary="Optimization"
                secondary="Run optimization engine"
              />
            </ListItemButton>

            <ListItemButton onClick={() => navigate("/market")}>
              <ListItemIcon>
                <ShowChartIcon />
              </ListItemIcon>
              <ListItemText primary="Market" secondary="View market prices" />
            </ListItemButton>
          </List>

          <Divider sx={{ my: 2 }} />

          {/* Forecasting Section */}
          <Paper sx={{ p: 2, mt: 2, backgroundColor: "#e3f2fd" }}>
            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
              ML Forecasting
            </Typography>

            <Box display="flex" flexDirection="column" gap={1.5} mt={1}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleTraining}
                disabled={trainingStatus.is_training}
                fullWidth
                size="small"
              >
                {trainingStatus.is_training ? "Training..." : "Train Models"}
              </Button>

              <Button
                variant="contained"
                color="secondary"
                onClick={handleInference}
                disabled={trainingStatus.is_running_inference}
                fullWidth
                size="small"
              >
                {trainingStatus.is_running_inference
                  ? "Running..."
                  : "Run Inference"}
              </Button>

              <Divider />

              <Typography variant="caption" color="textSecondary">
                <strong>Last Training:</strong>{" "}
                {trainingStatus.last_training
                  ? new Date(trainingStatus.last_training).toLocaleString()
                  : "Never"}
              </Typography>

              <Typography variant="caption" color="textSecondary">
                <strong>Last Inference:</strong>{" "}
                {trainingStatus.last_inference
                  ? new Date(trainingStatus.last_inference).toLocaleString()
                  : "Never"}
              </Typography>
            </Box>
          </Paper>

          {/* System Data Generation */}
          <Paper sx={{ p: 2, mt: 2, backgroundColor: "#fff3e0" }}>
            <Typography variant="subtitle2" gutterBottom fontWeight="bold">
              System Data
            </Typography>
            <Button
              variant="outlined"
              color="warning"
              onClick={handleGenerateSystemData}
              fullWidth
              size="small"
            >
              Generate Load & Market
            </Button>
            <Typography
              variant="caption"
              color="textSecondary"
              display="block"
              mt={1}
            >
              Starts streaming load and market price data
            </Typography>
          </Paper>

          <Divider sx={{ my: 2 }} />

          <Paper sx={{ p: 2, mt: 2, backgroundColor: "#f5f5f5" }}>
            <Typography variant="subtitle2" gutterBottom>
              System Info
            </Typography>
            <Typography variant="caption" display="block">
              Backend: Running
            </Typography>
            <Typography variant="caption" display="block">
              Kafka: Connected
            </Typography>
            <Typography variant="caption" display="block">
              Database: TimescaleDB
            </Typography>
          </Paper>
        </Box>
      </Drawer>

      <AddSourceDialog
        open={dialogOpen}
        position={selectedPosition}
        onClose={() => setDialogOpen(false)}
        onAdd={handleAddSource}
      />
    </Box>
  );
};

export default MapView;
