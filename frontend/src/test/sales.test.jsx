import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PriceTag from "../components/PriceTag";
import { presetRange, salePrice } from "../admin/sales/salePresets";
import { effectiveRate, priceLine } from "../utils/pricing";

describe("sale presets (weeks run Monday to Sunday)", () => {
  const wednesday = new Date(2026, 9, 28); // Wed 28 Oct 2026

  it("today", () => expect(presetRange("today", wednesday)).toEqual({ startDate: "2026-10-28", endDate: "2026-10-28" }));
  it("this week runs from today to Sunday", () => expect(presetRange("thisWeek", wednesday)).toEqual({ startDate: "2026-10-28", endDate: "2026-11-01" }));
  it("next week is the following Monday to Sunday", () => expect(presetRange("nextWeek", wednesday)).toEqual({ startDate: "2026-11-02", endDate: "2026-11-08" }));
  it("next month is the whole of next month", () => expect(presetRange("nextMonth", wednesday)).toEqual({ startDate: "2026-11-01", endDate: "2026-11-30" }));

  it("handles Sundays, month ends and year ends", () => {
    const sunday = new Date(2026, 10, 1);
    expect(presetRange("thisWeek", sunday)).toEqual({ startDate: "2026-11-01", endDate: "2026-11-01" });
    expect(presetRange("nextWeek", sunday)).toEqual({ startDate: "2026-11-02", endDate: "2026-11-08" });
    expect(presetRange("nextMonth", new Date(2026, 11, 15))).toEqual({ startDate: "2027-01-01", endDate: "2027-01-31" });
    expect(presetRange("nextMonth", new Date(2027, 0, 31))).toEqual({ startDate: "2027-02-01", endDate: "2027-02-28" });
  });
});

describe("sale pricing", () => {
  it("500 with 30% off is 350", () => expect(salePrice(500, 30)).toBe(350));

  it("charges the sale price per unit", () => {
    const line = priceLine(500, 2, 30);
    expect(line.unitPrice).toBe(350);
    expect(line.lineTotal).toBe(700);
    expect(line.originalTotal).toBe(1000);
  });

  it("the bigger of sale and bulk discount wins", () => {
    expect(effectiveRate(10, 5)).toBe(0.1);
    expect(effectiveRate(10, 40)).toBe(0.4);
    expect(priceLine(100, 1, 0).unitPrice).toBe(100);
  });
});

describe("price tag", () => {
  it("shows the crossed-out regular price, the sale price and the percent off", () => {
    const { container } = render(<PriceTag product={{ price: 500, onSale: true, salePrice: 350, salePercent: 30 }} />);
    expect(container.querySelector("s").textContent).toContain("500");
    expect(container.querySelector(".price-now").textContent).toContain("350");
    expect(screen.getByText("-30%")).toBeTruthy();
  });

  it("shows only the price when there is no sale", () => {
    const { container } = render(<PriceTag product={{ price: 500, onSale: false }} />);
    expect(container.querySelector("s")).toBeNull();
    expect(container.textContent).toContain("500");
  });
});
