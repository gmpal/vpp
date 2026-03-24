import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Tooltip, Divider, Box, Typography,
  Button, CircularProgress, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import MapIcon from '@mui/icons-material/Map';
import BoltIcon from '@mui/icons-material/Bolt';
import HomeIcon from '@mui/icons-material/Home';
import ElectricCarIcon from '@mui/icons-material/ElectricCar';
import BarChartIcon from '@mui/icons-material/BarChart';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import ShowChartIcon from '@mui/icons-material/ShowChart';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import DeleteIcon from '@mui/icons-material/Delete';
import ScienceIcon from '@mui/icons-material/Science';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BuildIcon from '@mui/icons-material/Build';
import { initDb, resetDb, triggerTraining, triggerInference } from '../api';

const DRAWER_WIDTH = 220;

const navItems = [
  { path: '/', label: 'Map', icon: <MapIcon /> },
  { path: '/community', label: 'Community', icon: <BarChartIcon /> },
  { path: '/households', label: 'Households', icon: <HomeIcon /> },
  { path: '/vehicles', label: 'Vehicles', icon: <ElectricCarIcon /> },
  { path: '/renewables', label: 'Renewables', icon: <WbSunnyIcon /> },
  { path: '/grid', label: 'Grid', icon: <BoltIcon /> },
  { path: '/profiles', label: 'Profiles', icon: <ShowChartIcon /> },
  { path: '/forecast', label: 'Forecast', icon: <TrendingUpIcon /> },
];

export const SIDEBAR_WIDTH = DRAWER_WIDTH;

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [initializing, setInitializing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [training, setTraining] = useState(false);
  const [inferring, setInferring] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  const handleInitDb = async () => {
    setInitializing(true);
    try {
      await initDb();
    } finally {
      setInitializing(false);
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
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: '#1a1a2e',
          color: 'white',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <BoltIcon sx={{ color: '#f0c040' }} />
        <Typography variant="h6" sx={{ color: '#f0c040', fontWeight: 'bold', fontSize: '0.95rem' }}>
          VPP Manager
        </Typography>
      </Box>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
      <List>
        {navItems.map(item => {
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
                  color: selected ? '#f0c040' : 'rgba(255,255,255,0.7)',
                  '&.Mui-selected': {
                    bgcolor: 'rgba(240,192,64,0.15)',
                  },
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.08)' },
                }}
              >
                <ListItemIcon sx={{ color: 'inherit', minWidth: 36 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: '0.875rem' }} />
              </ListItemButton>
            </Tooltip>
          );
        })}
      </List>

      <Box sx={{ mt: 'auto' }}>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />
        <Box sx={{ p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', px: 0.5 }}>
            Actions
          </Typography>
          <Button
            size="small"
            variant="outlined"
            fullWidth
            sx={{ color: 'rgba(255,255,255,0.7)', borderColor: 'rgba(255,255,255,0.3)' }}
            startIcon={initializing ? <CircularProgress size={14} color="inherit" /> : <BuildIcon />}
            disabled={initializing || resetting}
            onClick={handleInitDb}
          >
            {initializing ? 'Initializing…' : 'Init DB'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="error"
            fullWidth
            startIcon={resetting ? <CircularProgress size={14} color="inherit" /> : <DeleteIcon />}
            disabled={resetting || initializing}
            onClick={() => setConfirmReset(true)}
          >
            {resetting ? 'Resetting…' : 'Reset & Init DB'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="primary"
            fullWidth
            startIcon={training ? <CircularProgress size={14} color="inherit" /> : <ScienceIcon />}
            disabled={training}
            onClick={handleTrain}
          >
            {training ? 'Training…' : 'Train Model'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="success"
            fullWidth
            startIcon={inferring ? <CircularProgress size={14} color="inherit" /> : <PlayArrowIcon />}
            disabled={inferring}
            onClick={handleInfer}
          >
            {inferring ? 'Running…' : 'Run Inference'}
          </Button>
        </Box>
      </Box>

      <Dialog open={confirmReset} onClose={() => setConfirmReset(false)}>
        <DialogTitle>Reset &amp; Initialize Database</DialogTitle>
        <DialogContent>
          <Typography>This will <b>wipe all data</b> and recreate the schema with fresh baseline data. Are you sure?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmReset(false)}>Cancel</Button>
          <Button color="error" onClick={handleResetDb}>Confirm</Button>
        </DialogActions>
      </Dialog>
    </Drawer>
  );
};

export default Sidebar;
