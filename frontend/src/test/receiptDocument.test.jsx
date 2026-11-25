import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ReceiptDocument from "../components/ReceiptDocument";

vi.mock("jsbarcode", () => ({ default: vi.fn() }));

const receipt = {
  orderNumber: "ORD-20261125-0001", barcodeValue: "ORD-20261125-0001", deliveryStage: "awaiting_receipt",
  orderDate: "2026-11-25T02:00:00Z", deliveryDate: null, rider: "Robert",
  customer: { name: "Juan Dela Cruz", phone: "09171234567", address: "123 Sampaguita St, Quezon City" },
  items: [{ productId: 1, name: "Rainchem Engine Oil", sku: "RCH-001", quantity: 2, unitPrice: 350, discountRate: 0, discount: 0, subtotal: 700 }],
  subtotal: 700, discount: 0, shippingFee: 80, total: 780, upload: null,
  payment: { method: "Cash on Delivery", status: "unpaid", isPrepaid: false, isPaid: false, codAmountToCollect: 780 },
};

describe("delivery receipt", () => {
  it("shows the stored order values and the cash to collect", () => {
    render(<ReceiptDocument receipt={receipt} />);
    expect(screen.getByText("ORD-20261125-0001")).toBeTruthy();
    expect(screen.getByText("Juan Dela Cruz")).toBeTruthy();
    expect(screen.getByText("RCH-001")).toBeTruthy();
    expect(screen.getByText(/Amount to collect from customer/)).toBeTruthy();
  });

  it("says nothing is to collect for a prepaid order", () => {
    render(<ReceiptDocument receipt={{ ...receipt, payment: { ...receipt.payment, method: "GCash", isPrepaid: true, isPaid: true, codAmountToCollect: 0 } }} />);
    expect(screen.getByText("Paid in advance")).toBeTruthy();
  });
});
