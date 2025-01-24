// Dashboard.tsx
import React, { useEffect, useState } from 'react';
import {
    fetchSourceIDs,
    DeviceCounts,
} from './api.ts';
import { DateRange } from '@mui/x-date-pickers-pro/DateRangePicker';

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
import CombinedDataViewer from './CombinedDataViewer.tsx';
import TimeRangeSelector from './TimeRangeSelector.tsx';

function safeToISOString(date: any): string | undefined {
    if (!date) return undefined; // Check for null/undefined
    const d = new Date(date);
    return isNaN(d.getTime()) ? undefined : d.toISOString();
}

const Renewables: React.FC = () => {
    const [selectedSource, setSelectedSource] = useState<string>('solar');
    const [selectedSourceID, setSelectedSourceID] = useState<string>('3');
    const [selectedRange, setSelectedRange] = useState<DateRange<Date>>([null, null]);

    const [sourceIDs, setSourceIDs] = useState<string[]>([]);
    const [selectedTopN, setSelectedTopN] = useState<number>(50);

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
    }, [selectedSource, selectedSourceID]);


    return (

        <Container maxWidth="lg" sx={{ py: 4 }}>

            {/* Combined  and ing Data Plot */}
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Combined  and Forecasted Data
                </Typography>

                <Grid item xs={12}>
                    <Paper elevation={3} sx={{ p: 2 }}>
                        <FormControl fullWidth>
                            <InputLabel id="source-forecast-select-label">Select Source</InputLabel>
                            <Select
                                labelId="source-forecast-select-label"
                                id="source-forecast-select"
                                value={selectedSource}
                                label="Select  Source"
                                onChange={(e) => setSelectedSource(e.target.value as string)}
                            >
                                <MenuItem value="solar">Solar</MenuItem>
                                <MenuItem value="wind">Wind</MenuItem>
                                <MenuItem value="load">Load</MenuItem>
                            </Select>
                        </FormControl>
                    </Paper>
                </Grid>

                {/* ing Source ID Selection Menu */}
                {
                    selectedSource !== 'market' && selectedSource !== 'load' && (
                        <Grid item xs={12}>
                            <Paper elevation={3} sx={{ p: 2 }}>
                                <FormControl fullWidth>
                                    <InputLabel id="source-id-forecast-select-label">Select Source ID</InputLabel>
                                    <Select
                                        labelId="source-id-forecast-select-label"
                                        id="source-id-forecast-select"
                                        value={selectedSourceID}
                                        label="Select Source ID "
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

                {/* TOP N SELECTION INPUT BOX */}
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
                    <CombinedDataViewer
                        source={selectedSource}
                        sourceId={selectedSourceID}
                        start={safeToISOString(selectedRange[0])}
                        end={safeToISOString(selectedRange[1])}
                        top={selectedTopN}
                    />
                </Paper>
            </Box >

        </Container >
    );

};

export default Renewables;
