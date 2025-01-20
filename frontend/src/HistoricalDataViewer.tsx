import React, { useEffect, useState } from 'react';
import { CircularProgress, Typography } from '@mui/material';
import { fetchHistoricalData, HistoricalDataPoint } from './api.ts';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';

interface HistoricalDataViewerProps {
    source: string;
    sourceId?: string;
    start?: string;
    end?: string;
}

const HistoricalDataViewer: React.FC<HistoricalDataViewerProps> = ({
    source,
    sourceId,
    start,
    end,
}) => {
    const [data, setData] = useState<HistoricalDataPoint[] | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                const historicalData = await fetchHistoricalData(source, sourceId, start, end);
                setData(historicalData);
            } catch (err: any) {
                console.error('Error fetching historical data:', err);
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
                Historical Data for {source}
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
                            dataKey="value"
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

export default HistoricalDataViewer;
