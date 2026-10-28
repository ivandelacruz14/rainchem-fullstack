import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatMonitor from "../admin/pages/ChatMonitor";
import LiveChat from "../admin/pages/LiveChat";
import ChatWidget from "../components/ChatWidget";
import { AdminAuthProvider } from "../context/AdminAuthContext";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const HEAD = { id: 1, name: "Head", email: "h@x.com", role: "Head Admin", isHead: true, permissions: ["livechat", "chatbot"] };
const STAFF = { ...HEAD, id: 2, role: "Support Staff", isHead: false };
const STATS = { total: 2, resolved: 0, unresolved: 2, unanswered: 2, adminResolved: 0, handedOff: 0, averageConfidence: 10 };
const LOGS = [
  { id: 11, question: "Do you sell chain lube?", answer: "Not sure", confidence: 10, resolved: false, adminResolved: false, handedOff: false, createdAt: "2026-10-25T08:00:00", user: { id: 4, name: "Maria" } },
  { id: 12, question: "Ship to Cebu?", answer: "Not sure", confidence: 5, resolved: false, adminResolved: false, handedOff: true, createdAt: "2026-10-25T08:05:00", user: null },
];

function admin(me) {
  localStorage.setItem("rainchem_admin_token", "t");
  return (ui) => render(<Providers><AdminAuthProvider>{ui}</AdminAuthProvider></Providers>);
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("chat monitor", () => {
  function monitor(me = HEAD) {
    client.get.mockImplementation((url) => {
      if (url === "/api/admin/auth/me") return Promise.resolve({ data: { admin: me } });
      if (url === "/api/admin/chat-monitor") return Promise.resolve({ data: { logs: LOGS, stats: STATS } });
      if (url === "/api/admin/chat-monitor/11") return Promise.resolve({ data: { log: LOGS[0], context: [{ id: 20, question: "Earlier question", answer: "Earlier answer", createdAt: "2026-10-25T07:50:00" }], matchedQuestion: null, hasLiveChat: false } });
      return Promise.resolve({ data: {} });
    });
    return admin(me)(<ChatMonitor />);
  }

  it("lists unanswered questions with who asked and what the AI said", async () => {
    monitor();
    expect(await screen.findByText(/Do you sell chain lube\?/)).toBeTruthy();
    expect(screen.getAllByText("Unanswered").length).toBeGreaterThan(0);
    expect(screen.getByText("Maria")).toBeTruthy();
    expect(screen.getByText("Guest")).toBeTruthy();
    expect(screen.getAllByText("Sent to live chat").length).toBeGreaterThan(1);   // the stat box and the badge on that question
  });

  it("opens a review with the conversation around the question", async () => {
    const user = userEvent.setup();
    monitor();
    await user.click((await screen.findAllByRole("button", { name: "Review" }))[0]);
    expect(await screen.findByText("Earlier question")).toBeTruthy();
    expect(screen.getByText("Customer asked")).toBeTruthy();
    expect(screen.getByText("AI answered")).toBeTruthy();
  });

  it("asks before deleting, and cancelling deletes nothing", async () => {
    const user = userEvent.setup();
    monitor();
    await user.click((await screen.findAllByRole("button", { name: "Delete" }))[0]);
    const dialog = screen.getByRole("alertdialog");
    expect(within(dialog).getByText(/chat history, orders and the knowledge base are not affected/)).toBeTruthy();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(client.delete).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("deletes only the chosen record after confirming", async () => {
    client.delete.mockResolvedValue({ data: { message: "Record deleted" } });
    const user = userEvent.setup();
    monitor();
    await user.click((await screen.findAllByRole("button", { name: "Delete" }))[0]);
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete record" }));
    expect(client.delete).toHaveBeenCalledTimes(1);
    expect(client.delete).toHaveBeenCalledWith("/api/admin/chat-monitor/11");
  });

  it("marks a question resolved", async () => {
    client.post.mockResolvedValue({ data: { log: { ...LOGS[0], adminResolved: true } } });
    const user = userEvent.setup();
    monitor();
    await user.click((await screen.findAllByRole("button", { name: "Mark resolved" }))[0]);
    expect(client.post).toHaveBeenCalledWith("/api/admin/chat-monitor/11/resolve", { resolved: true });
  });
});

describe("admin live chat inbox", () => {
  const ROW = { id: 7, user: { id: 4, name: "Maria Santos", email: "m@x.com" }, topic: "order", topicLabel: "Order help", orderNumber: "ORD-5", unread: 2,
    lastMessage: { text: "Where is my order?", from: "user", deleted: false, at: "2026-10-25T08:00:00" }, lastMessageAt: "2026-10-25T08:00:00" };
  const MSG = { id: 1, sender: "user", senderName: "Maria Santos", mine: false, kind: "text", body: "Where is my order?", deleted: false, status: "delivered", createdAt: "2026-10-25T08:00:00", updatedAt: "2026-10-25T08:00:00" };

  function inbox(me = HEAD) {
    client.get.mockImplementation((url) => {
      if (url === "/api/admin/auth/me") return Promise.resolve({ data: { admin: me } });
      if (url === "/api/admin/live-chat/conversations") return Promise.resolve({ data: { conversations: [ROW] } });
      if (url === "/api/admin/live-chat/conversations/7") return Promise.resolve({ data: { conversation: ROW, messages: [MSG], serverTime: "x" } });
      return Promise.resolve({ data: {} });
    });
    return admin(me)(<LiveChat />);
  }

  it("lists who contacted the admin with unread count and the latest message", async () => {
    inbox();
    expect(await screen.findByText("Maria Santos")).toBeTruthy();
    expect(screen.getByText("Where is my order?")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText(/Order help · ORD-5/)).toBeTruthy();
  });

  it("opens a conversation, marks it read, and sends a reply", async () => {
    client.post.mockImplementation((url) => (url.endsWith("/messages")
      ? Promise.resolve({ data: { message: { ...MSG, id: 2, sender: "admin", senderName: "Head", mine: true, body: "It ships today", status: "sent" } } })
      : Promise.resolve({ data: { updated: 1 } })));
    const user = userEvent.setup();
    inbox();
    await user.click(await screen.findByText("Maria Santos"));
    expect(await screen.findAllByText("Where is my order?")).not.toHaveLength(0);
    await waitFor(() => expect(client.post).toHaveBeenCalledWith("/api/admin/live-chat/conversations/7/read"));
    await user.type(screen.getByLabelText("Reply to the customer"), "It ships today");
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(client.post).toHaveBeenCalledWith("/api/admin/live-chat/conversations/7/messages", { body: "It ships today" });
    expect(await screen.findByText("It ships today")).toBeTruthy();
    expect(screen.getByLabelText("Sent")).toBeTruthy();                 // the admin sees the status of their own message
  });

  it("only a Head Admin sees Delete conversation, and it asks first", async () => {
    const user = userEvent.setup();
    inbox(STAFF);
    await user.click(await screen.findByText("Maria Santos"));
    await screen.findByLabelText("Reply to the customer");
    expect(screen.queryByRole("button", { name: "Delete conversation" })).toBeNull();
  });

  it("deleting a conversation needs a confirmation", async () => {
    client.delete.mockResolvedValue({ data: { message: "Conversation deleted" } });
    const user = userEvent.setup();
    inbox(HEAD);
    await user.click(await screen.findByText("Maria Santos"));
    await user.click(await screen.findByRole("button", { name: "Delete conversation" }));
    expect(client.delete).not.toHaveBeenCalled();
    const dialog = screen.getByRole("alertdialog");
    expect(within(dialog).getByText(/permanently deleted/)).toBeTruthy();
    await user.click(within(dialog).getByRole("button", { name: "Delete conversation" }));
    expect(client.delete).toHaveBeenCalledWith("/api/admin/live-chat/conversations/7");
  });

  it("deleting a single message needs a confirmation", async () => {
    client.delete.mockResolvedValue({ data: { message: { ...MSG, deleted: true, body: null, status: "deleted" } } });
    const user = userEvent.setup();
    inbox(HEAD);
    await user.click(await screen.findByText("Maria Santos"));
    await user.click(await screen.findByLabelText("Delete message"));
    expect(client.delete).not.toHaveBeenCalled();
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete message" }));
    expect(client.delete).toHaveBeenCalledWith("/api/admin/live-chat/messages/1");
    expect(await screen.findByText("This message was deleted")).toBeTruthy();
  });
});

describe("chat widget", () => {
  beforeEach(() => {
    localStorage.setItem("rainchem_token", "t");
  });

  function widget(unread) {
    client.get.mockImplementation((url) => {
      if (url === "/api/auth/me") return Promise.resolve({ data: { user: { id: 1, name: "Maria", email: "m@x.com" } } });
      if (url === "/api/cart") return Promise.resolve({ data: { items: [] } });
      if (url === "/api/live-chat/unread") return Promise.resolve({ data: { unread, latest: null } });
      if (url === "/api/chat/suggestions") return Promise.resolve({ data: { suggestions: [] } });
      return Promise.resolve({ data: {} });
    });
    return render(<Providers><ChatWidget /></Providers>);
  }

  it("shows a badge on the chat button when the admin has replied", async () => {
    widget(3);
    expect(await screen.findByLabelText("3 unread messages")).toBeTruthy();
  });

  it("has an AI tab and a Live Chat tab", async () => {
    const user = userEvent.setup();
    widget(0);
    await user.click(await screen.findByTitle("Chat"));
    const ai = await screen.findByRole("tab", { name: /AI Assistant/ });
    expect(ai.getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: /Live Chat/ }).getAttribute("aria-selected")).toBe("false");
  });
});
