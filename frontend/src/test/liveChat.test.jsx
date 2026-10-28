import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LiveChatPanel from "../components/chat/LiveChatPanel";
import MessageThread from "../components/chat/MessageThread";
import { serverDate, formatTime } from "../utils/format";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const USER = { id: 1, name: "Maria Santos", email: "m@example.com" };
const TOPICS = [{ key: "order", label: "Order help" }, { key: "other", label: "Something else" }];

function msg(id, patch = {}) {
  return {
    id, sender: "user", senderName: "Maria Santos", mine: true, kind: "text", body: `message ${id}`, deleted: false,
    status: "sent", createdAt: "2026-10-25T08:00:00", updatedAt: "2026-10-25T08:00:00", ...patch,
  };
}

function server({ messages = [], conversation = null } = {}) {
  client.get.mockImplementation((url) => {
    if (url === "/api/auth/me") return Promise.resolve({ data: { user: USER } });
    if (url === "/api/live-chat") return Promise.resolve({ data: { conversation, messages, topics: TOPICS, unread: 0, serverTime: "x" } });
    if (url === "/api/cart") return Promise.resolve({ data: { items: [] } });
    if (url === "/api/live-chat/orders") return Promise.resolve({ data: { orders: [{ id: 5, orderNumber: "ORD-5", statusLabel: "Shipped" }] } });
    return Promise.resolve({ data: {} });
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("rainchem_token", "t");
});

const panel = () => render(<Providers><LiveChatPanel /></Providers>);

describe("message status ticks", () => {
  it("shows one tick when sent, two when delivered and two coloured when read", () => {
    const messages = [msg(1, { status: "sent" }), msg(2, { status: "delivered" }), msg(3, { status: "read" })];
    const { container } = render(<MessageThread messages={messages} viewer="user" empty="none" />);
    expect(screen.getByLabelText("Sent")).toBeTruthy();
    expect(screen.getByLabelText("Delivered")).toBeTruthy();
    expect(screen.getByLabelText("Read")).toBeTruthy();
    expect(container.querySelectorAll(".ticks.read").length).toBe(1);
    expect(container.querySelectorAll(".ticks.delivered svg path").length).toBe(2);   // double check
    expect(container.querySelectorAll(".ticks.sent svg path").length).toBe(1);        // single check
  });

  it("shows ticks only on your own messages and labels the admin clearly", () => {
    const messages = [msg(1, { sender: "admin", senderName: "Paul", mine: false, status: "read" })];
    const { container } = render(<MessageThread messages={messages} viewer="user" empty="none" />);
    expect(screen.getByText("Paul (Admin)")).toBeTruthy();
    expect(container.querySelector(".ticks")).toBeNull();
  });

  it("shows the date and time and replaces deleted text with a marker", () => {
    const messages = [msg(1, { deleted: true, body: null, status: "deleted" }), msg(2, { createdAt: "2026-10-26T01:30:00" })];
    const { container } = render(<MessageThread messages={messages} viewer="user" empty="none" />);
    expect(screen.getByText("This message was deleted")).toBeTruthy();
    expect(container.querySelectorAll(".thread-day").length).toBe(2);               // two different local days
    expect(container.querySelector("time").getAttribute("title")).toMatch(/2026/);
  });
});

describe("server times are UTC", () => {
  it("marks a time without a zone as UTC", () => {
    expect(serverDate("2026-10-25T08:00:00").toISOString()).toBe("2026-10-25T08:00:00.000Z");
    expect(serverDate("2026-10-25T08:00:00Z").toISOString()).toBe("2026-10-25T08:00:00.000Z");
    expect(serverDate("2026-10-25T16:00:00+08:00").toISOString()).toBe("2026-10-25T08:00:00.000Z");
    expect(serverDate(null)).toBeNull();
    expect(formatTime("2026-10-25T08:00:00")).toMatch(/\d/);
  });
});

describe("customer live chat", () => {
  it("starts a conversation with a topic and sends the message", async () => {
    server();
    client.post.mockResolvedValue({ data: { message: msg(1, { body: "Where is my order?" }), conversation: { id: 1, topic: "order", orderNumber: "ORD-5" } } });
    const user = userEvent.setup();
    panel();
    await screen.findByText("Chat with our admin");
    await user.selectOptions(screen.getByLabelText("What do you need help with?"), "order");
    await user.selectOptions(screen.getByLabelText("Which order?"), "5");
    await user.type(screen.getByLabelText("Message to the admin"), "Where is my order?");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(client.post).toHaveBeenCalledWith("/api/live-chat/messages", { body: "Where is my order?", topic: "order", orderId: 5 });
    expect(await screen.findByText("Where is my order?")).toBeTruthy();
    expect(screen.getByLabelText("Sent")).toBeTruthy();
    expect(screen.getByText("About order ORD-5")).toBeTruthy();
  });

  it("an existing conversation is reused without asking for a topic again", async () => {
    server({ conversation: { id: 1, topic: "order", orderNumber: null }, messages: [msg(1)] });
    panel();
    expect(await screen.findByText("message 1")).toBeTruthy();
    expect(screen.queryByLabelText("What do you need help with?")).toBeNull();
  });

  it("admin replies are marked as read when the chat is open", async () => {
    server({ conversation: { id: 1, topic: "other" }, messages: [msg(2, { sender: "admin", senderName: "Paul", mine: false, status: "delivered" })] });
    client.post.mockResolvedValue({ data: { updated: 1 } });
    panel();
    await screen.findByText("Paul (Admin)");
    await waitFor(() => expect(client.post).toHaveBeenCalledWith("/api/live-chat/read"));
  });

  it("deleting needs a confirmation and then shows the deleted marker", async () => {
    server({ conversation: { id: 1, topic: "other" }, messages: [msg(1, { body: "oops wrong chat" })] });
    client.delete.mockResolvedValue({ data: { message: msg(1, { deleted: true, body: null, status: "deleted" }) } });
    const user = userEvent.setup();
    panel();
    await user.click(await screen.findByLabelText("Delete message"));
    expect(client.delete).not.toHaveBeenCalled();                                    // nothing happens until confirmed
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(client.delete).not.toHaveBeenCalled();
    expect(screen.getByText("oops wrong chat")).toBeTruthy();

    await user.click(screen.getByLabelText("Delete message"));
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete" }));
    expect(client.delete).toHaveBeenCalledWith("/api/live-chat/messages/1");
    expect(await screen.findByText("This message was deleted")).toBeTruthy();
    expect(screen.queryByText("oops wrong chat")).toBeNull();
  });

  it("only your own messages can be deleted", async () => {
    server({ conversation: { id: 1, topic: "other" }, messages: [msg(1), msg(2, { sender: "admin", mine: false, senderName: "Paul" })] });
    panel();
    await screen.findByText("message 1");
    expect(screen.getAllByLabelText("Delete message").length).toBe(1);
  });

  it("shows the server's reason when a message cannot be sent", async () => {
    server();
    client.post.mockRejectedValue({ response: { status: 403, data: { error: "Please verify your email address before chatting with our team" } } });
    const user = userEvent.setup();
    panel();
    await screen.findByText("Chat with our admin");
    await user.type(screen.getByLabelText("Message to the admin"), "hello");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Please verify your email address before chatting with our team");
  });

  it("polls for status changes using the last update time", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    server({ conversation: { id: 1, topic: "other" }, messages: [msg(1, { updatedAt: "2026-10-25T08:00:05" })] });
    panel();
    await screen.findByText("message 1");
    await vi.advanceTimersByTimeAsync(3100);
    const polls = client.get.mock.calls.filter(([url]) => url === "/api/live-chat");
    expect(polls.length).toBeGreaterThanOrEqual(2);
    expect(polls[polls.length - 1][1]).toEqual({ params: { since: "2026-10-25T08:00:05" } });
    vi.useRealTimers();
  });
});
