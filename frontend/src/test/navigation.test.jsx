import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import Header from "../components/Header";
import AccountLayout from "../pages/account/AccountLayout";
import { Providers } from "./helpers";
import App from "../App";
import { ThemeProvider } from "../context/ThemeContext";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const USER = { id: 1, name: "Maria Santos", email: "m@example.com" };

function signedIn() {
  localStorage.setItem("rainchem_token", "t");
  client.get.mockImplementation((url) => (url === "/api/auth/me" ? Promise.resolve({ data: { user: USER } }) : Promise.resolve({ data: { items: [] } })));
}

beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });

describe("main navigation", () => {
  it("shows My Orders for signed-in customers, and no Track My Order anywhere in the top menu", async () => {
    client.get.mockRejectedValue({ response: { status: 401 } });
    const first = render(<Providers><Header /></Providers>);
    await screen.findAllByRole("button", { name: "Log In" });
    expect(screen.queryByRole("link", { name: "My Orders" })).toBeNull();
    first.unmount();

    signedIn();
    render(<Providers><Header /></Providers>);
    const nav = await screen.findByRole("navigation", { name: "Main" });
    await screen.findByLabelText("Account menu");
    expect(within(nav).getByRole("link", { name: "My Orders" })).toBeTruthy();
    expect(within(nav).queryByRole("link", { name: /Track/ })).toBeNull();
  });

  it("the account menu holds every account page and Log Out, and no Track link", async () => {
    signedIn();
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    await user.click(await screen.findByLabelText("Account menu"));
    const menu = screen.getByRole("menu");
    for (const label of ["My Account", "Service Requests", "Addresses", "Profile", "Settings & Privacy", "Help Center", "Log Out"]) {
      expect(within(menu).getByRole("menuitem", { name: label })).toBeTruthy();
    }
    expect(within(menu).queryByText(/Track/)).toBeNull();
    expect(within(menu).getByRole("menuitem", { name: "Log Out" })).toBeTruthy();
  });

  it("highlights the page you are on, from the real route", async () => {
    signedIn();
    render(<Providers route="/account/orders"><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "My Orders" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBeNull();
  });

  it("highlights Home only on the home page", async () => {
    signedIn();
    render(<Providers route="/"><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBe("page");
  });
});

describe("account pages", () => {
  it("show only their content: no side menu and no Log Out button in the page", async () => {
    signedIn();
    const { container } = render(
      <Providers route="/account/orders">
        <Routes><Route path="/account/*" element={<AccountLayout />}><Route path="*" element={<div>page content</div>} /></Route></Routes>
      </Providers>,
    );
    expect(await screen.findByText("page content")).toBeTruthy();
    expect(screen.queryByRole("navigation", { name: "Account" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Log Out" })).toBeNull();
    expect(container.querySelector(".account-logout")).toBeNull();
  });
});

describe("old tracking address", () => {
  it("sends /account/track to Track My Order and keeps the order number", async () => {
    signedIn();
    client.get.mockImplementation((url) => {
      if (url === "/api/auth/me") return Promise.resolve({ data: { user: USER } });
      if (url === "/api/orders") return Promise.resolve({ data: { orders: [] } });
      if (url.startsWith("/api/orders/track/")) return Promise.reject({ response: { status: 404, data: {} } });
      return Promise.resolve({ data: { items: [], products: [], suggestions: [] } });
    });
    window.history.pushState({}, "", "/account/track?order=ORD-7");
    render(<ThemeProvider><App /></ThemeProvider>);
    expect(await screen.findByLabelText("Order number or tracking number")).toBeTruthy();
    expect(window.location.pathname).toBe("/track");
    expect(await screen.findByDisplayValue("ORD-7")).toBeTruthy();
  });
});
