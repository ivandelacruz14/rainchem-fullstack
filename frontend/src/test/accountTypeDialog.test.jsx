import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import AccountTypeDialog from "../admin/AccountTypeDialog";

vi.mock("../api/client", () => ({ default: { put: vi.fn() } }));

describe("admin changes an account type", () => {
  it("needs a reason before it can be saved", () => {
    render(<AccountTypeDialog user={{ id: 3, name: "Juan", email: "j@example.com", accountType: "personal" }} onClose={() => {}} onSaved={() => {}} />);
    expect(screen.getByRole("button", { name: "Save" }).disabled).toBe(true);
  });

  it("asks for the business name when the type is business", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<AccountTypeDialog user={{ id: 3, name: "Juan", email: "j@example.com", accountType: "personal" }} onClose={() => {}} onSaved={() => {}} />);
    expect(screen.queryByLabelText("Business name")).toBeNull();
    await user.selectOptions(screen.getByLabelText("Account type"), "business");
    expect(screen.getByLabelText("Business name")).toBeTruthy();
  });
});
