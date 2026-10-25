import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminAccounts from "../admin/pages/AdminAccounts";
import { AdminAuthProvider } from "../context/AdminAuthContext";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const LABELS = [
  { key: "products", label: "Manage products and run sales or discounts" },
  { key: "services", label: "Manage services, areas and prices, and service requests" },
  { key: "orders", label: "View orders" },
  { key: "manage_orders", label: "Confirm, ship and manage orders, payments, returns and refunds" },
  { key: "customers", label: "View and manage customer accounts" },
  { key: "chatbot", label: "Manage the chatbot knowledge base and chat monitor" },
  { key: "analytics", label: "View sales reports and estimates" },
];
const ALL = LABELS.map((l) => l.key);
const ROLE_INFO = {
  "Head Admin": { allowed: ALL, preset: [], scoped: false },
  Admin: { allowed: ALL, preset: ALL, scoped: false },
  "Support Staff": { allowed: ALL, preset: ["orders", "manage_orders", "customers", "chatbot"], scoped: false },
  Distributor: { allowed: ["products", "services", "orders", "analytics"], preset: [], scoped: true },
};
const ME = { id: 1, name: "System Admin", email: "a@x.com", role: "Super Admin", isHead: true, isActive: true, permissions: ALL };
const STAFF = { id: 5, name: "Paul", email: "p@x.com", role: "Support Staff", isHead: false, isActive: true, permissions: ["orders", "manage_orders", "customers", "chatbot"], createdAt: "2026-10-20T00:00:00" };

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("rainchem_admin_token", "t");
  client.get.mockImplementation((url) => {
    if (url === "/api/admin/auth/me") return Promise.resolve({ data: { admin: ME } });
    if (url === "/api/admin/auth/accounts") {
      return Promise.resolve({ data: { admins: [{ ...ME, createdAt: "2026-09-22T00:00:00" }, STAFF], roles: Object.keys(ROLE_INFO), roleInfo: ROLE_INFO, permissions: LABELS } });
    }
    return Promise.resolve({ data: {} });
  });
});

function renderPage() {
  return render(<Providers><AdminAuthProvider><AdminAccounts /></AdminAuthProvider></Providers>);
}

describe("add account form", () => {
  it("offers Head Admin, Admin, Support Staff and Distributor", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText("+ Add Account"));
    const select = screen.getByLabelText ? screen.getAllByRole("combobox")[0] : null;
    const names = within(select).getAllByRole("option").map((o) => o.textContent);
    expect(names).toEqual(["Head Admin", "Admin", "Support Staff", "Distributor"]);
  });

  it("starts each role with its usual permissions, and a distributor cannot be given the wider ones", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByText("+ Add Account"));
    const select = screen.getAllByRole("combobox")[0];

    // Support Staff preset
    expect(screen.getByLabelText(/Confirm, ship and manage orders/).checked).toBe(true);
    expect(screen.getByLabelText(/Manage products and run sales/).checked).toBe(false);

    await user.selectOptions(select, "Admin");
    expect(screen.getAllByRole("checkbox").every((c) => c.checked)).toBe(true);

    await user.selectOptions(select, "Distributor");
    expect(screen.queryByLabelText(/Confirm, ship and manage orders/)).toBeNull();
    expect(screen.queryByLabelText(/customer accounts/)).toBeNull();
    expect(screen.queryByLabelText(/chatbot/)).toBeNull();
    expect(screen.getByLabelText(/Manage products and run sales/)).toBeTruthy();

    await user.selectOptions(select, "Head Admin");
    expect(screen.getByText(/Head Admins can do everything/)).toBeTruthy();
  });

  it("an existing Support Staff account shows its real access instead of Dashboard only", async () => {
    renderPage();
    expect(await screen.findByText(/Manage orders, Customers, Chatbot/)).toBeTruthy();
    expect(screen.queryByText("Dashboard only")).toBeNull();
  });
});
