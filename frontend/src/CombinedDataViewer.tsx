// CombinedDataViewer.tsx
import React, { useEffect, useState } from 'react';
import { fetchHistoricalData, fetchForecastedData } from './api.ts';
import { CombinedDataPoint } from './types.tsx'; // Define a type that combines both data points if necessary
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    TimeScale, // Import TimeScale
    ChartOptions,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import 'chartjs-adapter-date-fns'; // Import date-fns adapter for Chart.js
import { CircularProgress, Typography, Box } from '@mui/material';

// Register Chart.js components
ChartJS.register(
    TimeScale,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

interface CombinedDataViewerProps {
    source: string;
    sourceId?: string;
    start?: string;
    end?: string;
    top?: number;
}

interface HistoricalDataPoint {
    timestamp: string;
    value: number;
}

interface ForecastedDataPoint {
    timestamp: string;
    yhat: number;
    yhat_lower: number;
    yhat_upper: number;
}

const CombinedDataViewer: React.FC<CombinedDataViewerProps> = ({ source, sourceId, start, end, top }) => {
    const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([]);
    const [forecastedData, setForecastedData] = useState<ForecastedDataPoint[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchData() {
            try {
                setLoading(true);
                const [histData, foreData] = await Promise.all([
                    fetchHistoricalData(source, sourceId, start, end, top),
                    fetchForecastedData(source, sourceId, start, end),
                ]);
                console.log('Historical Data:', histData);
                console.log('Forecasted Data:', foreData);
                setHistoricalData(histData);
                setForecastedData(foreData);
            } catch (err) {
                console.error('Error fetching combined data:', err);
                setError('Failed to load data.');
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, [source, sourceId, start, end, top]);

    if (loading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Typography color="error" align="center">
                {error}
            </Typography>
        );
    }

    // Prepare datasets with x (timestamp) and y (value)
    const historicalDataset = {
        label: 'Historical Data',
        data: historicalData.map((d) => ({
            x: new Date(d.timestamp),
            y: d.value,
        })),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
    };

    const forecastedDataset = {
        label: 'Forecasted Data',
        data: forecastedData.map((d) => ({
            x: new Date(d.timestamp),
            y: d.yhat,
        })),
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderDash: [5, 5], // Dashed line for forecasted data
        tension: 0.4,
    };

    const data = {
        datasets: [historicalDataset, forecastedDataset],
    };

    const options: ChartOptions<'line'> = {
        responsive: true,
        plugins: {
            legend: {
                position: 'top' as const,
            },
            title: {
                display: true,
                text: 'Combined Historical and Forecasted Data',
            },
        },
        scales: {
            x: {
                type: 'time' as const, // Set x-axis to time scale
                time: {
                    unit: 'day', // Adjust based on data granularity (e.g., 'hour', 'week')
                    tooltipFormat: 'PPpp', // Tooltip date format
                    displayFormats: {
                        day: 'MMM dd', // X-axis label format
                        hour: 'MMM dd, h a',
                    },
                },
                ticks: {
                    maxRotation: 90,
                    minRotation: 45,
                },
            },
            y: {
                beginAtZero: false,
                title: {
                    display: true,
                    text: 'Value',
                },
            },
        },
    };

    return <Line options={options} data={data} />;
};

export default CombinedDataViewer;
