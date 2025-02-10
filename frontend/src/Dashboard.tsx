// Dashboard.tsx
import React, { useEffect, useState } from 'react';
import {
    fetchDeviceCounts,
    DeviceCounts,
    addNewSource,
} from './api.ts';

import BatteryManagement from './BatteryManagement.tsx';

import {
    Container,
    Typography,
    Paper,
    Grid,
    Box,
    CircularProgress,
    FormControl,
    Button,
    Snackbar,
    Alert,
} from '@mui/material';

const Dashboard: React.FC = () => {

    const [sourceIDs, setSourceIDs] = useState<string[]>([]);
    const [deviceCounts, setDeviceCounts] = useState<DeviceCounts | null>(null);
    const [addingSource, setAddingSource] = useState<boolean>(false); // Loading state
    const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

    useEffect(() => {
        async function fetchInitialDeviceCounts() {
            try {
                const counts = await fetchDeviceCounts();
                console.log('Fetched device counts:', counts);
                setDeviceCounts(counts);
            } catch (error) {
                console.error('Error fetching device counts:', error);
                setSnackbar({ open: true, message: 'Failed to fetch device counts.', severity: 'error' });
            }
        }
        fetchInitialDeviceCounts();
    }, []); // Runs once on mount

    const handleAddSource = async (type: 'solar' | 'wind') => {
        try {
            setAddingSource(true);
            const newSource = await addNewSource(type);
            console.log(`New ${type} source added:`, newSource);
            setSourceIDs(prev => [...prev, newSource.source_id]);

            // Update device counts locally
            setDeviceCounts(prevCounts => {
                if (!prevCounts) return prevCounts; // Handle null state
                return {
                    ...prevCounts,
                    [type]: prevCounts[type] + 1,
                };
            });

            setSnackbar({ open: true, message: `${type.charAt(0).toUpperCase() + type.slice(1)} source added successfully!`, severity: 'success' });
        } catch (error) {
            console.error(`Error adding ${type} source:`, error);
            setSnackbar({ open: true, message: `Failed to add ${type} source.`, severity: 'error' });
        } finally {
            setAddingSource(false);
        }
    };

    return (

        <Container maxWidth="lg" sx={{ py: 4 }}>

            {/* Devices Box */}
            <Box my={4}>
                <Typography variant="h2" component="h1" gutterBottom align="center">
                    Devices
                </Typography>

                {/* Status Widgets */}
                <Grid container spacing={2}>
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

                    {/* Add Source Buttons */}
                    <Grid item xs={12}>
                        <Paper elevation={3} sx={{ p: 2 }}>
                            <FormControl fullWidth>
                                <Box display="flex" justifyContent="center" gap={2}>
                                    <Button
                                        variant="contained"
                                        color="primary"
                                        onClick={() => handleAddSource('solar')}
                                        disabled={addingSource}
                                    >
                                        {addingSource ? 'Adding Solar...' : 'Add Solar'}
                                    </Button>
                                    <Button
                                        variant="contained"
                                        color="secondary"
                                        onClick={() => handleAddSource('wind')}
                                        disabled={addingSource}
                                    >
                                        {addingSource ? 'Adding Wind...' : 'Add Wind'}
                                    </Button>
                                </Box>
                            </FormControl>
                        </Paper>
                    </Grid>
                </Grid>
                <Container maxWidth="lg" sx={{ py: 4 }}>
                    {/* Battery Management */}
                    <BatteryManagement />

                </Container >
            </Box>

            {/* Snackbar for Notifications */}
            <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}>
                <Alert onClose={() => setSnackbar(prev => ({ ...prev, open: false }))} severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>

        </Container>
    );
};

export default Dashboard;
