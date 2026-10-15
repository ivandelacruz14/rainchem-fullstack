import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);
const STORAGE_KEY = "rainchem_theme";

function systemTheme() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function initialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage blocked: fall through to the system setting */
  }
  return systemTheme();
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(initialTheme);

  // Apply the theme to <html> so the CSS variables in site.css switch.
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // Follow the device setting until the person picks a theme themselves.
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!media) return undefined;
    function onChange(e) {
      let saved = null;
      try { saved = localStorage.getItem(STORAGE_KEY); } catch { /* ignore */ }
      if (!saved) setTheme(e.matches ? "dark" : "light");
    }
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  function chooseTheme(next) {
    setTheme(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
  }

  function toggleTheme() {
    chooseTheme(theme === "dark" ? "light" : "dark");
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme: chooseTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
