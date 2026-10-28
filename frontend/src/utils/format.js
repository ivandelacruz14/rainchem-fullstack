export function peso(amount) {
  return "\u20b1" + Number(amount).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// The server stores UTC times and sends them without a "Z". Without it the browser would read them
// as local time and show them hours early, so mark them as UTC first.
export function serverDate(isoString) {
  if (!isoString) return null;
  const text = String(isoString);
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(text) ? text : `${text}Z`);
}

export function formatDate(isoString) {
  if (!isoString) return "";
  return serverDate(isoString).toLocaleString("en-PH", {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function formatTime(isoString) {
  if (!isoString) return "";
  return serverDate(isoString).toLocaleTimeString("en-PH", { hour: "numeric", minute: "2-digit" });
}

export function formatDay(isoString) {
  if (!isoString) return "";
  return serverDate(isoString).toLocaleDateString("en-PH", { year: "numeric", month: "short", day: "numeric" });
}

export function validatePassword(password) {
  const errors = [];
  if (!password || password.length < 8) errors.push("At least 8 characters");
  if (password && password.length > 24) errors.push("No more than 24 characters");
  if (!/[A-Z]/.test(password || "")) errors.push("At least one uppercase letter");
  if (!/[a-z]/.test(password || "")) errors.push("At least one lowercase letter");
  if (!/[0-9]/.test(password || "")) errors.push("At least one number");
  if (!/[^A-Za-z0-9]/.test(password || "")) errors.push("At least one special symbol");
  return errors;
}
