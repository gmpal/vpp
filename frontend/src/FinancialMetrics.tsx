// FinancialMetrics.tsx
import React, { useState } from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { ChartOptions } from 'chart.js';
import { Bar } from 'react-chartjs-2';


interface MarketProps {
    revenue: Array<{ month: string; amount: number }>;
    costs: Array<{ month: string; amount: number }>;
}

const FinancialMetrics: React.FC<MarketProps> = ({ revenue, costs }) => {
    const labels = revenue.map(r => r.month);

    const data = {
        labels,
        datasets: [
            {
                label: 'Revenue ($)',
                data: revenue.map(r => r.amount),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
            },
            {
                label: 'Costs ($)',
                data: costs.map(c => c.amount),
                backgroundColor: 'rgba(255, 99, 132, 0.6)',
            },
        ],
    };

    const options: ChartOptions<'bar'> = {
        responsive: true,
        plugins: {
            legend: { position: 'top' },
            title: { display: true, text: 'Financial Performance' },
        },
        scales: {
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Amount ($)' },
            },
        },
    };

    return (
        <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
                Financial Metrics
            </Typography>
            <Bar data={data} options={options} />
        </Paper>
    );
};

export default FinancialMetrics;

