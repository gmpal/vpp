
// FinancialMetrics.tsx
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';

import CombinedDataViewer from './CombinedDataViewer.tsx';

const Grid: React.FC = () => {
    // Define all necessary states and handlers here
    return (
        <Box py={4}>
            <Typography variant="h5" gutterBottom>Market</Typography>
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