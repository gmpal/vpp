import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import HouseholdPanel from "./HouseholdPanel";
import * as api from "../api";

jest.mock("../api");
const mockApi = api as jest.Mocked<typeof api>;

// Mock sub-components that have their own API calls / complexity
jest.mock("./CommunityAction", () => () => null);
jest.mock("./EVCard", () => ({ ev }: any) => (
  <div data-testid="ev-card">{ev.name}</div>
));

const sampleHousehold = {
  household_id: "hh_abc1",
  name: "My House",
  latitude: 50.85,
  longitude: 4.35,
};

const sampleVehicle = {
  vehicle_id: "ev_001",
  household_id: "hh_abc1",
  name: "Family Car",
  capacity_kwh: 75,
  soc_kwh: 37.5,
  max_charge_kw: 11,
  max_discharge_kw: 7,
  eta: 0.9,
  status: "home",
};

describe("HouseholdPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApi.getHouseholds.mockResolvedValue([]);
    mockApi.getVehicles.mockResolvedValue([]);
  });

  it("renders the Households & EVs heading", () => {
    render(<HouseholdPanel />);
    expect(screen.getByText("Households & EVs")).toBeInTheDocument();
  });

  it("shows empty state when no households", async () => {
    render(<HouseholdPanel />);
    await waitFor(() =>
      expect(
        screen.getByText("No households yet. Add one to get started."),
      ).toBeInTheDocument(),
    );
  });

  it("renders household cards when households exist", async () => {
    mockApi.getHouseholds.mockResolvedValue([sampleHousehold]);
    render(<HouseholdPanel />);
    await waitFor(() =>
      expect(screen.getByText("My House")).toBeInTheDocument(),
    );
  });

  it("renders EVCard for each vehicle in a household", async () => {
    mockApi.getHouseholds.mockResolvedValue([sampleHousehold]);
    mockApi.getVehicles.mockResolvedValue([sampleVehicle]);
    render(<HouseholdPanel />);
    await waitFor(() =>
      expect(screen.getByTestId("ev-card")).toBeInTheDocument(),
    );
    expect(screen.getByText("Family Car")).toBeInTheDocument();
  });

  it("has Add Household button", () => {
    render(<HouseholdPanel />);
    expect(screen.getByText("Add Household")).toBeInTheDocument();
  });

  it("Add EV button is disabled when no households", async () => {
    render(<HouseholdPanel />);
    await waitFor(() =>
      screen.getByText("No households yet. Add one to get started."),
    );
    const addEvBtn = screen.getByText("Add EV").closest("button");
    expect(addEvBtn).toBeDisabled();
  });

  it("Add EV button is enabled when households exist", async () => {
    mockApi.getHouseholds.mockResolvedValue([sampleHousehold]);
    render(<HouseholdPanel />);
    await waitFor(() => screen.getByText("My House"));
    const addEvBtn = screen.getByText("Add EV").closest("button");
    expect(addEvBtn).not.toBeDisabled();
  });

  it("opens Add Household dialog when button is clicked", async () => {
    render(<HouseholdPanel />);
    fireEvent.click(screen.getByText("Add Household"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText("Add Household", { selector: "h2" }),
    ).toBeInTheDocument();
  });

  it("closes Add Household dialog on Cancel", async () => {
    render(<HouseholdPanel />);
    fireEvent.click(screen.getByText("Add Household"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("calls createHousehold and refreshes on dialog submit", async () => {
    mockApi.createHousehold.mockResolvedValue({
      household_id: "hh_new1",
      name: "New House",
      latitude: 50.85,
      longitude: 4.35,
    });
    mockApi.getHouseholds.mockResolvedValueOnce([]).mockResolvedValueOnce([
      {
        household_id: "hh_new1",
        name: "New House",
        latitude: 50.85,
        longitude: 4.35,
      },
    ]);

    render(<HouseholdPanel />);
    fireEvent.click(screen.getByText("Add Household"));

    const nameInput = screen.getByLabelText(/Name/i);
    fireEvent.change(nameInput, { target: { value: "New House" } });

    fireEvent.click(screen.getByRole("button", { name: /^Add$/ }));

    await waitFor(() => expect(mockApi.createHousehold).toHaveBeenCalled());
  });

  it("calls deleteHousehold when delete button is clicked", async () => {
    mockApi.getHouseholds.mockResolvedValue([sampleHousehold]);
    mockApi.deleteHousehold.mockResolvedValue({});

    render(<HouseholdPanel />);
    await waitFor(() => screen.getByText("My House"));

    // Find the delete IconButton in the household card
    const deleteButtons = screen
      .getAllByRole("button")
      .filter(
        (btn) =>
          btn.querySelector('svg[data-testid="DeleteIcon"]') !== null ||
          btn.closest('[class*="Paper"]') !== null,
      );

    // The delete button has color="error" — it's the last button before EVCard section
    // Use a more targeted query: find all buttons and click the error-colored one
    const allButtons = screen.getAllByRole("button");
    // The delete household button should be after the Add EV button in the card
    const lastButton = allButtons[allButtons.length - 1];
    fireEvent.click(lastButton);

    await waitFor(() =>
      expect(mockApi.deleteHousehold).toHaveBeenCalledWith("hh_abc1"),
    );
  });
});
