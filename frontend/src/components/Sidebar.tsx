import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Divider,
  Box,
  Typography,
  Button,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List as MuiList,
  ListItem,
  IconButton,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import { useAuth } from "../context/AuthContext";
import MapIcon from "@mui/icons-material/Map";
import BoltIcon from "@mui/icons-material/Bolt";
import HomeIcon from "@mui/icons-material/Home";
import ElectricCarIcon from "@mui/icons-material/ElectricCar";
import BarChartIcon from "@mui/icons-material/BarChart";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import DeleteIcon from "@mui/icons-material/Delete";
import ScienceIcon from "@mui/icons-material/Science";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import BuildIcon from "@mui/icons-material/Build";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import {
  initDbStream,
  resetDb,
  triggerTraining,
  triggerInference,
  InitStepStatus,
} from "../api";

const INIT_STEPS = [
  "Creating database tables",
  "Seeding load data",
  "Seeding market data",
];

type StepState = { status: "pending" | InitStepStatus; detail?: string };

function StepIcon({ status }: { status: StepState["status"] }) {
  if (status === "running") return <CircularProgress size={18} />;
  if (status === "done")
    return <CheckCircleIcon fontSize="small" sx={{ color: "success.main" }} />;
  if (status === "error")
    return <ErrorIcon fontSize="small" sx={{ color: "error.main" }} />;
  return (
    <RadioButtonUncheckedIcon
      fontSize="small"
      sx={{ color: "text.disabled" }}
    />
  );
}

const DRAWER_WIDTH = 220;

const navItems = [
  { path: "/", label: "Map", icon: <MapIcon /> },
  { path: "/community", label: "Community", icon: <BarChartIcon /> },
  { path: "/households", label: "Households", icon: <HomeIcon /> },
  { path: "/vehicles", label: "Vehicles", icon: <ElectricCarIcon /> },
  { path: "/grid", label: "Grid", icon: <BoltIcon /> },
  { path: "/profiles", label: "Profiles", icon: <ShowChartIcon /> },
  { path: "/forecast", label: "Forecast", icon: <TrendingUpIcon /> },
];

export const SIDEBAR_WIDTH = DRAWER_WIDTH;

