import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Composer from "../components/chat/Composer";
import MessageThread from "../components/chat/MessageThread";
import AuthImage from "../components/chat/AuthImage";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const file = (name, type, size = 1000) => new File([new Uint8Array(size)], name, { type });
const picker = (container) => container.querySelector("input[type=file]");

beforeEach(() => vi.clearAllMocks());

describe("message box with images", () => {
  it("previews a chosen image, lets the sender cancel it, and sends text and image together", async () => {
    const onSend = vi.fn().mockResolvedValue();
    const user = userEvent.setup();
    const { container } = render(<Composer onSend={onSend} inputLabel="Message" sendLabel="Send message" maxMb={3} />);
    await user.upload(picker(container), file("damage.png", "image/png"));
    expect(screen.getByAltText("Image to send")).toBeTruthy();
    await user.click(screen.getByLabelText("Remove image"));
    expect(screen.queryByAltText("Image to send")).toBeNull();               // cancelled before sending

    await user.upload(picker(container), file("damage.png", "image/png"));
    await user.type(screen.getByLabelText("Message"), "Look at this");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(onSend).toHaveBeenCalledWith({ body: "Look at this", file: expect.any(File) });
    await waitFor(() => expect(screen.queryByAltText("Image to send")).toBeNull());   // cleared after sending
  });

  it("allows an image without a caption but not an empty message", async () => {
    const onSend = vi.fn().mockResolvedValue();
    const user = userEvent.setup();
    const { container } = render(<Composer onSend={onSend} inputLabel="Message" sendLabel="Send message" />);
    expect(screen.getByRole("button", { name: "Send message" }).disabled).toBe(true);
    await user.upload(picker(container), file("a.jpg", "image/jpeg"));
    expect(screen.getByRole("button", { name: "Send message" }).disabled).toBe(false);
  });

  it("rejects unsupported files and files that are too large with clear messages", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const { container } = render(<Composer onSend={vi.fn()} inputLabel="Message" maxMb={1} />);
    await user.upload(picker(container), file("notes.pdf", "application/pdf"));
    expect((await screen.findByRole("alert")).textContent).toBe("Choose a JPG, PNG or WEBP image.");
    await user.upload(picker(container), file("a.gif", "image/gif"));
    expect(screen.getByRole("alert").textContent).toContain("JPG, PNG or WEBP");
    await user.upload(picker(container), file("huge.png", "image/png", 2 * 1024 * 1024));
    expect(screen.getByRole("alert").textContent).toBe("The image is too large. The limit is 1 MB.");
    expect(screen.queryByAltText("Image to send")).toBeNull();
  });

  it("shows an upload indicator while sending and the server's reason if it fails", async () => {
    let fail;
    const onSend = vi.fn(() => new Promise((_, reject) => { fail = reject; }));
    const user = userEvent.setup();
    const { container } = render(<Composer onSend={onSend} inputLabel="Message" sendLabel="Send message" />);
    await user.upload(picker(container), file("a.png", "image/png"));
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("Uploading image...")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Send message" }).disabled).toBe(true);
    fail({ response: { data: { error: "That file is not a valid JPG, PNG or WEBP image" } } });
    expect((await screen.findByRole("alert")).textContent).toBe("That file is not a valid JPG, PNG or WEBP image");
    expect(screen.getByAltText("Image to send")).toBeTruthy();               // the image stays so it can be retried or removed
  });

  it("keeps plain text messaging working", async () => {
    const onSend = vi.fn().mockResolvedValue();
    const user = userEvent.setup();
    render(<Composer onSend={onSend} inputLabel="Message" sendLabel="Send message" />);
    await user.type(screen.getByLabelText("Message"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send message" }));
    expect(onSend).toHaveBeenCalledWith({ body: "Hello", file: null });
  });
});

describe("images in the conversation", () => {
  const image = (patch = {}) => ({
    id: 1, sender: "admin", senderName: "Paul", mine: false, kind: "image", body: "Here is the invoice", deleted: false, status: "read",
    attachment: { id: 9, mime: "image/png", size: 100 }, createdAt: "2026-10-25T08:00:00", updatedAt: "2026-10-25T08:00:00", ...patch,
  });

  it("fetches the image with the person's login and shows it with its caption", async () => {
    client.get.mockResolvedValue({ data: new Blob(["x"], { type: "image/png" }) });
    render(<MessageThread messages={[image()]} viewer="user" empty="none" imageBase="/api/live-chat/attachments" />);
    const img = await screen.findByAltText("Here is the invoice");
    expect(img.getAttribute("src")).toBe("blob:test-image");
    expect(client.get).toHaveBeenCalledWith("/api/live-chat/attachments/9", { responseType: "blob" });
    expect(screen.getByText("Here is the invoice", { selector: ".bubble-text" })).toBeTruthy();
  });

  it("opens the image full size and closes it again", async () => {
    client.get.mockResolvedValue({ data: new Blob(["x"], { type: "image/png" }) });
    const user = userEvent.setup();
    render(<MessageThread messages={[image({ id: 2, attachment: { id: 10, mime: "image/png", size: 1 } })]} viewer="user" empty="none" imageBase="/x" />);
    await user.click(await screen.findByAltText("Here is the invoice"));
    expect(screen.getByAltText("Full size")).toBeTruthy();
    await user.click(screen.getByLabelText("Close image"));
    expect(screen.queryByAltText("Full size")).toBeNull();
  });

  it("shows a deleted image only as a deleted message", () => {
    render(<MessageThread messages={[image({ id: 3, deleted: true, body: null, attachment: null, status: "deleted" })]} viewer="user" empty="none" imageBase="/x" />);
    expect(screen.getByText("This message was deleted")).toBeTruthy();
    expect(client.get).not.toHaveBeenCalled();
  });

  it("says so when an image cannot be loaded", async () => {
    client.get.mockRejectedValue({ response: { status: 404 } });
    render(<AuthImage src="/missing/77" alt="gone" />);
    expect(await screen.findByText("Image unavailable")).toBeTruthy();
  });
});
