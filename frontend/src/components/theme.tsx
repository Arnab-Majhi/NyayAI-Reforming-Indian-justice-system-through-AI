"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Monitor, Moon, Sun } from "lucide-react";

import { STORAGE_KEY, SYSTEM_QUERY, validTheme, type Theme } from "@/lib/theme";

const ThemeContext = createContext<{ theme: Theme; ready: boolean; setTheme: (theme: Theme) => void } | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, updateTheme] = useState<Theme>("system");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(SYSTEM_QUERY);
    let preference: Theme = "system";
    try { preference = validTheme(localStorage.getItem(STORAGE_KEY)); } catch { /* Storage can be blocked by browser policy. */ }
    const apply = () => {
      document.documentElement.dataset.theme = preference === "system" ? (media.matches ? "dark" : "light") : preference;
      updateTheme(preference);
    };
    apply();
    setReady(true);
    const changed = (event: Event) => {
      if (event instanceof StorageEvent) {
        if (event.key !== STORAGE_KEY && event.key !== null) return;
        preference = validTheme(event.newValue);
      } else if (event instanceof CustomEvent) {
        preference = validTheme(event.detail);
      }
      apply();
    };
    media.addEventListener("change", changed);
    window.addEventListener("storage", changed);
    window.addEventListener("nyayaai-theme-change", changed);
    return () => {
      media.removeEventListener("change", changed);
      window.removeEventListener("storage", changed);
      window.removeEventListener("nyayaai-theme-change", changed);
    };
  }, []);

  const setTheme = (next: Theme) => {
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* Still switch for this tab when persistence is unavailable. */ }
    window.dispatchEvent(new CustomEvent("nyayaai-theme-change", { detail: next }));
  };

  return <ThemeContext.Provider value={{ theme, ready, setTheme }}>{children}</ThemeContext.Provider>;
}

export function ThemeControl() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("ThemeControl requires ThemeProvider");
  const { theme, ready, setTheme } = context;
  const Icon = theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;
  return <label className="theme-control" title="Choose light, dark, or device appearance">
    <Icon size={16} aria-hidden="true" />
    <span className="sr-only">Color theme</span>
    <select value={theme} disabled={!ready} onChange={event => setTheme(validTheme(event.target.value))}>
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  </label>;
}