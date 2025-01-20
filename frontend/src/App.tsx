// src/App.tsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Button, Container } from '@mui/material';
import Dashboard from './Dashboard.tsx';
import Settings from './Settings.tsx';

function App() {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" component={Link} to="/">
            Dashboard
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
          <Route path="/settings" element={<Settings />} />
          {/* Define additional routes as needed */}
        </Routes>
      </Container>
    </>
  );
}

export default App;
