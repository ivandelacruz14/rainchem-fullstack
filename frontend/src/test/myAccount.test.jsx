import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MyAccount from "../admin/pages/MyAccount";
import { AdminAuthProvider } from "../context/AdminAuthContext";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const ME = { id: 1, name: "System Admin", email: "wrong@example.com", role: "Head Admin", isHead: true, permissions: [] };

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("rainchem_admin_token", "t");
  client.get.mockImplementation((url) => (url === "/api/admin/auth/me" ? Promise.resolve({ data: { admin: ME } }) : Promise.resolve({ data: {} })));
});

const page = () => render(<Providers><AdminAuthProvider><MyAccount /></AdminAuthProvider></Providers>);

describe("my account", () => {
  it("changes the email only after the code sent to the new address", async () => {
    client.post.mockImplementation((url) => (url.endsWith("/email/start")
      ? Promise.resolve({ data: { message: "Code sent" } })
      : Promise.resolve({ data: { admin: { ...ME, email: "right@example.com" } } })));
    const user = userEvent.setup();
    page();
    expect(await screen.findByText("wrong@example.com")).toBeTruthy();

    await user.type(screen.getByLabelText("New email"), "right@example.com");
    await user.type(document.querySelector("input[type=password]"), "Passw0rd!x");
    await user.click(screen.getByRole("button", { name: "Send code to new email" }));
    expect(client.post).toHaveBeenCalledWith("/api/admin/auth/me/email/start", { password: "Passw0rd!x", newEmail: "right@example.com" });
    expect(await screen.findByText(/right@example.com/)).toBeTruthy();
    expect(screen.getByText("wrong@example.com")).toBeTruthy();            // not changed yet

    await user.type(screen.getByLabelText("Code"), "654321");
    await user.click(screen.getByRole("button", { name: "Confirm email" }));
    expect(client.post).toHaveBeenLastCalledWith("/api/admin/auth/me/email/confirm", { code: "654321" });
    expect(await screen.findByText("right@example.com")).toBeTruthy();
    expect(screen.queryByText("wrong@example.com")).toBeNull();
  });

  it("shows the server's message when the password is wrong", async () => {
    client.post.mockRejectedValue({ response: { data: { error: "Incorrect password" } } });
    const user = userEvent.setup();
    page();
    await user.type(await screen.findByLabelText("New email"), "right@example.com");
    await user.type(document.querySelector("input[type=password]"), "nope");
    await user.click(screen.getByRole("button", { name: "Send code to new email" }));
    expect(await screen.findByText("Incorrect password")).toBeTruthy();
    expect(screen.queryByLabelText("Code")).toBeNull();
  });
});
