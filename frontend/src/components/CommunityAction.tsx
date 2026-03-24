import React, { useEffect, useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import BoltIcon from '@mui/icons-material/Bolt';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import ElectricCarIcon from '@mui/icons-material/ElectricCar';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { getCommunitySummary } from '../api';

const ACTION_CONFIG: Record<string, { icon: React.ReactNode; color: string; getMessage: (s: any) => string }> = {
  selling: {
    icon: <TrendingUpIcon sx={{ fontSize: 48 }} />,
    color: '#4caf50',
    getMessage: (s) => `Selling ${s.net.toFixed(2)} kW to the grid`,
  },
  buying: {
    icon: <TrendingDownIcon sx={{ fontSize: 48 }} />,
    color: '#ff9800',
    getMessage: (s) => `Buying ${Math.abs(s.net).toFixed(2)} kW — consider charging your EVs`,
  },
  charging_evs: {
    icon: <ElectricCarIcon sx={{ fontSize: 48 }} />,
    color: '#2196f3',
    getMessage: (s) => `Charging EVs with ${s.net.toFixed(2)} kW surplus`,
  },
  self_sufficient: {
    icon: <CheckCircleIcon sx={{ fontSize: 48 }} />,
    color: '#9c27b0',
    getMessage: () => 'Self-sufficient — production matches consumption',
  },
};

const CommunityAction: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    const fetch = async () => {
      try { setSummary(await getCommunitySummary()); } catch {}
    };
    fetch();
    const id = setInterval(fetch, 5000);
    return () => clearInterval(id);
  }, []);

  if (!summary) return null;
  const config = ACTION_CONFIG[summary.action] ?? ACTION_CONFIG.self_sufficient;

  return (
    <Paper sx={{
      p: 3, borderRadius: 3,
      border: `2px solid ${config.color}`,
      bgcolor: config.color + '11',
      display: 'flex', alignItems: 'center', gap: 2,
    }}>
      <Box sx={{ color: config.color }}>{config.icon}</Box>
      <Box>
        <Typography variant="overline" color="text.secondary">Currently</Typography>
        <Typography variant="h6" fontWeight="bold" color={config.color}>
          {config.getMessage(summary)}
        </Typography>
      </Box>
    </Paper>
  );
};

export default CommunityAction;
