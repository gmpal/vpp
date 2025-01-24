
// FinancialMetrics.tsx
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';

import GridStability from './GridStability.tsx';
import CombinedDataViewer from './CombinedDataViewer.tsx';

const Grid: React.FC = () => {
    // Define all necessary states and handlers here
    const [frequency, setFrequency] = useState<number>(60);
    const [voltage, setVoltage] = useState<number>(240);
    return (
        <Box py={4}>
            <Typography variant="h5" gutterBottom>Market</Typography>
            <GridStability frequency={frequency} voltage={voltage} />
            <CombinedDataViewer
                source={'load'}
                sourceId={''}
                start={''}
                end={''}
                top={50}
            />
        </Box>
    );
}

export default Grid;