import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import TimelineBar from "./TimelineBar";

describe("TimelineBar", () => {
  it("renders with Live mode by default", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("renders the toggle switch", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    expect(screen.getByRole("checkbox")).toBeInTheDocument();
  });

  it("toggle switch is checked by default (live mode)", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    const toggle = screen.getByRole("checkbox");
    expect(toggle).toBeChecked();
  });

  it("slider is disabled in live mode", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    // MUI Slider with disabled={true} adds Mui-disabled class to the root span
    // The slider inputs are hidden; check that the root container has disabled state
    const sliderRoot = document.querySelector(".MuiSlider-root");
    expect(sliderRoot).toHaveClass("Mui-disabled");
  });

  it("calls onStateChange with isLive=false when toggle is unchecked", () => {
    const onChange = jest.fn();
    render(<TimelineBar onStateChange={onChange} />);
    const toggle = screen.getByRole("checkbox");
    fireEvent.click(toggle);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ isLive: false }),
    );
  });

  it("shows Past label after toggling to past mode", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    const toggle = screen.getByRole("checkbox");
    fireEvent.click(toggle);
    expect(screen.getByText("Past")).toBeInTheDocument();
  });

  it("shows Past chip after switching to past mode", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    expect(
      screen.queryByRole("button", { name: /h ago/i }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox"));
    // The chip with range label appears
    expect(screen.queryByText(/h –/)).toBeInTheDocument();
  });

  it("slider is enabled in past mode", () => {
    render(<TimelineBar onStateChange={jest.fn()} />);
    fireEvent.click(screen.getByRole("checkbox"));
    const sliderRoot = document.querySelector(".MuiSlider-root");
    expect(sliderRoot).not.toHaveClass("Mui-disabled");
  });

  it("calls onStateChange with startHoursAgo and endHoursAgo", () => {
    const onChange = jest.fn();
    render(<TimelineBar onStateChange={onChange} />);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        isLive: false,
        startHoursAgo: expect.any(Number),
        endHoursAgo: expect.any(Number),
      }),
    );
  });
});
