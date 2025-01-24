// GridStability.tsx
import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

interface GridStabilityProps {
    frequency: number; // in Hz
    voltage: number;   // in V
}

const GridStability: React.FC<GridStabilityProps> = ({ frequency, voltage }) => {
    // Placeholder for Gauge implementation
    return (
        <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
                Grid Stability Metrics
            </Typography>
            <Box display="flex" justifyContent="space-around">
                <Box textAlign="center">
                    <Typography variant="subtitle1">Frequency (Hz)</Typography>
                    <Typography variant="h4" color={frequency < 59.9 || frequency > 60.1 ? 'error' : 'primary'}>
                        {frequency} Hz
                    </Typography>
                </Box>
                <Box textAlign="center">
                    <Typography variant="subtitle1">Voltage (V)</Typography>
                    <Typography variant="h4" color={voltage < 230 || voltage > 240 ? 'error' : 'primary'}>
                        {voltage} V
                    </Typography>
                </Box>
            </Box>
        </Paper>
    );
};

export default GridStability;