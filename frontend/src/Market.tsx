
// FinancialMetrics.tsx
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';

import FinancialMetrics from './FinancialMetrics.tsx';
import CombinedDataViewer from './CombinedDataViewer.tsx';

const Market: React.FC = () => {
    // Define all necessary states and handlers here
    const [revenue, setRevenue] = useState<Array<{ month: string; amount: number }>>([{ month: 'January', amount: 10 }, { month: 'February', amount: 30 },],);
    const [costs, setCosts] = useState<Array<{ month: string; amount: number }>>([{ month: 'January', amount: 20 }, { month: 'February', amount: 50 },],);
    return (
        <Box py={4}>
            <Typography variant="h5" gutterBottom>Market</Typography>
            <FinancialMetrics revenue={revenue} costs={costs} />
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