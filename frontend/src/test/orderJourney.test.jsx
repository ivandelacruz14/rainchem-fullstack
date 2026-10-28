import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccountTrack from "../pages/account/AccountTrack";
import OrderJourney from "../components/journey/OrderJourney";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const TITLES = ["Order Received", "Order Verification", "Order Approved", "Preparing Your Products", "In Transit", "Delivered"];

function journey(states, extra = {}) {
  return {
    state: "in_progress", headline: "Order Approved", stageNumber: 3, stageCount: 6, updatedAt: "2026-10-25T08:30:00", alerts: [],
    milestones: TITLES.map((title, i) => ({
      key: ["received", "verification", "approved", "preparing", "in_transit", "delivered"][i], title, state: states[i],
      description: `${title} text`, at: states[i] === "upcoming" ? null : "2026-10-25T08:00:00",
    })),
    ...extra,
  };
}

function order(j, patch = {}) {
  return {
    id: 9, orderNumber: "ORD-2026-0009", trackingNumber: "RC-TRK-90009", status: "confirmed", journey: j,
    items: [{ id: 1, name: "RAIMOL Oil 1L", quantity: 2, lineTotal: 700 }], total: 700,
    customer: { name: "Maria Santos", phone: "09171234567" },
    address: { line1: "1 Rider St", city: "Quezon City", province: "Metro Manila", region: "NCR", zip: "1100" },
    paymentMethod: "Cash on Delivery", paymentStatusLabel: "Unpaid", ...patch,
  };
}

describe("order journey", () => {
  it("shows the order number, status, latest update and distinguishes completed, current and upcoming stops", () => {
    const { container } = render(<OrderJourney order={order(journey(["done", "done", "current", "upcoming", "upcoming", "upcoming"]))} />);
    expect(screen.getByRole("heading", { level: 2, name: "ORD-2026-0009" })).toBeTruthy();
    expect(screen.getByText("RC-TRK-90009")).toBeTruthy();
    expect(screen.getByText("Order Approved", { selector: ".journey-chip" })).toBeTruthy();
    expect(screen.getByText(/Latest update:/)).toBeTruthy();
    expect(container.querySelectorAll(".stop.done").length).toBe(2);
    expect(container.querySelectorAll(".stop.current").length).toBe(1);
    expect(container.querySelectorAll(".stop.upcoming").length).toBe(3);
    expect(container.querySelector(".stop.current").getAttribute("aria-current")).toBe("step");
    expect(container.querySelectorAll(".stop.linked").length).toBe(2);           // the route is lit only up to the current stop
    expect(screen.getByRole("progressbar").getAttribute("aria-valuenow")).toBe("3");
  });

  it("never shows In Transit or Delivered as reached before the status says so", () => {
    const { container } = render(<OrderJourney order={order(journey(["done", "current", "upcoming", "upcoming", "upcoming", "upcoming"]))} />);
    const stops = [...container.querySelectorAll(".stop")];
    expect(stops[4].className).toContain("upcoming");
    expect(stops[5].className).toContain("upcoming");
    expect(stops[4].textContent).toContain("Not yet");
  });

  it("a delivered order shows every stop completed", () => {
    const j = journey(Array(6).fill("done"), { state: "completed", headline: "Delivered", stageNumber: 6 });
    const { container } = render(<OrderJourney order={order(j)} />);
    expect(container.querySelectorAll(".stop.done").length).toBe(6);
    expect(container.querySelector(".journey-completed")).toBeTruthy();
  });

  it("a cancelled order stops where it was and says so clearly", () => {
    const j = journey(["done", "stopped", "upcoming", "upcoming", "upcoming", "upcoming"], {
      state: "cancelled", headline: "Cancelled", stageNumber: 2,
      alerts: [{ kind: "cancelled", title: "Order cancelled", message: "This order was cancelled and will not be delivered.", at: "2026-10-25T09:00:00" }],
    });
    const { container } = render(<OrderJourney order={order(j, { status: "cancelled" })} />);
    expect(screen.getByText("Order cancelled")).toBeTruthy();
    expect(screen.getByText("Cancelled", { selector: ".journey-chip" })).toBeTruthy();
    expect(container.querySelectorAll(".stop.stopped").length).toBe(1);
    expect(container.querySelectorAll(".stop.upcoming").length).toBe(4);
  });

  it("shows a payment problem instead of advancing", () => {
    const j = journey(["done", "current", "upcoming", "upcoming", "upcoming", "upcoming"], {
      headline: "Order Verification", stageNumber: 2,
      alerts: [{ kind: "payment", title: "Payment needed", message: "Your order cannot be verified until the payment is completed.", at: null }],
    });
    render(<OrderJourney order={order(j)} />);
    expect(screen.getByText("Payment needed")).toBeTruthy();
  });

  it("does not invent delivery estimates, couriers or tracking events", () => {
    const { container } = render(<OrderJourney order={order(journey(["done", "done", "done", "done", "current", "upcoming"]))} />);
    expect(container.textContent).not.toMatch(/estimated|courier|arrives by|expected delivery/i);
  });
});

describe("Track My Order page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("rainchem_token", "t");
    client.get.mockImplementation((url) => {
      if (url === "/api/auth/me") return Promise.resolve({ data: { user: { id: 1, name: "Maria", email: "m@x.com" } } });
      if (url === "/api/cart") return Promise.resolve({ data: { items: [] } });
      if (url === "/api/orders") return Promise.resolve({ data: { orders: [{ id: 9, orderNumber: "ORD-2026-0009", statusLabel: "Confirmed", journey: { headline: "Order Approved" } }] } });
      if (url.startsWith("/api/orders/track/ORD-2026-0009")) return Promise.resolve({ data: { order: order(journey(["done", "done", "current", "upcoming", "upcoming", "upcoming"])) } });
      if (url.startsWith("/api/orders/track/")) return Promise.reject({ response: { status: 404, data: { error: "No order found" } } });
      return Promise.resolve({ data: {} });
    });
  });

  const page = (route = "/account/track") => render(<Providers route={route}><AccountTrack /></Providers>);

  it("tracks the order from the link and shows products and delivery details", async () => {
    page("/account/track?order=ORD-2026-0009");
    expect(await screen.findByRole("heading", { level: 2, name: "ORD-2026-0009" })).toBeTruthy();
    expect(screen.getByText(/RAIMOL Oil 1L/)).toBeTruthy();
    expect(screen.getByText("Maria Santos")).toBeTruthy();
    expect(screen.getByText(/Quezon City, Metro Manila/)).toBeTruthy();
    expect(screen.getByText(/Cash on Delivery/)).toBeTruthy();
  });

  it("looks up an order typed by the customer and explains when it is not theirs", async () => {
    const user = userEvent.setup();
    page();
    await user.type(await screen.findByLabelText("Order number or tracking number"), "ORD-9999");
    await user.click(screen.getByRole("button", { name: "Track" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", expect.stringContaining("could not find an order"));
  });

  it("lists the customer's own orders as shortcuts", async () => {
    page();
    expect(await screen.findByRole("button", { name: /ORD-2026-0009 · Order Approved/ })).toBeTruthy();
  });

  it("lets the customer message the admin about this order", async () => {
    const user = userEvent.setup();
    page("/account/track?order=ORD-2026-0009");
    const button = await screen.findByRole("button", { name: "Message the admin about this order" });
    await user.click(button);
    expect(button).toBeTruthy();
  });
});
