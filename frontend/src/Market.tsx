
// FinancialMetrics.tsx
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';

import CombinedDataViewer from './CombinedDataViewer.tsx';

const Market: React.FC = () => {
    return (
        <Box py={4}>
            <Typography variant="h5" gutterBottom>Market</Typography>
            <CombinedDataViewer
                source={'market'}
                sourceId={''}
                start={''}
                end={''}
                top={50}
            />
        </Box>
    );
}

export default Market;