import React from 'react';
import {
    Container,
} from '@mui/material';

import BatteryManagement from './BatteryManagement.tsx';



const Batteries: React.FC = () => {

    return (

        <Container maxWidth="lg" sx={{ py: 4 }}>
            {/* Battery Management */}
            <BatteryManagement />

        </Container >
    );
};

export default Batteries;
