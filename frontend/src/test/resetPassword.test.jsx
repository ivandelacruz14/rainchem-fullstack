import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import ResetPassword from "../pages/ResetPassword";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

function page(route) {
  return render(
    <Providers route={route}>
      <Routes><Route path="/reset-password" element={<ResetPassword />} /><Route path="/" element={<div>home</div>} /></Routes>
    </Providers>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  client.get.mockImplementation((url) => (url === "/api/auth/me" ? Promise.reject({ response: { status: 401 } }) : Promise.resolve({ data: {} })));
});

describe("reset password page", () => {
  it("is reachable at /reset-password and shows the form for a valid link", async () => {
    client.get.mockImplementation((url) => (url.includes("check") ? Promise.resolve({ data: { valid: true } }) : Promise.reject({ response: { status: 401 } })));
    page("/reset-password?token=abc");
    expect(await screen.findByText("Update password")).toBeTruthy();
    expect(screen.getByText("Confirm new password")).toBeTruthy();
    expect(client.get).toHaveBeenCalledWith("/api/auth/reset-password/check", { params: { token: "abc" } });
  });

  it("explains expired, used or invalid links and offers a new one", async () => {
    client.get.mockImplementation((url) => (url.includes("check")
      ? Promise.resolve({ data: { valid: false, reason: "expired", error: "This reset link has expired. Please request a new one." } })
      : Promise.reject({ response: { status: 401 } })));
    page("/reset-password?token=old");
    expect(await screen.findByText(/has expired/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Request a new link" })).toBeTruthy();
    expect(screen.queryByText("Update password")).toBeNull();
  });

  it("handles a link with no token", async () => {
    page("/reset-password");
    expect(await screen.findByText(/missing its reset code/)).toBeTruthy();
  });

  it("rejects mismatched or weak passwords without calling the server", async () => {
    client.get.mockImplementation((url) => (url.includes("check") ? Promise.resolve({ data: { valid: true } }) : Promise.reject({ response: { status: 401 } })));
    const user = userEvent.setup();
    const { container } = page("/reset-password?token=abc");
    await screen.findByText("Update password");
    const [pw, confirm] = container.querySelectorAll("input");
    await user.type(pw, "Passw0rd!x");
    await user.type(confirm, "Different1!");
    await user.click(screen.getByText("Update password"));
    expect(await screen.findByText(/do not match/)).toBeTruthy();
    expect(client.post).not.toHaveBeenCalled();
  });

  it("submits the new password and shows the success state", async () => {
    client.get.mockImplementation((url) => (url.includes("check") ? Promise.resolve({ data: { valid: true } }) : Promise.reject({ response: { status: 401 } })));
    client.post.mockResolvedValue({ data: { message: "ok" } });
    const user = userEvent.setup();
    const { container } = page("/reset-password?token=abc");
    await screen.findByText("Update password");
    const [pw, confirm] = container.querySelectorAll("input");
    await user.type(pw, "Passw0rd!x");
    await user.type(confirm, "Passw0rd!x");
    await user.click(screen.getByText("Update password"));
    await waitFor(() => expect(client.post).toHaveBeenCalledWith("/api/auth/reset-password", { token: "abc", password: "Passw0rd!x" }));
    expect(await screen.findByText(/password has been updated/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Log in now" })).toBeTruthy();
  });

  it("shows the server's message when the link was already used", async () => {
    client.get.mockImplementation((url) => (url.includes("check") ? Promise.resolve({ data: { valid: true } }) : Promise.reject({ response: { status: 401 } })));
    client.post.mockRejectedValue({ response: { data: { error: "This reset link has already been used.", reason: "used" } } });
    const user = userEvent.setup();
    const { container } = page("/reset-password?token=abc");
    await screen.findByText("Update password");
    const [pw, confirm] = container.querySelectorAll("input");
    await user.type(pw, "Passw0rd!x");
    await user.type(confirm, "Passw0rd!x");
    await user.click(screen.getByText("Update password"));
    expect((await screen.findAllByText(/already been used/)).length).toBeGreaterThan(0);
  });
});
