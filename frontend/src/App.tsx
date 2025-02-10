// src/App.tsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Button, Container } from '@mui/material';
import Dashboard from './Dashboard.tsx';
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
          <Button color="inherit" component={Link} to="/grid">
            Grid
          </Button>
          <Button color="inherit" component={Link} to="/market">
            Market
          </Button>
          <Button color="inherit" component={Link} to="/optimization">
            Optimization
          </Button>
        </Toolbar>
      </AppBar>
      <Container>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/renewables" element={<Renewables />} />
          <Route path="/grid" element={<Grid />} />
          <Route path="/market" element={<Market />} />
          <Route path="/optimization" element={<Optimization />} />

        </Routes>
      </Container>
    </>
  );
}

export default App;
