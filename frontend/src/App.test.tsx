import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

// Mock components that use external libraries or complex dependencies
jest.mock("./components/Map3D", () => () => (
  <div data-testid="map3d">Map View</div>
));
jest.mock("./components/CommunityDashboard", () => () => (
  <div>Community Dashboard</div>
));
jest.mock("./components/HouseholdPanel", () => () => (
  <div>Households &amp; EVs</div>
));
jest.mock("./Dashboard", () => () => (
  <div data-testid="dashboard-page">Dashboard Page</div>
));
jest.mock("./Renewables", () => () => <div>Renewables</div>);
jest.mock("./Grid", () => () => <div>Grid</div>);
jest.mock("./Market", () => () => <div>Market</div>);
jest.mock("./Optimization", () => () => <div>Optimization</div>);
jest.mock("./chartjs-config", () => {});

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

  it("renders HouseholdPanel at /vehicles", () => {
    renderAtPath("/vehicles");
    expect(screen.getByText("Households & EVs")).toBeInTheDocument();
  });

  it("renders Dashboard at /dashboard", () => {
    renderAtPath("/dashboard");
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("Sidebar nav items are present", () => {
    renderAtPath("/");
    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Community")).toBeInTheDocument();
    expect(screen.getByText("Households")).toBeInTheDocument();
  });

  it("renders the TimelineBar on all pages", () => {
    renderAtPath("/community");
    // TimelineBar has a Live toggle switch
    expect(screen.getByRole("checkbox")).toBeInTheDocument();
  });
});
