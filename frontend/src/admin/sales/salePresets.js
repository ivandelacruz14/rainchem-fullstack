// Quick date ranges for a sale. Dates are plain local calendar days (YYYY-MM-DD), weeks run Monday to Sunday.

export function isoDay(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(date, days) {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
  return next;
}

export const PRESETS = [
  { key: "today", label: "Today" },
  { key: "thisWeek", label: "This week" },
  { key: "nextWeek", label: "Next week" },
  { key: "nextMonth", label: "Next month" },
];

export function presetRange(key, now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const sinceMonday = (today.getDay() + 6) % 7;
  const thisMonday = addDays(today, -sinceMonday);

  if (key === "today") return { startDate: isoDay(today), endDate: isoDay(today) };
  if (key === "thisWeek") return { startDate: isoDay(today), endDate: isoDay(addDays(thisMonday, 6)) };
  if (key === "nextWeek") return { startDate: isoDay(addDays(thisMonday, 7)), endDate: isoDay(addDays(thisMonday, 13)) };
  if (key === "nextMonth") {
    const first = new Date(today.getFullYear(), today.getMonth() + 1, 1);
    const last = new Date(today.getFullYear(), today.getMonth() + 2, 0);
    return { startDate: isoDay(first), endDate: isoDay(last) };
  }
  throw new Error(`Unknown preset: ${key}`);
}

export function salePrice(price, percent) {
  const keep = 100 - Number(percent || 0);
  return Math.round((Number(price) * 100 * keep) / 100) / 100;
}
