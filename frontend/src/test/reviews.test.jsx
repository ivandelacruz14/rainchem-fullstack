import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ReviewSection from "../components/reviews/ReviewSection";
import { Providers } from "./helpers";

vi.mock("../api/client", () => {
  const client = { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() };
  return { default: client, SESSION_EXPIRED_EVENT: "rainchem:session-expired" };
});
import client from "../api/client";

const none = { summary: { average: 0, count: 0, distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } }, reviews: [] };

beforeEach(() => {
  vi.clearAllMocks();
  client.get.mockImplementation((url) => (url === "/api/auth/me" ? Promise.reject({ response: { status: 401 } }) : Promise.resolve({ data: none })));
});

describe("review section", () => {
  it("shows a clear message when a product has no reviews", async () => {
    render(<Providers><ReviewSection productId={1} /></Providers>);
    expect(await screen.findByText(/No reviews yet/)).toBeTruthy();
  });

  it("shows the real average, count, author and comment", async () => {
    client.get.mockImplementation((url) => (url === "/api/auth/me" ? Promise.reject({ response: { status: 401 } }) : Promise.resolve({ data: {
      summary: { average: 4.5, count: 2, distribution: { 1: 0, 2: 0, 3: 0, 4: 1, 5: 1 } },
      reviews: [{ id: 1, rating: 5, comment: "Runs smoother", author: "Maria S.", createdAt: "2026-10-01T10:00:00" }],
    } })));
    render(<Providers><ReviewSection productId={1} /></Providers>);
    expect(await screen.findByText("4.5")).toBeTruthy();
    expect(screen.getByText("2 reviews")).toBeTruthy();
    expect(screen.getByText("Runs smoother")).toBeTruthy();
    expect(screen.getByText("Maria S.")).toBeTruthy();
  });
});
