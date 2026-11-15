import { describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import LoadingState, { SkeletonGrid } from "../components/LoadingState";
import useAction from "../hooks/useAction";
import { renderHook } from "@testing-library/react";

describe("loading states", () => {
  it("shows a message while data loads", () => {
    render(<LoadingState message="Loading orders..." />);
    expect(screen.getByRole("status").textContent).toContain("Loading orders...");
  });

  it("keeps the product layout while products load", () => {
    const { container } = render(<SkeletonGrid count={6} />);
    expect(container.querySelectorAll(".skeleton-card").length).toBe(6);
    expect(container.querySelector("[aria-busy='true']")).toBeTruthy();
  });
});

describe("double submit guard", () => {
  it("runs the action once while the first call is still running", async () => {
    const { result } = renderHook(() => useAction());
    let release;
    const action = vi.fn(() => new Promise((resolve) => { release = resolve; }));
    let first, second;
    await act(async () => { first = result.current.run(action); second = result.current.run(action); });
    expect(action).toHaveBeenCalledTimes(1);
    await act(async () => { release("done"); await first; });
    await expect(first).resolves.toBe("done");
    await expect(second).resolves.toBeUndefined();
  });

  it("can run again after the first call finishes", async () => {
    const { result } = renderHook(() => useAction());
    const action = vi.fn(async () => "ok");
    await act(async () => { await result.current.run(action); });
    await act(async () => { await result.current.run(action); });
    expect(action).toHaveBeenCalledTimes(2);
  });
});
