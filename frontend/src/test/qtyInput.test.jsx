import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QtyInput from "../components/QtyInput";

describe("quantity you can type", () => {
  it("sends the typed number of pieces when Enter is pressed", async () => {
    const onCommit = vi.fn();
    const user = userEvent.setup();
    render(<QtyInput value={1} onCommit={onCommit} max={500} />);
    const input = screen.getByLabelText("Quantity");
    await user.clear(input);
    await user.type(input, "20{Enter}");
    expect(onCommit).toHaveBeenCalledWith(20);
  });

  it("converts boxes to pieces when the unit is boxes", async () => {
    const onCommit = vi.fn();
    const user = userEvent.setup();
    render(<QtyInput value={24} onCommit={onCommit} max={10000} packSize={24} />);
    await user.selectOptions(screen.getByLabelText("Unit"), "boxes");
    const input = screen.getByLabelText("Quantity");
    await user.clear(input);
    await user.type(input, "3");
    await user.tab();
    expect(onCommit).toHaveBeenCalledWith(72);
  });

  it("keeps the amount within the stock", async () => {
    const onCommit = vi.fn();
    const user = userEvent.setup();
    render(<QtyInput value={1} onCommit={onCommit} max={50} />);
    const input = screen.getByLabelText("Quantity");
    await user.clear(input);
    await user.type(input, "100{Enter}");
    expect(onCommit).toHaveBeenCalledWith(50);
    expect(input.value).toBe("50");
  });

  it("ignores text that is not a number and restores the last value", async () => {
    const onCommit = vi.fn();
    const user = userEvent.setup();
    render(<QtyInput value={5} onCommit={onCommit} max={50} />);
    const input = screen.getByLabelText("Quantity");
    await user.clear(input);
    await user.type(input, "abc");
    await user.tab();
    expect(onCommit).not.toHaveBeenCalled();
    expect(input.value).toBe("5");
  });

  it("hides the unit choice when the product has no pack size", () => {
    render(<QtyInput value={2} onCommit={() => {}} max={9} />);
    expect(screen.queryByLabelText("Unit")).toBeNull();
  });
});
