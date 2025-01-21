import React, { useEffect, useState } from 'react';
import { CircularProgress, Typography } from '@mui/material';
import { fetchRealTimeData, RealTimeDataPoint } from './api.ts';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';

interface RealTimeDataViewerProps {
    source: string;
    sourceId?: string;
    start?: string;
    end?: string;
}

// TODO: make sure it resets when the source changes
const RealTimeDataViewer: React.FC<RealTimeDataViewerProps> = ({
    source,
    sourceId,
}) => {

    const localISOString = (date: Date) => {
        const tzOffset = date.getTimezoneOffset() * 60000; // Offset in milliseconds
        const localTime = new Date(date.getTime() - tzOffset);
        return localTime.toISOString().slice(0, -1); // Removes the trailing 'Z'
    };

    const [data, setData] = useState<RealTimeDataPoint[]>([]);
    const [lastFetchedTime, setLastFetchedTime] = useState<string>(localISOString(new Date()));
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const newData = await fetchRealTimeData(source, sourceId, lastFetchedTime);
                if (newData.length > 0) {
                    setData(prev => [...prev, ...newData].slice(-50));
                    // Update lastFetchedTime to the timestamp of the newest data point
                    const latestTimestamp = newData[newData.length - 1].timestamp;
                    setLastFetchedTime(latestTimestamp);
                }
            } catch (error) {
                console.error('Error fetching new data', error);
                setError(error.message || 'Failed to load data.');
            } finally {
                setLoading(false);
            }
        }, 1 * 1000); // 60 seconds interval

        return () => clearInterval(interval);
    }, [source, sourceId, lastFetchedTime]);

    if (loading) {
        return <CircularProgress />;
    }

    if (error) {
        return <Typography color="error">Error: {error}</Typography>;
    }

    return (
        <div>
            <Typography variant="h6" gutterBottom>
                Real Time Data for {source}
            </Typography>
            {data && data.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                            dataKey="timestamp"
                            tickFormatter={(tick) => {
                                const date = new Date(tick);
                                const formattedTime = date.toLocaleString('it-IT', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    second: '2-digit',
                                    hour12: false, // Use 24-hour format
                                });
                                return formattedTime;
                            }}
                            tick={{ angle: +90, textAnchor: 'beginning' }}
                            padding={{ left: 20, right: 20 }}
                            height={80} // Increase the height to provide more space for rotated ticks
                        />
                        <YAxis />
                        {/* <Tooltip
                            labelFormatter={(label) => new Date(label).toLocaleString()}
                        /> */}
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

export default RealTimeDataViewer;
