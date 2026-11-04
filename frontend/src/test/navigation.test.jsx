import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
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
  it("puts My Orders and Track My Order in the main menu for signed-in customers only", async () => {
    client.get.mockRejectedValue({ response: { status: 401 } });
    const first = render(<Providers><Header /></Providers>);
    await screen.findAllByRole("button", { name: "Log In" });
    expect(screen.queryByRole("link", { name: "Track My Order" })).toBeNull();
    first.unmount();

    signedIn();
    render(<Providers><Header /></Providers>);
    const nav = await screen.findByRole("navigation", { name: "Main" });
    await screen.findByLabelText("Account menu");
    expect(within(nav).getByRole("link", { name: "My Orders" })).toBeTruthy();
    expect(within(nav).getByRole("link", { name: "Track My Order" })).toBeTruthy();
  });

  it("keeps Track My Order out of the profile menu", async () => {
    signedIn();
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    await user.click(await screen.findByLabelText("Account menu"));
    const menu = screen.getByRole("menu");
    expect(within(menu).queryByText(/Track/)).toBeNull();
    expect(within(menu).getByText("My Account")).toBeTruthy();
    expect(within(menu).getByRole("menuitem", { name: "Log Out" })).toBeTruthy();
  });

  it("highlights the page you are on, from the real route", async () => {
    signedIn();
    render(<Providers route="/track"><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Track My Order" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "My Orders" }).getAttribute("aria-current")).toBeNull();
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBeNull();
  });

  it("highlights My Orders on its page, including deeper routes, and Home only on the home page", async () => {
    signedIn();
    const first = render(<Providers route="/account/orders"><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    let nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "My Orders" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBeNull();
    first.unmount();
    render(<Providers route="/"><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    nav = screen.getByRole("navigation", { name: "Main" });
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBe("page");
  });
});

describe("account area", () => {
  function area(route) {
    signedIn();
    return render(
      <Providers route={route}>
        <Routes><Route path="/account/*" element={<AccountLayout />}><Route path="*" element={<div>page content</div>} /></Route><Route path="/" element={<div>home</div>} /></Routes>
      </Providers>,
    );
  }

  it("highlights the current account page and has no Track link", async () => {
    area("/account/orders");
    const nav = await screen.findByRole("navigation", { name: "Account" });
    expect(within(nav).getByRole("link", { name: "My Orders" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Overview" }).getAttribute("aria-current")).toBeNull();
    expect(within(nav).queryByText(/Track/)).toBeNull();
  });

  it("keeps Log Out out of the link list, after the page content, and it logs out", async () => {
    const user = userEvent.setup();
    const { container } = area("/account");
    const nav = await screen.findByRole("navigation", { name: "Account" });
    expect(within(nav).queryByRole("button", { name: "Log Out" })).toBeNull();
    const logout = screen.getByRole("button", { name: "Log Out" });
    expect(container.querySelector(".account-logout").contains(logout)).toBe(true);
    const main = container.querySelector(".account-main");
    expect(main.compareDocumentPosition(logout) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();   // below the content in the DOM
    await user.click(logout);
    expect(localStorage.getItem("rainchem_token")).toBeNull();
    expect(await screen.findByText("home")).toBeTruthy();
  });
});

describe("old tracking address", () => {
  it("sends /account/track to the new Track My Order page and keeps the order number", async () => {
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
    expect(window.location.search).toBe("?order=ORD-7");
    expect(await screen.findByDisplayValue("ORD-7")).toBeTruthy();   // the order number is carried over into the search box
  });
});
