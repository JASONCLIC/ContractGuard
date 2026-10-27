import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import RiskBadge from "../RiskBadge";

describe("<RiskBadge />", () => {
  it.each([
    ["high", "High Risk"],
    ["medium", "Medium Risk"],
    ["low", "Low Risk"],
  ])("renders the human label for level=%s", (level, label) => {
    render(<RiskBadge level={level} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("falls back to the raw level string when unknown", () => {
    render(<RiskBadge level="critical" />);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("falls back to 'Unknown' when level is undefined", () => {
    render(<RiskBadge />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
