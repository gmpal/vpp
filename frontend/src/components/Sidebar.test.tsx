import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Sidebar from "./Sidebar";

const renderSidebar = (initialPath = "/") =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar />
    </MemoryRouter>,
  );

describe("Sidebar", () => {
  it("renders VPP Manager title", () => {
    renderSidebar();
    expect(screen.getByText("VPP Manager")).toBeInTheDocument();
  });

  it("renders all 7 nav items", () => {
    renderSidebar();
    expect(screen.getByText("Map")).toBeInTheDocument();
    expect(screen.getByText("Community")).toBeInTheDocument();
    expect(screen.getByText("Households")).toBeInTheDocument();
    expect(screen.getByText("Vehicles")).toBeInTheDocument();
    expect(screen.getByText("Renewables")).toBeInTheDocument();
    expect(screen.getByText("Grid")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("marks the active item as selected when on / route", () => {
    renderSidebar("/");
    // MUI ListItemButton with component={Link} renders as <a> → role="link"
    const mapLinks = screen
      .getAllByRole("link")
      .filter((link) => link.textContent?.includes("Map"));
    expect(mapLinks.length).toBeGreaterThan(0);
    expect(mapLinks[0]).toHaveClass("Mui-selected");
  });

  it("marks Community as selected when on /community route", () => {
    renderSidebar("/community");
    const communityLinks = screen
      .getAllByRole("link")
      .filter((link) => link.textContent?.includes("Community"));
    expect(communityLinks.length).toBeGreaterThan(0);
    expect(communityLinks[0]).toHaveClass("Mui-selected");
  });

  it("does not mark non-active items as selected", () => {
    renderSidebar("/community");
    const mapLinks = screen
      .getAllByRole("link")
      .filter((link) => link.textContent?.trim() === "Map");
    if (mapLinks.length > 0) {
      expect(mapLinks[0]).not.toHaveClass("Mui-selected");
    }
  });

  it("nav items are links to correct paths", () => {
    renderSidebar();
    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/community");
    expect(hrefs).toContain("/households");
    expect(hrefs).toContain("/vehicles");
    expect(hrefs).toContain("/renewables");
    expect(hrefs).toContain("/grid");
    expect(hrefs).toContain("/dashboard");
  });
});
