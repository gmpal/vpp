import React, { useEffect, useState } from 'react';
import { fetchSourceIDs, fetchHistoricalData, HistoricalDataPoint } from './api.ts';
import {
    Container,
    Typography,
    Paper,
    Box,
    Grid,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

function formatTimestamp(timestamp: string): string {
    const d = new Date(timestamp);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const mo = String(d.getMonth() + 1).padStart(2, '0');
    return `${hh}:${mm} ${dd}/${mo}`;
}

const SOURCE_COLORS: Record<string, string> = {
    solar: '#f0c040',
    load: '#ef5350',
};

const Renewables: React.FC = () => {
    const [selectedSource, setSelectedSource] = useState<string>('solar');
    const [selectedSourceID, setSelectedSourceID] = useState<string>('');
    const [sourceIDs, setSourceIDs] = useState<string[]>([]);
    const [selectedTopN, setSelectedTopN] = useState<number>(50);
    const [chartData, setChartData] = useState<{ time: string; value: number }[]>([]);

    useEffect(() => {
        async function updateSourceIDs() {
            if (selectedSource === 'market' || selectedSource === 'load') {
                setSourceIDs([]);
                setSelectedSourceID('');
                return;
            }
            try {
                const ids = await fetchSourceIDs(selectedSource);
                setSourceIDs(ids);
                if (!ids.includes(selectedSourceID)) {
                    setSelectedSourceID(ids[0] || '');
                }
            } catch (error) {
                console.error('Error fetching source IDs:', error);
            }
        }
        updateSourceIDs();
    }, [selectedSource]);

    useEffect(() => {
        async function loadHistorical() {
            try {
                const sourceId = selectedSource === 'solar'
                    ? selectedSourceID
                    : undefined;
                if (selectedSource === 'solar' && !sourceId) {
                    setChartData([]);
                    return;
                }
                const data: HistoricalDataPoint[] = await fetchHistoricalData(
                    selectedSource,
                    sourceId,
                    undefined,
                    undefined,
                    selectedTopN
                );
                setChartData(data.map(p => ({
                    time: formatTimestamp(p.timestamp),
                    value: p.value,
                })));
            } catch (err) {
                console.error('Error fetching historical data:', err);
                setChartData([]);
            }
        }
        loadHistorical();
    }, [selectedSource, selectedSourceID, selectedTopN]);

    const lineColor = SOURCE_COLORS[selectedSource] ?? '#8884d8';

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Renewables
                </Typography>

                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="source-select-label">Select Source</InputLabel>
                            <Select
                                labelId="source-select-label"
                                id="source-select"
                                value={selectedSource}
                                label="Select Source"
                                onChange={(e) => setSelectedSource(e.target.value as string)}
                            >
                                <MenuItem value="solar">Solar</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {selectedSource !== 'market' && selectedSource !== 'load' && (
                    <Grid item xs={12}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <FormControl fullWidth>
                                <InputLabel id="source-id-select-label">Select Source ID</InputLabel>
                                <Select
                                    labelId="source-id-select-label"
                                    id="source-id-select"
                                    value={selectedSourceID}
                                    label="Select Source ID"
                                    onChange={(e) => setSelectedSourceID(e.target.value as string)}
                                >
                                    {sourceIDs.map((id) => (
                                        <MenuItem key={id} value={id}>{id}</MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        </Paper>
                    </Grid>
                )}

                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="top-n-select-label">Select Top N</InputLabel>
                            <Select
                                labelId="top-n-select-label"
                                id="top-n-select"
                                value={selectedTopN}
                                label="Select Top N"
                                onChange={(e) => setSelectedTopN(e.target.value as number)}
                            >
                                {[50, 100, 150, 200].map((n) => (
                                    <MenuItem key={n} value={n}>{n}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                <Paper elevation={3} sx={{ p: 2 }}>
                    {chartData.length === 0 ? (
                        <Typography color="text.secondary" align="center" py={4}>No data</Typography>
                    ) : (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                <XAxis
                                    dataKey="time"
                                    tick={{ fontSize: 9, angle: -30, textAnchor: 'end' }}
                                    height={50}
                                />
                                <YAxis tick={{ fontSize: 10 }} />
                                <Tooltip />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="value"
                                    stroke={lineColor}
                                    name={selectedSource.charAt(0).toUpperCase() + selectedSource.slice(1)}
                                    dot={false}
                                    strokeWidth={2}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    )}
                </Paper>
            </Box>
        </Container>
    );
};

export default Renewables;
