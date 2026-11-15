import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AiChat from "../components/chat/AiChat";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const SUGGEST = "I may not have enough information to answer your question accurately. Would you like to chat with our admin for further assistance?";
let nextLog = 0;

function answer(extra = {}) {
  nextLog += 1;
  return { data: { logId: nextLog, answer: "Here is what I found.", confidence: 80, resolved: true, source: "knowledge", canRate: false, related: [], needsHuman: false, ...extra } };
}
const miss = () => answer({ answer: "Sorry, I do not know.", resolved: false, confidence: 5, source: "fallback", needsHuman: true, humanReason: "no_answer", humanMessage: SUGGEST });

async function ask(user, text) {
  await user.type(screen.getByPlaceholderText(/Ask about oil/), text);
  await user.click(screen.getByRole("button", { name: "Send" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  nextLog = 0;
  client.get.mockResolvedValue({ data: { suggestions: [] } });
});

describe("AI assistant suggesting the admin", () => {
  it("labels AI replies and does not suggest a person for a good answer", async () => {
    client.post.mockResolvedValue(answer());
    const user = userEvent.setup();
    render(<AiChat onOpenLive={() => {}} />);
    await ask(user, "What payment methods do you accept?");
    expect(await screen.findByText("Here is what I found.")).toBeTruthy();
    expect(screen.getAllByText("AI assistant").length).toBeGreaterThan(0);
    expect(screen.queryByRole("group", { name: "Chat with our admin" })).toBeNull();
  });

  it("shows the suggestion with a button when the AI cannot answer, and hands the question over", async () => {
    client.post.mockImplementation((url) => (url === "/api/chat/ask" ? Promise.resolve(miss()) : Promise.resolve({ data: { message: "ok" } })));
    const onOpenLive = vi.fn();
    const user = userEvent.setup();
    render(<AiChat onOpenLive={onOpenLive} />);
    await ask(user, "zxqv wibble");
    expect(await screen.findByText(SUGGEST)).toBeTruthy();
    expect(screen.getByText(/shared with the admin/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Chat with admin" }));
    expect(client.post).toHaveBeenCalledWith("/api/live-chat/from-ai", { logIds: [1] });
    expect(onOpenLive).toHaveBeenCalledTimes(1);
  });

  it("does not repeat the suggestion after every message", async () => {
    client.post.mockResolvedValue(miss());
    const user = userEvent.setup();
    render(<AiChat onOpenLive={() => {}} />);
    await ask(user, "first odd question");
    await screen.findByText(SUGGEST);
    for (const text of ["second odd one", "third odd one"]) {
      await ask(user, text);
      await screen.findAllByText("Sorry, I do not know.");
    }
    expect(screen.getAllByText(SUGGEST).length).toBe(1);                 // still only the first one
  });

  it("offers it again later if the AI keeps failing", async () => {
    client.post.mockResolvedValue(miss());
    const user = userEvent.setup();
    render(<AiChat onOpenLive={() => {}} />);
    for (let i = 0; i < 5; i += 1) {
      await ask(user, `odd question ${i}`);
      await screen.findAllByText("Sorry, I do not know.");
      if (i < 4) expect(screen.getAllByText("Sorry, I do not know.").length).toBe(i + 1);
    }
    expect(screen.getAllByText(SUGGEST).length).toBe(2);                 // first reply and the fifth
  });

  it("'Not now' hides the card", async () => {
    client.post.mockResolvedValue(miss());
    const user = userEvent.setup();
    render(<AiChat onOpenLive={() => {}} />);
    await ask(user, "odd");
    await user.click(await screen.findByRole("button", { name: "Not now" }));
    expect(screen.queryByText(SUGGEST)).toBeNull();
  });

  it("asking for a person opens the live chat without sending any context", async () => {
    client.post.mockResolvedValue(answer({ answer: "Sure.", needsHuman: true, humanReason: "requested", humanMessage: "Sure, I can connect you with our admin. Would you like to open the live chat?" }));
    const onOpenLive = vi.fn();
    const user = userEvent.setup();
    render(<AiChat onOpenLive={onOpenLive} />);
    await ask(user, "I want to talk to an admin");
    await user.click(await screen.findByRole("button", { name: "Chat with admin" }));
    expect(client.post).toHaveBeenCalledTimes(1);                        // only the /ask call
    expect(onOpenLive).toHaveBeenCalled();
  });

  it("shows a clear message if the hand-over fails and keeps the chat usable", async () => {
    client.post.mockImplementation((url) => (url === "/api/chat/ask"
      ? Promise.resolve(miss())
      : Promise.reject({ response: { data: { error: "Please verify your email address before chatting with our team" } } })));
    const onOpenLive = vi.fn();
    const user = userEvent.setup();
    render(<AiChat onOpenLive={onOpenLive} />);
    await ask(user, "odd");
    await user.click(await screen.findByRole("button", { name: "Chat with admin" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(onOpenLive).not.toHaveBeenCalled();
  });

  it("a low rating can offer the admin", async () => {
    client.post.mockImplementation((url) => {
      if (url === "/api/chat/ask") return Promise.resolve(answer({ canRate: true }));
      return Promise.resolve({ data: { needsHuman: true, humanReason: "low_rating", humanMessage: "Sorry that answer did not help. Would you like to chat with our admin for further assistance?" } });
    });
    const user = userEvent.setup();
    render(<AiChat onOpenLive={() => {}} />);
    await ask(user, "question");
    await user.click(await screen.findByLabelText("Rate 1 star"));
    expect(await screen.findByText(/Sorry that answer did not help/)).toBeTruthy();
  });
});
