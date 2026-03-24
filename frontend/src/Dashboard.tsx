// Dashboard.tsx
import React, { useEffect, useState } from 'react';
import {
    fetchDeviceCounts,
    DeviceCounts,
} from './api.ts';

import BatteryManagement from './BatteryManagement.tsx';

import {
    Container,
    Typography,
    Paper,
    Grid,
    Box,
    CircularProgress,
    Snackbar,
    Alert,
} from '@mui/material';

const Dashboard: React.FC = () => {

    const [deviceCounts, setDeviceCounts] = useState<DeviceCounts | null>(null);
    const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

    useEffect(() => {
        async function fetchInitialDeviceCounts() {
            try {
                const counts = await fetchDeviceCounts();
                setDeviceCounts(counts);
            } catch (error) {
                console.error('Error fetching device counts:', error);
                setSnackbar({ open: true, message: 'Failed to fetch device counts.', severity: 'error' });
            }
        }
        fetchInitialDeviceCounts();
    }, []); // Runs once on mount


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
