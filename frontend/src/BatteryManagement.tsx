// BatteryManagement.tsx
import React, { useState, useEffect } from 'react';
import {
    Paper,
    Typography,
    Box,
    CircularProgress,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Button,
    Grid,
    Snackbar,
    Alert,
    IconButton,
} from '@mui/material';
import {
    fetchAllBatteries,
    addBattery,
    removeBattery,
    chargeBattery,
    dischargeBattery,
    BatteryStatus
} from './api.ts';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';

const BatteryManagement: React.FC = () => {
    const [batteries, setBatteries] = useState<BatteryStatus[]>([]);
    const [loadingBatteries, setLoadingBatteries] = useState<boolean>(true);

    // State to manage the popup dialog visibility
    const [openBatteryDialog, setOpenBatteryDialog] = useState<boolean>(false);

    // States for battery input fields with default values
    const [capacity, setCapacity] = useState<number>(10);
    const [currentSoc, setCurrentSoc] = useState<number>(5);
    const [maxCharge, setMaxCharge] = useState<number>(2);
    const [maxDischarge, setMaxDischarge] = useState<number>(2);
    const [eta, setEta] = useState<number>(0.95);

    // State for Snackbar notifications
    const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
        open: false,
        message: '',
        severity: 'success',
    });

    // State for action dialogs (Charge/Discharge)
    const [actionDialog, setActionDialog] = useState<{
        open: boolean;
        type: 'charge' | 'discharge';
        batteryId: string;
    }>({ open: false, type: 'charge', batteryId: '' });

    // Action input states
    const [actionPower, setActionPower] = useState<number>(0);
    const [actionDuration, setActionDuration] = useState<number>(0);

    const handleOpenBatteryDialog = () => setOpenBatteryDialog(true);
    const handleCloseBatteryDialog = () => setOpenBatteryDialog(false);

    const handleOpenActionDialog = (type: 'charge' | 'discharge', batteryId: string) => {
        setActionDialog({ open: true, type, batteryId });
    };

    const handleCloseActionDialog = () => {
        setActionDialog({ open: false, type: 'charge', batteryId: '' });
        setActionPower(0);
        setActionDuration(0);
    };

    async function handleAddBatteryFromDialog() {
        try {
            const newBattery = await addBattery(capacity, currentSoc, maxCharge, maxDischarge, eta);
            setBatteries(prev => [...prev, newBattery]);
            handleCloseBatteryDialog();
            setSnackbar({ open: true, message: 'Battery added successfully!', severity: 'success' });
        } catch (error) {
            console.error('Error adding battery:', error);
            setSnackbar({ open: true, message: 'Failed to add battery.', severity: 'error' });
        }
    }

    async function handleRemoveBattery(batteryId: string) {
        try {
            // Assuming you have an API function to remove a battery
            await removeBattery(batteryId);
            setBatteries(prev => prev.filter(b => b.battery_id !== batteryId));
            setSnackbar({ open: true, message: 'Battery removed successfully!', severity: 'success' });
        } catch (error) {
            console.error('Error removing battery:', error);
            setSnackbar({ open: true, message: 'Failed to remove battery.', severity: 'error' });
        }
    }

    async function loadBatteries() {
        try {
            setLoadingBatteries(true);
            const batteryList = await fetchAllBatteries();
            setBatteries(batteryList);
        } catch (error) {
            console.error('Error fetching batteries:', error);
            setSnackbar({ open: true, message: 'Failed to fetch batteries.', severity: 'error' });
        } finally {
            setLoadingBatteries(false);
        }
    }

    useEffect(() => {
        loadBatteries();
    }, []);

    async function handleCharge(batteryId: string, power: number, duration: number) {
        try {
            const updated = await chargeBattery(batteryId, { power_kW: power, duration_h: duration });
            setBatteries(prev => prev.map(b => (b.battery_id === batteryId ? updated : b)));
            setSnackbar({ open: true, message: `Battery ${batteryId} charged successfully!`, severity: 'success' });
        } catch (error) {
            console.error(`Error charging battery ${batteryId}:`, error);
            setSnackbar({ open: true, message: `Failed to charge Battery ${batteryId}.`, severity: 'error' });
        }
    }

    async function handleDischarge(batteryId: string, power: number, duration: number) {
        try {
            const updated = await dischargeBattery(batteryId, { power_kW: power, duration_h: duration });
            setBatteries(prev => prev.map(b => (b.battery_id === batteryId ? updated : b)));
            setSnackbar({ open: true, message: `Battery ${batteryId} discharged successfully!`, severity: 'success' });
        } catch (error) {
            console.error(`Error discharging battery ${batteryId}:`, error);
            setSnackbar({ open: true, message: `Failed to discharge Battery ${batteryId}.`, severity: 'error' });
        }
    }

    // Calculate total number of batteries
    const totalBatteries = batteries.length;

    return (
        <Box my={4}>
            <Typography variant="h2" component="h1" gutterBottom align="center">
                Battery Management
            </Typography>

            {/* Total Batteries */}
            <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
                <Typography variant="h5" align="center">
                    Total Batteries: {totalBatteries}
                </Typography>
            </Paper>

            {/* Battery Input Dialog */}
            <Dialog open={openBatteryDialog} onClose={handleCloseBatteryDialog}>
                <DialogTitle>Add New Battery</DialogTitle>
                <DialogContent>
                    <TextField
                        margin="dense"
                        label="Capacity (kWh)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={capacity}
                        onChange={e => setCapacity(parseFloat(e.target.value))}
                        inputProps={{ min: 0 }}
                    />
                    <TextField
                        margin="dense"
                        label="Current SOC (kWh)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={currentSoc}
                        onChange={e => setCurrentSoc(parseFloat(e.target.value))}
                        inputProps={{ min: 0, max: capacity }}
                    />
                    <TextField
                        margin="dense"
                        label="Max Charge (kW)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={maxCharge}
                        onChange={e => setMaxCharge(parseFloat(e.target.value))}
                        inputProps={{ min: 0 }}
                    />
                    <TextField
                        margin="dense"
                        label="Max Discharge (kW)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={maxDischarge}
                        onChange={e => setMaxDischarge(parseFloat(e.target.value))}
                        inputProps={{ min: 0 }}
                    />
                    <TextField
                        margin="dense"
                        label="Efficiency (η)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={eta}
                        onChange={e => setEta(parseFloat(e.target.value))}
                        inputProps={{ min: 0, max: 1, step: 0.01 }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseBatteryDialog}>Cancel</Button>
                    <Button onClick={handleAddBatteryFromDialog} variant="contained" color="primary">
                        Add Battery
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Add Battery Button */}
            <Paper elevation={3} sx={{ p: 2, mb: 2 }}>
                <Box display="flex" justifyContent="center">
                    <Button
                        variant="outlined"
                        startIcon={<AddIcon />}
                        onClick={handleOpenBatteryDialog}
                    >
                        Add New Battery
                    </Button>
                </Box>
            </Paper>

            {/* Battery List */}
            {loadingBatteries ? (
                <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
                    <CircularProgress />
                </Box>
            ) : (
                <Grid container spacing={2}>
                    {batteries.map(battery => (
                        <Grid item xs={12} md={6} key={battery.battery_id}>
                            <Paper elevation={3} sx={{ p: 2 }}>
                                <Typography variant="h6">Battery ID: {battery.battery_id}</Typography>
                                <Typography>Capacity: {battery.capacity_kWh} kWh</Typography>
                                <Typography>State of Charge: {battery.soc_kWh} kWh</Typography>
                                <Typography>Max Charge Rate: {battery.max_charge_kW} kW</Typography>
                                <Typography>Max Discharge Rate: {battery.maxDischarge_kW} kW</Typography>
                                <Typography>Efficiency (η): {battery.eta}</Typography>
                                <Box mt={2} display="flex" gap={2}>
                                    <Button
                                        variant="contained"
                                        color="success"
                                        onClick={() => handleOpenActionDialog('charge', battery.battery_id)}
                                    >
                                        Charge
                                    </Button>
                                    <Button
                                        variant="contained"
                                        color="error"
                                        onClick={() => handleOpenActionDialog('discharge', battery.battery_id)}
                                    >
                                        Discharge
                                    </Button>
                                    <Button
                                        variant="outlined"
                                        color="error"
                                        onClick={() => handleRemoveBattery(battery.battery_id)}
                                    >
                                        Remove
                                    </Button>

                                </Box>
                            </Paper>
                        </Grid>
                    ))}
                </Grid>
            )}

            {/* Action Dialog (Charge/Discharge) */}
            <Dialog open={actionDialog.open} onClose={handleCloseActionDialog}>
                <DialogTitle>
                    {actionDialog.type === 'charge' ? 'Charge Battery' : 'Discharge Battery'}
                </DialogTitle>
                <DialogContent>
                    <TextField
                        margin="dense"
                        label="Power (kW)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={actionPower}
                        onChange={e => setActionPower(parseFloat(e.target.value))}
                        inputProps={{ min: 0 }}
                    />
                    <TextField
                        margin="dense"
                        label="Duration (hours)"
                        type="number"
                        fullWidth
                        variant="outlined"
                        value={actionDuration}
                        onChange={e => setActionDuration(parseFloat(e.target.value))}
                        inputProps={{ min: 0 }}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={handleCloseActionDialog}>Cancel</Button>
                    <Button
                        onClick={() => {
                            if (actionDialog.type === 'charge') {
                                handleCharge(actionDialog.batteryId, actionPower, actionDuration);
                            } else {
                                handleDischarge(actionDialog.batteryId, actionPower, actionDuration);
                            }
                            handleCloseActionDialog();
                        }}
                        variant="contained"
                        color={actionDialog.type === 'charge' ? 'success' : 'error'}
                    >
                        {actionDialog.type === 'charge' ? 'Charge' : 'Discharge'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Snackbar for Notifications */}
            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert
                    onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
                    severity={snackbar.severity}
                    sx={{ width: '100%' }}
                >
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
};

export default BatteryManagement;
