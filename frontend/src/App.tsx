import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import Sidebar from './components/Sidebar';
import Map3D from './components/Map3D';
import Renewables from './Renewables';
import Grid from './Grid';
import Market from './Market';
import Optimization from './Optimization';
import CommunityDashboard from './components/CommunityDashboard';
import HouseholdPanel from './components/HouseholdPanel';
import VehiclePanel from './components/VehiclePanel';
import ProfilesTab from './components/ProfilesTab';
import ForecastTab from './components/ForecastTab';
import './chartjs-config';

function App() {
  const location = useLocation();
  const isMapPage = location.pathname === '/';

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          height: '100vh',
          overflow: isMapPage ? 'hidden' : 'auto',
        }}
      >
        <Routes>
          <Route path="/" element={<Map3D />} />
          <Route path="/community" element={<CommunityDashboard />} />
          <Route path="/households" element={<HouseholdPanel />} />
          <Route path="/vehicles" element={<VehiclePanel />} />
          <Route path="/renewables" element={<Renewables />} />
          <Route path="/grid" element={<Grid />} />
          <Route path="/market" element={<Market />} />
          <Route path="/optimization" element={<Optimization />} />
          <Route path="/profiles" element={<ProfilesTab />} />
          <Route path="/forecast" element={<ForecastTab />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
