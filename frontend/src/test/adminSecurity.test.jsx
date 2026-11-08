import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdminLogin from "../admin/AdminLogin";
import { AdminAuthProvider, useAdminAuth } from "../context/AdminAuthContext";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const ME = { id: 1, name: "Head", email: "h@example.com", role: "Head Admin", isHead: true, permissions: [] };

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => vi.useRealTimers());

describe("admin sign-in with the emailed code", () => {
  it("asks for the code after the password, then signs in with the token", async () => {
    client.post
      .mockResolvedValueOnce({ status: 202, data: { otpRequired: true, challenge: "c-1", maskedEmail: "h*@example.com" } })
      .mockResolvedValueOnce({ status: 200, data: { token: "tok-1", admin: ME, idleMinutes: 10 } });
    const user = userEvent.setup();
    render(<Providers><AdminAuthProvider><AdminLogin /></AdminAuthProvider></Providers>);

    await user.type(screen.getByLabelText("Email"), "h@example.com");
    await user.type(document.querySelector("input[type=password]"), "Passw0rd!x");
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText(/h\*@example\.com/)).toBeTruthy();
    expect(sessionStorage.getItem("rainchem_admin_token")).toBeNull();          // not signed in yet

    await user.type(screen.getByLabelText("Code"), "123456");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(client.post).toHaveBeenLastCalledWith("/api/admin/auth/login/verify", { challenge: "c-1", code: "123456" });
    await waitFor(() => expect(sessionStorage.getItem("rainchem_admin_token")).toBe("tok-1"));
    expect(localStorage.getItem("rainchem_admin_token")).toBeNull();              // never kept after the browser closes
  });

  it("the code box takes digits only and needs all six", async () => {
    client.post.mockResolvedValueOnce({ status: 202, data: { otpRequired: true, challenge: "c", maskedEmail: "x" } });
    const user = userEvent.setup();
    render(<Providers><AdminAuthProvider><AdminLogin /></AdminAuthProvider></Providers>);
    await user.type(screen.getByLabelText("Email"), "h@example.com");
    await user.type(document.querySelector("input[type=password]"), "Passw0rd!x");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.type(await screen.findByLabelText("Code"), "12a34");
    expect(screen.getByLabelText("Code").value).toBe("1234");
    expect(screen.getByRole("button", { name: "Sign in" }).disabled).toBe(true);
  });
});

describe("idle timeout", () => {
  function Probe() {
    const { admin, warningSeconds } = useAdminAuth();
    return <div>{admin ? "signed-in" : "signed-out"} {warningSeconds === null ? "" : `warn-${warningSeconds}`}</div>;
  }

  it("warns in the last minute, then signs out and says why", async () => {
    vi.useFakeTimers();
    sessionStorage.setItem("rainchem_admin_token", "tok");
    client.get.mockResolvedValue({ data: { admin: ME, idleMinutes: 3 } });
    client.post.mockResolvedValue({ data: { ok: true } });
    render(<AdminAuthProvider><Probe /></AdminAuthProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    expect(screen.getByText(/signed-in/)).toBeTruthy();

    await act(async () => { await vi.advanceTimersByTimeAsync(2 * 60 * 1000 + 5000); });
    expect(screen.getByText(/warn-5/)).toBeTruthy();                             // the last minute is counted down

    await act(async () => { await vi.advanceTimersByTimeAsync(60 * 1000); });
    expect(screen.getByText(/signed-out/)).toBeTruthy();
    expect(sessionStorage.getItem("rainchem_admin_token")).toBeNull();
    expect(sessionStorage.getItem("rainchem_admin_notice")).toContain("3 minuto");
  });

  it("activity resets the timer, and the warning can be dismissed by staying signed in", async () => {
    vi.useFakeTimers();
    sessionStorage.setItem("rainchem_admin_token", "tok");
    client.get.mockResolvedValue({ data: { admin: ME, idleMinutes: 3 } });
    client.post.mockResolvedValue({ data: { ok: true } });
    render(<AdminAuthProvider><Probe /></AdminAuthProvider>);
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });

    await act(async () => { await vi.advanceTimersByTimeAsync(90 * 1000); });
    await act(async () => { window.dispatchEvent(new Event("mousemove")); await vi.advanceTimersByTimeAsync(10); });
    expect(screen.getByText(/signed-in/)).toBeTruthy();
    expect(screen.queryByText(/warn-/)).toBeNull();                              // activity cleared the warning
  });
});
