import React from "react";
import { render, screen, waitFor, act } from "@testing-library/react";
import CommunityDashboard from "./CommunityDashboard";
import * as api from "../api";

jest.mock("../api");
const mockApi = api as jest.Mocked<typeof api>;

// Mock Recharts to avoid canvas/ResizeObserver issues in jsdom
jest.mock("recharts", () => {
  const React = require("react");
  return {
    LineChart: ({ children }: any) => (
      <div data-testid="line-chart">{children}</div>
    ),
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const mockSummary = {
  total_production: 10.0,
  total_consumption: 8.0,
  net: 2.0,
  ev_soc_total: 50.0,
  ev_soc_capacity: 100.0,
  action: "selling",
  household_count: 3,
  ev_count: 2,
};

describe("CommunityDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  it("renders Community Dashboard heading", async () => {
    mockApi.getCommunitySummary.mockImplementation(() => new Promise(() => {}));
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(screen.getByText("Community Dashboard")).toBeInTheDocument();
    });
  });

  it("shows stat card titles before data loads", async () => {
    mockApi.getCommunitySummary.mockImplementation(() => new Promise(() => {}));
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(screen.getByText("Total Production")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Consumption")).toBeInTheDocument();
    expect(screen.getByText("Households")).toBeInTheDocument();
    expect(screen.getByText("EVs")).toBeInTheDocument();
  });

  it("shows production and consumption values after data loads", async () => {
    mockApi.getCommunitySummary.mockResolvedValue(mockSummary);
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(screen.getByText("10.00 kW")).toBeInTheDocument();
    });
    expect(screen.getByText("8.00 kW")).toBeInTheDocument();
  });

  it("shows household count and ev count", async () => {
    mockApi.getCommunitySummary.mockResolvedValue(mockSummary);
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows EV SOC bar when ev_count > 0", async () => {
    mockApi.getCommunitySummary.mockResolvedValue(mockSummary);
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(screen.getByText("Fleet EV State of Charge")).toBeInTheDocument();
    });
  });

  it("hides EV SOC bar when ev_count === 0", async () => {
    mockApi.getCommunitySummary.mockResolvedValue({
      ...mockSummary,
      ev_count: 0,
    });
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      screen.getByText("10.00 kW");
    });
    expect(
      screen.queryByText("Fleet EV State of Charge"),
    ).not.toBeInTheDocument();
  });

  it("renders live power chart", async () => {
    mockApi.getCommunitySummary.mockResolvedValue(mockSummary);
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(
        screen.getByText("Live Power (last 30 readings)"),
      ).toBeInTheDocument();
    });
  });

  it("shows error alert when fetch fails", async () => {
    mockApi.getCommunitySummary.mockRejectedValue(new Error("network error"));
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(
        screen.getByText("Could not load community data"),
      ).toBeInTheDocument();
    });
  });

  it("polls getCommunitySummary on interval", async () => {
    jest.useFakeTimers();
    mockApi.getCommunitySummary.mockResolvedValue(mockSummary);
    await act(async () => {
      render(<CommunityDashboard />);
    });
    await waitFor(() => {
      expect(mockApi.getCommunitySummary).toHaveBeenCalledTimes(1);
    });
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    await waitFor(() => {
      expect(mockApi.getCommunitySummary).toHaveBeenCalledTimes(2);
    });
    jest.useRealTimers();
  });
});
