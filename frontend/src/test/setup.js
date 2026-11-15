import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import { vi } from "vitest";

URL.createObjectURL = vi.fn(() => "blob:test-image");
URL.revokeObjectURL = vi.fn();
Element.prototype.scrollIntoView = Element.prototype.scrollIntoView || vi.fn();

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
