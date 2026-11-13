import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import OnboardingGate from "../components/OnboardingGate";

const auth = { user: null, setUser: vi.fn(), logout: vi.fn() };
vi.mock("../context/AuthContext", () => ({ useAuth: () => auth }));
vi.mock("../api/client", () => ({ default: { put: vi.fn() } }));

describe("first-time account gate", () => {
  it("is shown when the account type has not been chosen", () => {
    auth.user = { name: "Juan", accountTypeChosen: false, phone: "" };
    render(<OnboardingGate />);
    expect(screen.getByRole("dialog", { name: /Tell us about your account/ })).toBeTruthy();
  });

  it("is hidden once the type is chosen", () => {
    auth.user = { name: "Juan", accountTypeChosen: true };
    const { container } = render(<OnboardingGate />);
    expect(container.innerHTML).toBe("");
  });

  it("shows the business name field only for a business", async () => {
    auth.user = { name: "Juan", accountTypeChosen: false, phone: "" };
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<OnboardingGate />);
    expect(screen.queryByLabelText("Business name")).toBeNull();
    await user.selectOptions(screen.getByLabelText("Account type"), "business");
    expect(screen.getByLabelText("Business name")).toBeTruthy();
  });
});
