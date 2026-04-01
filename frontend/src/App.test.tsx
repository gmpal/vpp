import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock components that use external libraries or complex dependencies
jest.mock("./components/Map3D", () => () => (
  <div data-testid="map3d">Map View</div>
));
jest.mock("./components/ProtectedRoute", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("./context/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    logout: jest.fn(),
  }),
}));
jest.mock("./components/CommunityDashboard", () => () => (
  <div>Community Dashboard</div>
));
jest.mock("./components/HouseholdPanel", () => () => (
  <div>Households &amp; EVs</div>
));
jest.mock("./components/VehiclePanel", () => () => <div>Vehicles</div>);
jest.mock("./Grid", () => () => <div>Grid</div>);
jest.mock("./Market", () => () => <div>Market</div>);
jest.mock("./Optimization", () => () => <div>Optimization</div>);
jest.mock("./components/ProfilesTab", () => () => <div>Profiles</div>);
jest.mock("./components/ForecastTab", () => () => <div>Forecast Viewer</div>);
jest.mock("./chartjs-config", () => { });

// App.tsx uses useLocation internally, so we wrap it in a MemoryRouter
// but App itself does NOT provide a Router — the real index.tsx does.
import App from "./App";

const renderAtPath = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );

describe("App routing", () => {
  it("renders the Sidebar on every route", () => {
    renderAtPath("/");
    expect(screen.getByText("VPP Manager")).toBeInTheDocument();
  });

  it("renders Map3D component at root path /", () => {
    renderAtPath("/");
    expect(screen.getByTestId("map3d")).toBeInTheDocument();
  });

  it("renders CommunityDashboard at /community", () => {
    renderAtPath("/community");
    expect(screen.getByText("Community Dashboard")).toBeInTheDocument();
  });

  it("renders HouseholdPanel at /households", () => {
    renderAtPath("/households");
    expect(screen.getByText("Households & EVs")).toBeInTheDocument();
  });

  it("renders VehiclePanel at /vehicles", () => {
    renderAtPath("/vehicles");
    expect(screen.getAllByText("Vehicles").length).toBeGreaterThan(0);
  });

  it("Sidebar nav items are present", () => {
    renderAtPath("/");
    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Community")).toBeInTheDocument();
    expect(screen.getByText("Households")).toBeInTheDocument();
    expect(screen.getByText("Vehicles")).toBeInTheDocument();
    expect(screen.getByText("Grid")).toBeInTheDocument();
    expect(screen.getByText("Profiles")).toBeInTheDocument();
    expect(screen.getByText("Forecast")).toBeInTheDocument();
  });

  it("renders Grid at /grid", () => {
    renderAtPath("/grid");
    expect(screen.getAllByText("Grid").length).toBeGreaterThan(0);
  });

  it("renders Forecast at /forecast", () => {
    renderAtPath("/forecast");
    expect(screen.getByText("Forecast Viewer")).toBeInTheDocument();
  });
});
