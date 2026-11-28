import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import RiderInfo from "../components/RiderInfo";

const base = { status: "shipped", rider: { name: "Ben Cruz", phone: "09171112222" }, estimatedDelivery: "2026-12-03", canReceive: false };

describe("RiderInfo", () => {
  it("shows the rider's name, a call link and the estimated date while the order is on its way", () => {
    render(<RiderInfo order={base} />);
    expect(screen.getByText("Ben Cruz")).toBeTruthy();
    expect(screen.getByRole("link", { name: "09171112222" }).getAttribute("href")).toBe("tel:09171112222");
    expect(screen.getByText(/December 3, 2026/)).toBeTruthy();
  });

  it("asks the customer to confirm once the rider has delivered", () => {
    render(<RiderInfo order={{ ...base, status: "delivered", canReceive: true }} />);
    expect(screen.getByText(/Please confirm that you received it/)).toBeTruthy();
    expect(screen.queryByText("Ben Cruz")).toBeNull(); // the rider's phone is hidden after delivery
  });

  it("shows nothing before a rider is assigned", () => {
    const { container } = render(<RiderInfo order={{ status: "confirmed", rider: null, estimatedDelivery: null, canReceive: false }} />);
    expect(container.firstChild).toBeNull();
  });
});
