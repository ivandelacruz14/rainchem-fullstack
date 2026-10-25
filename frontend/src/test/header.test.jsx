import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Header from "../components/Header";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const USER = { id: 7, name: "Maria Santos", email: "maria@example.com" };

function mockServer({ loggedIn, cart = [] }) {
  client.get.mockImplementation((url) => {
    if (url === "/api/auth/me") return loggedIn ? Promise.resolve({ data: { user: USER } }) : Promise.reject({ response: { status: 401 } });
    if (url === "/api/cart") return Promise.resolve({ data: { items: cart } });
    return Promise.resolve({ data: {} });
  });
}

beforeEach(() => vi.clearAllMocks());

describe("header before login", () => {
  it("shows public navigation and Log In / Sign Up, but no cart or dark mode", async () => {
    mockServer({ loggedIn: false });
    render(<Providers><Header /></Providers>);
    expect(await screen.findAllByRole("button", { name: "Log In" })).not.toHaveLength(0);
    expect(screen.getAllByRole("button", { name: "Sign Up" }).length).toBeGreaterThan(0);
    for (const label of ["Home", "Shop", "Services", "FAQs"]) expect(screen.getByRole("link", { name: label })).toBeTruthy();
    expect(screen.queryByText("Cart")).toBeNull();
    expect(screen.queryByText("Dark mode")).toBeNull();
    expect(screen.queryByLabelText("Account menu")).toBeNull();
  });
});

describe("header after login", () => {
  beforeEach(() => localStorage.setItem("rainchem_token", "t"));

  it("puts cart, dark mode and log out inside the account menu", async () => {
    mockServer({ loggedIn: true });
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    const chip = await screen.findByLabelText("Account menu");
    expect(screen.queryByText("Dark mode")).toBeNull();
    await user.click(chip);
    expect(screen.getByRole("menuitem", { name: /Cart/ })).toBeTruthy();
    expect(screen.getByRole("menuitemcheckbox", { name: /Dark mode/ })).toBeTruthy();
    expect(screen.getByRole("menuitem", { name: "Log Out" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Log In" })).toBeNull();
  });

  it("toggles dark mode from the menu", async () => {
    mockServer({ loggedIn: true });
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    await user.click(await screen.findByLabelText("Account menu"));
    const before = document.documentElement.getAttribute("data-theme");
    await user.click(screen.getByRole("menuitemcheckbox", { name: /Dark mode/ }));
    expect(document.documentElement.getAttribute("data-theme")).not.toBe(before);
  });

  it("closes on Escape and on outside click", async () => {
    mockServer({ loggedIn: true });
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    await user.click(await screen.findByLabelText("Account menu"));
    expect(screen.getByRole("menu")).toBeTruthy();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    await user.click(screen.getByLabelText("Account menu"));
    await user.click(document.body);
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("logging out clears the token and the cart and returns to the public header", async () => {
    mockServer({ loggedIn: true, cart: [{ product: { id: 1, name: "Oil", price: 100 }, qty: 2 }] });
    const user = userEvent.setup();
    render(<Providers><Header /></Providers>);
    const chip = await screen.findByLabelText("Account menu");
    await waitFor(() => expect(chip.textContent).toContain("2"));
    await user.click(chip);
    await user.click(screen.getByRole("menuitem", { name: "Log Out" }));
    expect(localStorage.getItem("rainchem_token")).toBeNull();
    expect(await screen.findAllByRole("button", { name: "Log In" })).not.toHaveLength(0);
    expect(screen.queryByLabelText("Account menu")).toBeNull();
  });

  it("signs out when the server reports the session expired", async () => {
    mockServer({ loggedIn: true });
    render(<Providers><Header /></Providers>);
    await screen.findByLabelText("Account menu");
    window.dispatchEvent(new CustomEvent("rainchem:session-expired", { detail: { scope: "user" } }));
    expect(await screen.findAllByRole("button", { name: "Log In" })).not.toHaveLength(0);
    expect(localStorage.getItem("rainchem_token")).toBeNull();
  });
});
