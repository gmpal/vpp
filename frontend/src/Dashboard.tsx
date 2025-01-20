import React, { useEffect, useState } from 'react';
import { fetchRealTimeData, RealTimeData, fetchSourceIDs } from './api.ts';
import Chart from './Chart.tsx';
import { DateRange } from '@mui/x-date-pickers-pro/DateRangePicker';
import TimeRangeSelector from './TimeRangeSelector.tsx';

import {
    Container,
    Typography,
    Paper,
    Grid,
    Box,
    CircularProgress,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
} from '@mui/material';
import HistoricalDataViewer from './HistoricalDataViewer.tsx';
import ForecastedDataViewer from './ForecastedDataViewer.tsx';

function safeToISOString(date: any): string | undefined {
    if (!date) return undefined; // Check for null/undefined
    const d = new Date(date);
    return isNaN(d.getTime()) ? undefined : d.toISOString();
}

const Dashboard: React.FC = () => {
    const [data, setData] = useState<RealTimeData | null>(null);
    const [dataHistory, setDataHistory] = useState<RealTimeData[]>([]);
    const [selectedSource, setSelectedSource] = useState<string>('solar');
    const [selectedSourceID, setSelectedSourceID] = useState<string>('');
    const [selectedRange, setSelectedRange] = useState<DateRange<Date>>([null, null]);
    const [sourceIDs, setSourceIDs] = useState<string[]>([]);

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const newData = await fetchRealTimeData();
                setData(newData);
                setDataHistory(prevHistory => {
                    // Append newData with a timestamp if needed, or use the data as-is
                    const updatedHistory = [...prevHistory, newData];
                    // Limit history to last 50 entries
                    return updatedHistory.length > 50 ? updatedHistory.slice(-50) : updatedHistory;
                });
            } catch (error) {
                console.error('Error fetching data', error);
            }
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        async function updateSourceIDs() {
            if (selectedSource === 'market' || selectedSource === 'load') {
                setSourceIDs([]);      // Clear IDs since not applicable
                setSelectedSourceID(''); // Reset source ID
                return;
            }
            try {
                const ids = await fetchSourceIDs(selectedSource);
                setSourceIDs(ids);
                // Optionally reset selectedSourceID if current one is not in new list
                if (!ids.includes(selectedSourceID)) {
                    setSelectedSourceID(ids[0] || '');  // select first if available
                }
            } catch (error) {
                console.error('Error fetching source IDs:', error);
            }
        }

        updateSourceIDs();
    }, [selectedSource]);

    if (!data) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
                <CircularProgress />
            </Box>
        );
    }

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h4" component="h1" gutterBottom align="center">
                Virtual Power Plant Dashboard
            </Typography>
            <Grid container spacing={3}>

                {/* Source Selection Menu */}
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
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                                <MenuItem value="market">Market</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* Source ID Selection Menu */}
                {
                    selectedSource !== 'market' && selectedSource !== 'load' && (
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
                    )
                }

                {/* Time Range Selector */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <TimeRangeSelector value={selectedRange} onChange={setSelectedRange} />
                    </Paper>
                </Grid>



                {/* Historical Data Viewer Section */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <HistoricalDataViewer
                            source={selectedSource}
                            sourceId={selectedSourceID}
                            start={safeToISOString(selectedRange[0])}
                            end={safeToISOString(selectedRange[1])}
                        />
                    </Paper>
                </Grid>
            </Grid >

            <Typography variant="h4" component="h1" gutterBottom align="center">
                Forecasting
            </Typography>
            <Grid container spacing={3}>

                {/* Source Selection Menu */}
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
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                                <MenuItem value="market">Market</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* Source ID Selection Menu */}
                {
                    selectedSource !== 'market' && selectedSource !== 'load' && (
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
                    )
                }

                {/* Time Range Selector */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <TimeRangeSelector value={selectedRange} onChange={setSelectedRange} />
                    </Paper>
                </Grid>



                {/* Historical Data Viewer Section */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <ForecastedDataViewer
                            source={selectedSource}
                            sourceId={selectedSourceID}
                            start={safeToISOString(selectedRange[0])}
                            end={safeToISOString(selectedRange[1])}
                        />
                    </Paper>
                </Grid>
            </Grid >
        </Container >
    );
};

export default Dashboard;