const Sidebar: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [initializing, setInitializing] = useState(false);
  const [initSteps, setInitSteps] = useState<StepState[]>(
    INIT_STEPS.map(() => ({ status: "pending" })),
  );
  const [initDone, setInitDone] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);
  const [initDialog, setInitDialog] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [training, setTraining] = useState(false);
  const [inferring, setInferring] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  const handleInitDb = async () => {
    setInitializing(true);
    setInitDone(false);
    setInitError(null);
    setInitSteps(INIT_STEPS.map(() => ({ status: "pending" })));
    setInitDialog(true);
    try {
      await initDbStream(({ step, status, count, message }) => {
        if (step === "complete") {
          setInitDone(true);
          return;
        }
        if (step === "error") {
          setInitError(message ?? "Unknown error");
          return;
        }
        const idx = INIT_STEPS.indexOf(step);
        if (idx === -1) return;
        setInitSteps((prev) =>
          prev.map((s, i) =>
            i === idx
              ? {
                status,
                detail:
                  status === "done" && count !== undefined && count > 0
                    ? `${count} rows seeded`
                    : undefined,
              }
              : s,
          ),
        );
      });
    } catch (e: any) {
      setInitError(e?.message ?? "Request failed");
    } finally {
      setInitializing(false);
      setInitDone(true);
    }
  };

  const handleResetDb = async () => {
    setConfirmReset(false);
    setResetting(true);
    try {
      await resetDb();
    } finally {
      setResetting(false);
    }
  };

  const handleTrain = async () => {
    setTraining(true);
    try {
      await triggerTraining();
    } finally {
      setTraining(false);
    }
  };

  const handleInfer = async () => {
    setInferring(true);
    try {
      await triggerInference();
    } finally {
      setInferring(false);
    }
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
          bgcolor: "#1a1a2e",
          color: "white",
        },
      }}
    >
      <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1 }}>
        <BoltIcon sx={{ color: "#f0c040" }} />
        <Typography
          variant="h6"
          sx={{ color: "#f0c040", fontWeight: "bold", fontSize: "0.95rem" }}
        >
          VPP Manager
        </Typography>
      </Box>
      <Divider sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
      <List>
        {navItems.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <Tooltip key={item.path} title="" placement="right">
              <ListItemButton
                component={Link}
                to={item.path}
                selected={selected}
                sx={{
                  my: 0.5,
                  mx: 1,
                  borderRadius: 2,
                  color: selected ? "#f0c040" : "rgba(255,255,255,0.7)",
                  "&.Mui-selected": {
                    bgcolor: "rgba(240,192,64,0.15)",
                  },
                  "&:hover": { bgcolor: "rgba(255,255,255,0.08)" },
                }}
              >
                <ListItemIcon sx={{ color: "inherit", minWidth: 36 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: "0.875rem" }}
                />
              </ListItemButton>
            </Tooltip>
          );
        })}
      </List>

      <Box sx={{ mt: "auto" }}>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
        <Box sx={{ p: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
          <Typography
            variant="caption"
            sx={{ color: "rgba(255,255,255,0.4)", px: 0.5 }}
          >
            Actions
          </Typography>
          <Button
            size="small"
            variant="outlined"
            fullWidth
            sx={{
              color: "rgba(255,255,255,0.7)",
              borderColor: "rgba(255,255,255,0.3)",
            }}
            startIcon={
              initializing ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <BuildIcon />
              )
            }
            disabled={initializing || resetting}
            onClick={handleInitDb}
          >
            {initializing ? "Initializing…" : "Init DB"}
          </Button>

          <Dialog
            open={initDialog}
            onClose={() => {
              if (initDone || initError) setInitDialog(false);
            }}
            maxWidth="xs"
            fullWidth
          >
            <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <BuildIcon fontSize="small" />
              Initialize Database
            </DialogTitle>
            <DialogContent>
              <MuiList dense disablePadding>
                {INIT_STEPS.map((label, i) => (
                  <ListItem
                    key={label}
                    disableGutters
                    sx={{ gap: 1.5, py: 0.75 }}
                  >
                    <StepIcon status={initSteps[i].status} />
                    <Box>
                      <Typography
                        variant="body2"
                        color={
                          initSteps[i].status === "error"
                            ? "error"
                            : "text.primary"
                        }
                      >
                        {label}
                      </Typography>
                      {initSteps[i].detail && (
                        <Typography variant="caption" color="text.secondary">
                          {initSteps[i].detail}
                        </Typography>
                      )}
                    </Box>
                  </ListItem>
                ))}
              </MuiList>
              {initError && (
                <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                  {initError}
                </Typography>
              )}
              {initDone && !initError && (
                <Typography
                  variant="body2"
                  color="success.main"
                  sx={{ mt: 1, fontWeight: 500 }}
                >
                  Database initialized successfully.
                </Typography>
              )}
            </DialogContent>
            <DialogActions>
              <Button
                onClick={() => setInitDialog(false)}
                disabled={initializing}
              >
                {initDone || initError ? "Close" : "Running…"}
              </Button>
            </DialogActions>
          </Dialog>
          <Button
            size="small"
            variant="outlined"
            color="error"
            fullWidth
            startIcon={
              resetting ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <DeleteIcon />
              )
            }
            disabled={resetting || initializing}
            onClick={() => setConfirmReset(true)}
          >
            {resetting ? "Resetting…" : "Reset & Init DB"}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="primary"
            fullWidth
            startIcon={
              training ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <ScienceIcon />
              )
            }
            disabled={training}
            onClick={handleTrain}
          >
            {training ? "Training…" : "Train Model"}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="success"
            fullWidth
            startIcon={
              inferring ? (
                <CircularProgress size={14} color="inherit" />
              ) : (
                <PlayArrowIcon />
              )
            }
            disabled={inferring}
            onClick={handleInfer}
          >
            {inferring ? "Running…" : "Run Inference"}
          </Button>
        </Box>
      </Box>

      <Dialog open={confirmReset} onClose={() => setConfirmReset(false)}>
        <DialogTitle>Reset &amp; Initialize Database</DialogTitle>
        <DialogContent>
          <Typography>
            This will <b>wipe all data</b> and recreate the schema with fresh
            baseline data. Are you sure?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmReset(false)}>Cancel</Button>
          <Button color="error" onClick={handleResetDb}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {user && (
        <>
          <Divider sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
          <Box
            sx={{
              px: 1.5,
              py: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: "rgba(255,255,255,0.5)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.username}
            </Typography>
            <Tooltip title="Logout">
              <IconButton
                size="small"
                onClick={logout}
                sx={{
                  color: "rgba(255,255,255,0.5)",
                  "&:hover": { color: "#f0c040" },
                }}
              >
                <LogoutIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </>
      )}
    </Drawer>
  );
};

export default Sidebar;
