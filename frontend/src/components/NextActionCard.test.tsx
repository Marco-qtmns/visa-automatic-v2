import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { NextActionCard } from "./NextActionCard";

it("renders recommendation, action, description, then navigation", () => {
  render(<NextActionCard action={{
    type: "continue", title: "Review the imported passport information",
    case_id: "case-1", fact_id: null, fact_key: null, requirement_id: null,
    task_id: null, document_id: null, fact_candidate_id: null,
    target_state: "DOCUMENTS",
  }} />);
  const recommendation = screen.getByText("Backend recommendation");
  const heading = screen.getByRole("heading", { name: "Next action" });
  const description = screen.getByText("Review the imported passport information");
  const link = screen.getByRole("link", { name: "Open relevant section" });
  expect(recommendation.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(heading.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(description.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});
