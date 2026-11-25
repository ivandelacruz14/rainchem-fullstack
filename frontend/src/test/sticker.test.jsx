import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import StickerDocument from "../components/StickerDocument";

vi.mock("jsbarcode", () => ({ default: vi.fn() }));

const base = {
  orderNumber: "ORD-20261125-0007", barcodeValue: "ORD-20261125-0007", itemCount: 2,
  customer: { name: "Maria Santos", phone: "09171234567", address: "12 Rizal St, Quezon City" },
};

describe("package sticker", () => {
  it("shows the cash to collect for a cash-on-delivery order", () => {
    render(<StickerDocument sticker={{ ...base, payment: { method: "Cash on Delivery", isPaid: false, codAmountToCollect: 780 } }} />);
    expect(screen.getByText(/COLLECT/)).toBeTruthy();
    expect(screen.getByText("ORD-20261125-0007")).toBeTruthy();
    expect(screen.getByText("Maria Santos")).toBeTruthy();
  });

  it("shows PAID and no cash for a prepaid order", () => {
    render(<StickerDocument sticker={{ ...base, payment: { method: "GCash", isPaid: true, codAmountToCollect: 0 } }} />);
    expect(screen.getByText("PAID")).toBeTruthy();
    expect(screen.queryByText(/COLLECT/)).toBeNull();
  });
});
