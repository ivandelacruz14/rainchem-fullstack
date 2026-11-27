import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import StickerDocument from "../components/StickerDocument";

vi.mock("jsbarcode", () => ({ default: vi.fn() }));

const base = {
  orderNumber: "ORD-20261125-0007", barcodeValue: "ORD-20261125-0007", itemCount: 2,
  customer: { name: "Maria Santos", phone: "09171234567", address: "12 Rizal St, Quezon City" },
  orderDate: "2026-11-25T02:24:00", total: 780,
  items: [{ productId: 1, name: "Engine Oil 1L", sku: "RCH-001", quantity: 2, unitPrice: 390, subtotal: 780 }],
};

describe("package sticker", () => {
  it("shows the cash to collect for a cash-on-delivery order", () => {
    render(<StickerDocument sticker={{ ...base, payment: { method: "Cash on Delivery", isPaid: false, codAmountToCollect: 780 } }} />);
    expect(screen.getByText(/COD to be collected/)).toBeTruthy();
    expect(screen.getAllByText("ORD-20261125-0007").length).toBeGreaterThan(0);
    expect(screen.getByText("Maria Santos")).toBeTruthy();
  });

  it("shows PAID and no cash for a prepaid order", () => {
    render(<StickerDocument sticker={{ ...base, payment: { method: "GCash", isPaid: true, codAmountToCollect: 0 } }} />);
    expect(screen.getAllByText("PAID").length).toBeGreaterThan(0);
    expect(screen.queryByText(/to be collected/)).toBeNull();
  });

  it("lists the items like the delivery receipt and the total", () => {
    render(<StickerDocument sticker={{ ...base, payment: { method: "Cash on Delivery", isPaid: false, codAmountToCollect: 780 } }} />);
    expect(screen.getByText("Engine Oil 1L")).toBeTruthy();
    expect(screen.getByText("RCH-001")).toBeTruthy();
    expect(screen.getByText("TOTAL AMOUNT")).toBeTruthy();
    expect(screen.getByText("COD")).toBeTruthy();
  });
});
