import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import Checkout from "../pages/Checkout";
import OrderSuccess from "../pages/OrderSuccess";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const USER = { id: 1, name: "Maria Santos", email: "m@example.com", phone: "09171234567", address: { line1: "1 St", city: "QC", province: "MM", region: "NCR", zip: "1100" } };
const PRODUCT = { id: 1, name: "Oil", category: "Oils & Fluids", price: 500, stock: 20, onSale: true, salePrice: 350, salePercent: 30, rating: 0, reviews: 0, imageGlyph: "oil-synthetic" };
const ORDER = { orderNumber: "ORD-1001", trackingNumber: "RC-TRK-12345", total: 700, customer: { name: "Maria Santos" } };
const RECOMMENDATION = { ...PRODUCT, id: 2, name: "Coolant", price: 200, salePrice: 150, salePercent: 25 };

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("rainchem_token", "t");
  client.get.mockImplementation((url) => {
    if (url === "/api/auth/me") return Promise.resolve({ data: { user: USER } });
    if (url === "/api/cart") return Promise.resolve({ data: { items: [{ product: PRODUCT, qty: 2 }] } });
    if (url === "/api/payments/config") return Promise.resolve({ data: { methods: { "Cash on Delivery": true }, demoMode: false } });
    return Promise.resolve({ data: {} });
  });
});

function renderCheckout() {
  return render(
    <Providers route="/checkout">
      <Routes>
        <Route path="/checkout" element={<ProtectedRoute><Checkout /></ProtectedRoute>} />
        <Route path="/order-success" element={<ProtectedRoute><OrderSuccess /></ProtectedRoute>} />
        <Route path="/pay/:id" element={<div>payment page</div>} />
      </Routes>
    </Providers>,
  );
}

describe("checkout", () => {
  it("cash on delivery lands on the order confirmation page", async () => {
    client.post.mockResolvedValue({ data: { order: ORDER, recommendations: [RECOMMENDATION] } });
    const user = userEvent.setup();
    renderCheckout();
    await user.click(await screen.findByRole("button", { name: "Place Order" }));
    expect(await screen.findByText("ORD-1001")).toBeTruthy();
    expect(screen.getByText("RC-TRK-12345")).toBeTruthy();
    expect(screen.getByText(/Total \(pay on delivery\)/)).toBeTruthy();
    expect(screen.getByText("You May Also Like")).toBeTruthy();
    expect(client.post).toHaveBeenCalledWith("/api/orders", expect.objectContaining({ paymentMethod: "Cash on Delivery" }));
  });

  it("GCash and card still continue to the payment page", async () => {
    client.post.mockResolvedValue({ data: { order: ORDER, payPath: "/pay/1" } });
    client.get.mockImplementation((url) => {
      if (url === "/api/auth/me") return Promise.resolve({ data: { user: USER } });
      if (url === "/api/cart") return Promise.resolve({ data: { items: [{ product: PRODUCT, qty: 2 }] } });
      if (url === "/api/payments/config") return Promise.resolve({ data: { methods: { "Cash on Delivery": true, GCash: true }, demoMode: false } });
      return Promise.resolve({ data: {} });
    });
    const user = userEvent.setup();
    renderCheckout();
    await user.click(await screen.findByLabelText(/GCash/));
    await user.click(screen.getByRole("button", { name: /Place Order & Pay with GCash/ }));
    expect(await screen.findByText("payment page")).toBeTruthy();
  });

  it("shows the server's message when the order cannot be placed", async () => {
    client.post.mockRejectedValue({ response: { status: 400, data: { error: "Only 1 units of Oil are available" } } });
    const user = userEvent.setup();
    renderCheckout();
    await user.click(await screen.findByRole("button", { name: "Place Order" }));
    expect(await screen.findByText(/Only 1 units of Oil/)).toBeTruthy();
    expect(screen.queryByText("ORD-1001")).toBeNull();
  });
});

describe("order confirmation page", () => {
  it("opened with no order goes back home instead of crashing", async () => {
    render(
      <Providers route="/order-success">
        <Routes><Route path="/order-success" element={<OrderSuccess />} /><Route path="/" element={<div>home</div>} /></Routes>
      </Providers>,
    );
    await waitFor(() => expect(screen.getByText("home")).toBeTruthy());
  });
});
