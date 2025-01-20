import React, { useEffect, useState } from 'react';
import { CircularProgress, Typography } from '@mui/material';
import { fetchForecastedData, ForecastedDataPoint } from './api.ts';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';

interface ForecastedDataViewerProps {
    source: string;
    sourceId?: string;
    start?: string;
    end?: string;
}

const ForecastedDataViewer: React.FC<ForecastedDataViewerProps> = ({
    source,
    sourceId,
    start,
    end,
}) => {
    const [data, setData] = useState<ForecastedDataPoint[] | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const forecastedData = await fetchForecastedData(source, sourceId, start, end);
                setData(forecastedData);
            } catch (err: any) {
                console.error('Error fetching forecasted data:', err);
                setError(err.message || 'Failed to load data.');
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [source, sourceId, start, end]);

    if (loading) {
        return <CircularProgress />;
    }

    if (error) {
        return <Typography color="error">Error: {error}</Typography>;
    }

    return (
        <div>
            <Typography variant="h6" gutterBottom>
                Forecasted Data for {source}
            </Typography>
            {data && data.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                            dataKey="timestamp"
                            tickFormatter={(tick) => new Date(tick).toLocaleDateString()}
                        />
                        <YAxis />
                        <Tooltip
                            labelFormatter={(label) => new Date(label).toLocaleString()}
                        />
                        <Line
                            type="monotone"
                            dataKey="yhat"
                            stroke="#8884d8"
                            dot={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            ) : (
                <Typography>No data available.</Typography>
            )}
        </div>
    );
};

export default ForecastedDataViewer;
