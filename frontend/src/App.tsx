import React from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { Box } from "@mui/material";
import Sidebar from "./components/Sidebar";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import Map3D from "./components/Map3D";
import Grid from "./Grid";
import Market from "./Market";
import Optimization from "./Optimization";
import CommunityDashboard from "./components/CommunityDashboard";
import HouseholdPanel from "./components/HouseholdPanel";
import VehiclePanel from "./components/VehiclePanel";
import ProfilesTab from "./components/ProfilesTab";
import ForecastTab from "./components/ForecastTab";
import "./chartjs-config";

function App() {
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";
  const isMapPage = location.pathname === "/";

  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {!isLoginPage && <Sidebar />}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          height: "100vh",
          overflow: isMapPage ? "hidden" : "auto",
        }}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Map3D />
              </ProtectedRoute>
            }
          />
          <Route
            path="/community"
            element={
              <ProtectedRoute>
                <CommunityDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/households"
            element={
              <ProtectedRoute>
                <HouseholdPanel />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vehicles"
            element={
              <ProtectedRoute>
                <VehiclePanel />
              </ProtectedRoute>
            }
          />
          <Route
            path="/grid"
            element={
              <ProtectedRoute>
                <Grid />
              </ProtectedRoute>
            }
          />
          <Route
            path="/market"
            element={
              <ProtectedRoute>
                <Market />
              </ProtectedRoute>
            }
          />
          <Route
            path="/optimization"
            element={
              <ProtectedRoute>
                <Optimization />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profiles"
            element={
              <ProtectedRoute>
                <ProfilesTab />
              </ProtectedRoute>
            }
          />
          <Route
            path="/forecast"
            element={
              <ProtectedRoute>
                <ForecastTab />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;
