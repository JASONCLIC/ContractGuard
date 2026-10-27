import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ClauseCard from "../ClauseCard";

describe("<ClauseCard />", () => {
  it("renders heading and content", () => {
    render(
      <ClauseCard
        clause={{
          index_num: 1,
          heading: "Article 1 Term",
          content: "Contract is for 24 months.",
          category: "general",
        }}
      />
    );
    expect(screen.getByText("Article 1 Term")).toBeInTheDocument();
    expect(screen.getByText("Contract is for 24 months.")).toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();
  });

  it("falls back to 'Clause N' when heading is missing", () => {
    render(
      <ClauseCard
        clause={{ index_num: 7, content: "Body", category: "general" }}
      />
    );
    expect(screen.getByText("Clause 7")).toBeInTheDocument();
  });

  it("maps known categories to their human label", () => {
    const cases = [
      ["salary", "Salary"],
      ["work_location", "Work Location"],
      ["working_hours", "Working Hours"],
      ["probation", "Probation"],
      ["termination", "Termination"],
      ["breach", "Breach"],
      ["dispute", "Dispute"],
      ["general", "General"],
    ];
    for (const [key, label] of cases) {
      const { unmount } = render(
        <ClauseCard
          clause={{ index_num: 1, heading: `H ${key}`, content: "x", category: key }}
        />
      );
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("falls back to General label when category is unknown", () => {
    render(
      <ClauseCard
        clause={{ index_num: 1, heading: "H", content: "x", category: "no_such_cat" }}
      />
    );
    expect(screen.getByText("General")).toBeInTheDocument();
  });
});
