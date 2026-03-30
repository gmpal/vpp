import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import EVCard from "./EVCard";
import * as api from "../api";

jest.mock("../api");
const mockApi = api as jest.Mocked<typeof api>;

const makeEV = (overrides: Record<string, any> = {}) => ({
  vehicle_id: "ev_test1",
  household_id: "hh_1",
  name: "Test EV",
  capacity_kwh: 75,
  soc_kwh: 37.5,
  max_charge_kw: 11,
  max_discharge_kw: 7,
  eta: 0.9,
  status: "home",
  ...overrides,
});

describe("EVCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the EV name", () => {
    render(<EVCard ev={makeEV()} onRefresh={jest.fn()} />);
    expect(screen.getByText("Test EV")).toBeInTheDocument();
  });

  it("renders the status chip", () => {
    render(<EVCard ev={makeEV({ status: "home" })} onRefresh={jest.fn()} />);
    expect(screen.getByText("home")).toBeInTheDocument();
  });

  it("shows SOC percentage in text", () => {
    // soc_kwh=37.5, capacity=75 → 50%
    render(
      <EVCard
        ev={makeEV({ soc_kwh: 37.5, capacity_kwh: 75 })}
        onRefresh={jest.fn()}
      />,
    );
    expect(screen.getByText(/50%/)).toBeInTheDocument();
  });

  it("shows correct SOC text for high SOC (>70%)", () => {
    // 60/75 = 80%
    render(
      <EVCard
        ev={makeEV({ soc_kwh: 60, capacity_kwh: 75 })}
        onRefresh={jest.fn()}
      />,
    );
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });

  it("shows correct SOC text for low SOC (<30%)", () => {
    // 15/75 = 20%
    render(
      <EVCard
        ev={makeEV({ soc_kwh: 15, capacity_kwh: 75 })}
        onRefresh={jest.fn()}
      />,
    );
    expect(screen.getByText(/20%/)).toBeInTheDocument();
  });

  it("expand button reveals charge and discharge controls", () => {
    render(<EVCard ev={makeEV()} onRefresh={jest.fn()} />);
    // First button is expand/collapse toggle
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(screen.getByText(/Charge/)).toBeInTheDocument();
    expect(screen.getByText("Discharge")).toBeInTheDocument();
  });

  it("expand toggle button is present in the card", () => {
    render(<EVCard ev={makeEV()} onRefresh={jest.fn()} />);
    // There should be at least expand and delete buttons
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it("calls chargeVehicle with correct vehicle_id and calls onRefresh", async () => {
    mockApi.chargeVehicle.mockResolvedValue({
      vehicle_id: "ev_test1",
      new_soc_kwh: 50,
    });
    const onRefresh = jest.fn();
    render(<EVCard ev={makeEV()} onRefresh={onRefresh} />);

    // Expand
    fireEvent.click(screen.getAllByRole("button")[0]);

    // Click charge button
    const chargeBtn = screen.getByText(/Charge/);
    fireEvent.click(chargeBtn);

    await waitFor(() =>
      expect(mockApi.chargeVehicle).toHaveBeenCalledWith(
        "ev_test1",
        expect.any(Number),
      ),
    );
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
  });

  it("calls dischargeVehicle and onRefresh on discharge button click", async () => {
    mockApi.dischargeVehicle.mockResolvedValue({
      vehicle_id: "ev_test1",
      new_soc_kwh: 30,
    });
    const onRefresh = jest.fn();
    render(<EVCard ev={makeEV({ soc_kwh: 40 })} onRefresh={onRefresh} />);

    fireEvent.click(screen.getAllByRole("button")[0]);

    const dischargeBtn = screen.getByText("Discharge");
    fireEvent.click(dischargeBtn);

    await waitFor(() =>
      expect(mockApi.dischargeVehicle).toHaveBeenCalledWith(
        "ev_test1",
        expect.any(Number),
      ),
    );
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
  });

  it("charge button is disabled when SOC is at 100%", () => {
    // 75/75 = 100%
    render(
      <EVCard
        ev={makeEV({ soc_kwh: 75, capacity_kwh: 75 })}
        onRefresh={jest.fn()}
      />,
    );
    fireEvent.click(screen.getAllByRole("button")[0]);
    const chargeBtn = screen.getByText(/Charge/).closest("button");
    expect(chargeBtn).toBeDisabled();
  });

  it("discharge button is disabled when SOC is at 0%", () => {
    render(<EVCard ev={makeEV({ soc_kwh: 0 })} onRefresh={jest.fn()} />);
    fireEvent.click(screen.getAllByRole("button")[0]);
    const dischargeBtn = screen.getByText("Discharge").closest("button");
    expect(dischargeBtn).toBeDisabled();
  });

  it("calls deleteVehicle with vehicle_id and calls onRefresh on delete", async () => {
    mockApi.deleteVehicle.mockResolvedValue({});
    const onRefresh = jest.fn();
    render(<EVCard ev={makeEV()} onRefresh={onRefresh} />);

    // Delete button is second button
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]);

    await waitFor(() =>
      expect(mockApi.deleteVehicle).toHaveBeenCalledWith("ev_test1"),
    );
    await waitFor(() => expect(onRefresh).toHaveBeenCalled());
  });
});
