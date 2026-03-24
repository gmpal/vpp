import React, { useEffect, useState, useCallback } from 'react';
import { Box, Typography, Grid, Paper, Alert } from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { fetchHistoricalData, fetchSourceIDs, HistoricalDataPoint } from '../api';

interface ChartData {
  time: string;
  value: number;
}

const toChartData = (points: HistoricalDataPoint[]): ChartData[] =>
  points.map(p => ({
    time: new Date(p.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    value: p.value,
  }));

interface ProfileChartProps {
  title: string;
  data: ChartData[];
  stroke: string;
  unit?: string;
}

const ProfileChart: React.FC<ProfileChartProps> = ({ title, data, stroke, unit = '' }) => (
  <Paper sx={{ p: 2, borderRadius: 2, borderTop: `3px solid ${stroke}` }}>
    <Typography variant="subtitle2" gutterBottom fontWeight="bold">
      {title}
    </Typography>
    {data.length === 0 ? (
      <Box sx={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Typography variant="body2" color="text.secondary">No data</Typography>
      </Box>
    ) : (
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="time" tick={{ fontSize: 10 }} />
          <YAxis unit={unit} tick={{ fontSize: 10 }} width={55} />
          <Tooltip formatter={(v: number) => [`${v.toFixed(3)}${unit}`, title]} />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            stroke={stroke}
            name={title}
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    )}
  </Paper>
);

const ProfilesTab: React.FC = () => {
  const [solarData, setSolarData] = useState<ChartData[]>([]);
  const [loadData, setLoadData] = useState<ChartData[]>([]);
  const [marketData, setMarketData] = useState<ChartData[]>([]);
  const [error, setError] = useState('');

  const loadAll = useCallback(async () => {
    try {
      const solarIds = await fetchSourceIDs('solar');

      const firstSolarId = solarIds.length > 0 ? solarIds[0] : undefined;

      const [solar, load, market] = await Promise.all([
        fetchHistoricalData('solar', firstSolarId, undefined, undefined, 100),
        fetchHistoricalData('load', undefined, undefined, undefined, 100),
        fetchHistoricalData('market', undefined, undefined, undefined, 100),
      ]);

      setSolarData(toChartData(solar));
      setLoadData(toChartData(load));
      setMarketData(toChartData(market));
      setError('');
    } catch (e) {
      setError('Could not load profile data. Ensure the backend is running and data has been initialized.');
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 30000);
    return () => clearInterval(interval);
  }, [loadAll]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight="bold" mb={2}>
        Energy Profiles
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <ProfileChart
            title="Solar Production"
            data={solarData}
            stroke="#f0c040"
            unit=" kW"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ProfileChart
            title="Load"
            data={loadData}
            stroke="#ef5350"
            unit=" kW"
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <ProfileChart
            title="Market Price"
            data={marketData}
            stroke="#4caf50"
            unit=" €/MWh"
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProfilesTab;
