import React, { useEffect, useState } from 'react';
import { fetchSourceIDs, fetchDeviceCounts, DeviceCounts } from './api.ts';
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
import RealTimeDataViewer from './RealTimeDataViewer.tsx';

function safeToISOString(date: any): string | undefined {
    if (!date) return undefined; // Check for null/undefined
    const d = new Date(date);
    return isNaN(d.getTime()) ? undefined : d.toISOString();
}

const Dashboard: React.FC = () => {
    const [selectedSourceHistorical, setSelectedSourceHistorical] = useState<string>('solar');
    const [selectedSourceIDHistorical, setSelectedSourceIDHistorical] = useState<string>('3');
    const [selectedRangeHistorical, setSelectedRangeHistorical] = useState<DateRange<Date>>([null, null]);

    const [selectedSourceForecast, setSelectedSourceForecast] = useState<string>('solar');
    const [selectedSourceIDForecast, setSelectedSourceIDForecast] = useState<string>('3');
    const [selectedRangeForecast, setSelectedRangeForecast] = useState<DateRange<Date>>([null, null]);

    const [selectedSourceRealTime, setSelectedSourceRealTime] = useState<string>('solar');
    const [selectedSourceIDRealTime, setSelectedSourceIDRealTime] = useState<string>('3');
    const [selectedRangeRealTime, setSelectedRangeRealTime] = useState<DateRange<Date>>([null, null]);


    const [sourceIDs, setSourceIDs] = useState<string[]>([]);
    const [deviceCounts, setDeviceCounts] = useState<DeviceCounts | null>(null);


    useEffect(() => {
        async function updateSourceIDs() {
            if (selectedSourceHistorical === 'market' || selectedSourceHistorical === 'load') {
                setSourceIDs([]);      // Clear IDs since not applicable
                setSelectedSourceIDHistorical(''); // Reset source ID
                return;
            }
            try {
                const ids = await fetchSourceIDs(selectedSourceHistorical);
                setSourceIDs(ids);
                // Optionally reset selectedSourceID if current one is not in new list
                if (!ids.includes(selectedSourceIDHistorical)) {
                    setSelectedSourceIDHistorical(ids[0] || '');  // select first if available
                }
            } catch (error) {
                console.error('Error fetching source IDs:', error);
            }
        }

        updateSourceIDs();
    }, [selectedSourceHistorical, selectedSourceIDHistorical]);


    useEffect(() => {
        async function updateDeviceCounts() {
            try {
                const counts = await fetchDeviceCounts();
                setDeviceCounts(counts);
            } catch (error) {
                console.error('Error fetching device counts:', error);
            }
        }
        updateDeviceCounts();
    }, []);


    // if (!realTimeData) {
    //     return (
    //         <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
    //             <CircularProgress />
    //         </Box>
    //     );
    // }

    return (

        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Typography variant="h1" component="h1" gutterBottom align="center">
                Virtual Power Plant Dashboard
            </Typography>

            {/* Real-Time Box */}
            <Box my={4}>
                {/* Real-Time Title */}
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Real-Time Data Plot
                </Typography>


                {/* Real-Time Data Source Selection Menu */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="source-select-label">Select Source Real Time</InputLabel>
                            <Select
                                labelId="source-real-time-select-label"
                                id="source-real-time-select"
                                value={selectedSourceRealTime}
                                label="Select Realtime Source"
                                onChange={(e) => setSelectedSourceRealTime(e.target.value as string)}
                            >
                                <MenuItem value="solar">Solar</MenuItem>
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                                <MenuItem value="market">Market</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* Real-Time Source ID Selection Menu */}
                {
                    selectedSourceRealTime !== 'market' && selectedSourceRealTime !== 'load' && (
                        <Grid item xs={12}>
                            <Paper elevation={3} sx={{ p: 2 }}>
                                <FormControl fullWidth>
                                    <InputLabel id="source-id-realtime-select-label">Select Source ID</InputLabel>
                                    <Select
                                        labelId="source-id-realtime-select-label"
                                        id="source-id-realtime-select"
                                        value={selectedSourceIDRealTime}
                                        label="Select Source Real Time ID"
                                        onChange={(e) => setSelectedSourceIDRealTime(e.target.value as string)}
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

                {/* Real-Time  Time Range Selector */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <TimeRangeSelector value={selectedRangeRealTime} onChange={setSelectedRangeRealTime} />
                    </Paper>
                </Grid>



                {/* Real-Time Data Viewer Section */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <RealTimeDataViewer
                            source={selectedSourceRealTime}
                            sourceId={selectedSourceIDRealTime}
                            start={safeToISOString(selectedRangeRealTime[0])}
                            end={safeToISOString(selectedRangeRealTime[1])}
                        />
                    </Paper>
                </Grid>
            </Box>

            {/* Devices Box */}
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Devices
                </Typography>

                {/* Status Widgets */}
                <Grid item xs={12} md={6}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <Typography variant="h6">Solar Devices</Typography>
                        <Typography variant="h4">
                            {deviceCounts ? deviceCounts.solar : <CircularProgress size={24} />}
                        </Typography>
                    </Paper>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <Typography variant="h6">Wind Devices</Typography>
                        <Typography variant="h4">
                            {deviceCounts ? deviceCounts.wind : <CircularProgress size={24} />}
                        </Typography>
                    </Paper>
                </Grid>

            </Box>

            {/* Historical Data Box */}
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Historical Data
                </Typography>
                {/* Historical Data Source Selection Menu */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="source-select-label">Select Source</InputLabel>
                            <Select
                                labelId="source-select-label"
                                id="source-select"
                                value={selectedSourceHistorical}
                                label="Select Source"
                                onChange={(e) => setSelectedSourceHistorical(e.target.value as string)}
                            >
                                <MenuItem value="solar">Solar</MenuItem>
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                                <MenuItem value="market">Market</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* Historical Data Source ID Selection Menu */}
                {
                    selectedSourceHistorical !== 'market' && selectedSourceHistorical !== 'load' && (
                        <Grid item xs={12}>
                            <Paper elevation={3} sx={{ p: 2 }}>
                                <FormControl fullWidth>
                                    <InputLabel id="source-id-historical-select-label">Select Source ID</InputLabel>
                                    <Select
                                        labelId="source-id-historical-select-label"
                                        id="source-id-historical-select"
                                        value={selectedSourceIDHistorical}
                                        label="Select Source ID Historical"
                                        onChange={(e) => setSelectedSourceIDHistorical(e.target.value as string)}
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

                {/* Historical Data Time Range Selector */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <TimeRangeSelector value={selectedRangeHistorical} onChange={setSelectedRangeHistorical} />
                    </Paper>
                </Grid>



                {/* Historical Data Viewer Section */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <HistoricalDataViewer
                            source={selectedSourceHistorical}
                            sourceId={selectedSourceIDHistorical}
                            start={safeToISOString(selectedRangeHistorical[0])}
                            end={safeToISOString(selectedRangeHistorical[1])}
                        />
                    </Paper>
                </Grid>
            </Box>

            {/* Forecasting Box */}
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Forecasting
                </Typography>


                {/* Forecasting Source Selection Menu */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="source-forecast-select-label">Select Source</InputLabel>
                            <Select
                                labelId="source-forecast-select-label"
                                id="source-forecast-select"
                                value={selectedSourceHistorical}
                                label="Select Forecast Source"
                                onChange={(e) => setSelectedSourceForecast(e.target.value as string)}
                            >
                                <MenuItem value="solar">Solar</MenuItem>
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                                <MenuItem value="market">Market</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* Forecasting Source ID Selection Menu */}
                {
                    selectedSourceForecast !== 'market' && selectedSourceForecast !== 'load' && (
                        <Grid item xs={12}>
                            <Paper elevation={3} sx={{ p: 2 }}>
                                <FormControl fullWidth>
                                    <InputLabel id="source-id-forecast-select-label">Select Source ID</InputLabel>
                                    <Select
                                        labelId="source-id-forecast-select-label"
                                        id="source-id-forecast-select"
                                        value={selectedSourceIDForecast}
                                        label="Select Source ID Forecast"
                                        onChange={(e) => setSelectedSourceIDForecast(e.target.value as string)}
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

                {/* Forecasting Time Range Selector */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <TimeRangeSelector value={selectedRangeForecast} onChange={setSelectedRangeForecast} />
                    </Paper>
                </Grid>



                {/* Forecasting Data Viewer Section */}
                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <ForecastedDataViewer
                            source={selectedSourceForecast}
                            sourceId={selectedSourceIDForecast}
                            start={safeToISOString(selectedRangeForecast[0])}
                            end={safeToISOString(selectedRangeForecast[1])}
                        />
                    </Paper>
                </Grid>
            </Box >
        </Container >
    );
};

export default Dashboard;
