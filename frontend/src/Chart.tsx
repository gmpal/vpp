// src/Chart.tsx
import React from 'react';
import { RealTimeData } from './api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Box, Typography } from '@mui/material';

interface ChartProps {
    data: RealTimeData[];
}

const Chart: React.FC<ChartProps> = ({ data }) => {
    return (
        <Box>
            <Typography variant="subtitle1" gutterBottom>Real-Time Chart</Typography>
            <ResponsiveContainer width="100%" height={300}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="generation" stroke="#8884d8" />
                    <Line type="monotone" dataKey="consumption" stroke="#82ca9d" />
                    {/* Add more lines as needed */}
                </LineChart>
            </ResponsiveContainer>
        </Box>
    );
};

export default Chart;