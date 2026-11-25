import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorBox from "../components/ErrorBox";

function Broken() {
  throw new Error("boom in receipt");
}

describe("ErrorBox", () => {
  it("shows a clear message instead of a blank area when a child fails", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<ErrorBox><Broken /></ErrorBox>);
    expect(screen.getByRole("alert").textContent).toContain("This part could not be displayed");
    expect(screen.getByRole("alert").textContent).toContain("boom in receipt");
  });

  it("renders its children when nothing fails", () => {
    render(<ErrorBox><p>Receipt content</p></ErrorBox>);
    expect(screen.getByText("Receipt content")).toBeTruthy();
  });
});
