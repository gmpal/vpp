// src/App.tsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Button, Container } from '@mui/material';
import Dashboard from './Dashboard.tsx';
import Settings from './Settings.tsx';
import Batteries from './Batteries.tsx';
import Renewables from './Renewables.tsx';
import Grid from './Grid.tsx';
import Market from './Market.tsx';
import Optimization from './Optimization.tsx';

import './chartjs-config.tsx'; // Import the Chart.js configuration

function App() {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" component={Link} to="/">
            Dashboard
          </Button>
          <Button color="inherit" component={Link} to="/renewables">
            Renewables
          </Button>
          <Button color="inherit" component={Link} to="/batteries">
            Batteries
          </Button>
          <Button color="inherit" component={Link} to="/grid">
            Grid
          </Button>
          <Button color="inherit" component={Link} to="/market">
            Market
          </Button>
          <Button color="inherit" component={Link} to="/optimization">
            Optimization
          </Button>
          <Button color="inherit" component={Link} to="/settings">
            Settings
          </Button>
          {/* Add more navigation links as needed */}
        </Toolbar>
      </AppBar>
      <Container>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/renewables" element={<Renewables />} />
          <Route path="/batteries" element={<Batteries />} />
          <Route path="/grid" element={<Grid />} />
          <Route path="/market" element={<Market />} />
          <Route path="/optimization" element={<Optimization />} />

          <Route path="/settings" element={<Settings />} />
          {/* Define additional routes as needed */}
        </Routes>
      </Container>
    </>
  );
}

export default App;
