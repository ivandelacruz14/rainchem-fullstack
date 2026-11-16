import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const unitOf = (c) => c.querySelector(".confirm-unit-price").textContent;
const subtotalOf = (c) => c.querySelector(".confirm-subtotal strong").textContent;
import userEvent from "@testing-library/user-event";
import OrderConfirmModal from "../components/OrderConfirmModal";

vi.mock("../api/client", () => ({ default: { get: vi.fn(() => Promise.resolve({ data: { addresses: [] } })) } }));

const product = { id: 1, name: "RAIMOL FLASH 4T", price: 249, stock: 3, salePercent: 0 };

describe("confirm add to cart", () => {
  it("shows the unit price and the subtotal, and updates the subtotal when the quantity changes", async () => {
    const user = userEvent.setup();
    const { container } = render(<OrderConfirmModal product={product} initialQty={1} mode="cart" onCancel={() => {}} onConfirm={() => {}} />);
    expect(unitOf(container)).toContain("249");
    expect(subtotalOf(container)).toContain("249");
    await user.click(screen.getByRole("button", { name: "Increase" }));
    expect(subtotalOf(container)).toContain("498");
  });

  it("does not go above the stock", async () => {
    const user = userEvent.setup();
    const { container } = render(<OrderConfirmModal product={product} initialQty={1} mode="cart" onCancel={() => {}} onConfirm={() => {}} />);
    for (let i = 0; i < 6; i++) await user.click(screen.getByRole("button", { name: "Increase" }));
    expect(subtotalOf(container)).toContain("747");   // 3 units x 249
  });

  it("Confirm sends the chosen quantity, and Cancel sends nothing", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<OrderConfirmModal product={product} initialQty={2} mode="cart" onCancel={onCancel} onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm).toHaveBeenCalledWith(2);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
  });

  it("Buy Now asks for the payment step before it continues", () => {
    render(<OrderConfirmModal product={product} initialQty={1} mode="buy" onCancel={() => {}} onConfirm={() => {}} />);
    expect(screen.getByText(/Cash on Delivery or GCash/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Confirm and continue" })).toBeTruthy();
  });
});
