import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RequestDialog from "../admin/approvals/RequestDialog";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const REQUEST = {
  id: 7, kind: "product_update", kindLabel: "Edit product", status: "pending", targetName: "Oil",
  requestedBy: { id: 3, name: "Dina Distributor", role: "Distributor" }, createdAt: "2026-10-25T08:00:00",
  changes: [{ field: "Price", from: "100.00", to: "1.00" }], hasPhoto: false, photo: null,
};

function open({ isHead }) {
  const onChanged = vi.fn();
  render(<Providers><RequestDialog requestId={7} isHead={isHead} onClose={() => {}} onChanged={onChanged} /></Providers>);
  return onChanged;
}

beforeEach(() => {
  vi.clearAllMocks();
  client.get.mockImplementation((url) => (url === "/api/admin/approvals/7" ? Promise.resolve({ data: { request: REQUEST } }) : Promise.reject({ response: { status: 401 } })));
});

describe("approval dialog", () => {
  it("shows what would change, from the current value to the requested one", async () => {
    open({ isHead: true });
    expect(await screen.findByText("Dina Distributor")).toBeTruthy();
    expect(screen.getByText("100.00")).toBeTruthy();
    expect(screen.getByText("1.00")).toBeTruthy();
  });

  it("the change is only applied after the password step and the emailed code", async () => {
    client.post.mockImplementation((url) => {
      if (url.endsWith("/approve/start")) return Promise.resolve({ data: { email: "ad***@example.com", expiresInMinutes: 10 } });
      if (url.endsWith("/approve/confirm")) return Promise.resolve({ data: { request: { ...REQUEST, status: "approved" } } });
      return Promise.reject(new Error("unexpected " + url));
    });
    const user = userEvent.setup();
    const onChanged = open({ isHead: true });

    await user.click(await screen.findByRole("button", { name: "Approve..." }));
    expect(client.post).not.toHaveBeenCalled();                       // opening the step changes nothing

    const sendButton = screen.getByRole("button", { name: "Send code" });
    expect(sendButton.disabled).toBe(true);                           // a password is required first
    await user.type(document.querySelector("input[type=password]"), "Passw0rd!x");
    await user.click(sendButton);
    expect(client.post).toHaveBeenCalledTimes(1);
    expect(client.post).toHaveBeenCalledWith("/api/admin/approvals/7/approve/start", { password: "Passw0rd!x" });
    expect(await screen.findByText(/ad\*\*\*@example.com/)).toBeTruthy();
    expect(onChanged).not.toHaveBeenCalled();                         // still not applied

    const confirmButton = screen.getByRole("button", { name: "Approve and apply" });
    expect(confirmButton.disabled).toBe(true);
    await user.type(screen.getByLabelText("Code"), "12a3456");        // letters are ignored, 6 digits kept
    expect(screen.getByLabelText("Code").value).toBe("123456");
    await user.click(confirmButton);
    expect(client.post).toHaveBeenLastCalledWith("/api/admin/approvals/7/approve/confirm", { code: "123456" });
    expect(onChanged).toHaveBeenCalledWith("Approved and applied");
  });

  it("a wrong password shows the error and does not move to the code step", async () => {
    client.post.mockRejectedValue({ response: { status: 403, data: { error: "Incorrect password" } } });
    const user = userEvent.setup();
    open({ isHead: true });
    await user.click(await screen.findByRole("button", { name: "Approve..." }));
    await user.type(document.querySelector("input[type=password]"), "nope");
    await user.click(screen.getByRole("button", { name: "Send code" }));
    expect(await screen.findByText("Incorrect password")).toBeTruthy();
    expect(screen.queryByLabelText("Code")).toBeNull();
  });

  it("a wrong code shows how many tries are left", async () => {
    client.post.mockImplementation((url) => (url.endsWith("/approve/start")
      ? Promise.resolve({ data: { email: "ad***@example.com" } })
      : Promise.reject({ response: { status: 400, data: { error: "Incorrect code. 4 tries left." } } })));
    const user = userEvent.setup();
    const onChanged = open({ isHead: true });
    await user.click(await screen.findByRole("button", { name: "Approve..." }));
    await user.type(document.querySelector("input[type=password]"), "Passw0rd!x");
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText("Code"), "000000");
    await user.click(screen.getByRole("button", { name: "Approve and apply" }));
    expect(await screen.findByText(/4 tries left/)).toBeTruthy();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("people who are not the Head Admin can only cancel their own request", async () => {
    open({ isHead: false });
    expect(await screen.findByRole("button", { name: "Cancel this request" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Approve..." })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
  });
});
