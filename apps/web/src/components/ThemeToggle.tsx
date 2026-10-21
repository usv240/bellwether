"use client";

import { useEffect, useId, useState } from "react";

type Mode = "light" | "dark";
const ORDER: Mode[] = ["light", "dark"];
const LABEL: Record<Mode, string> = {
  light: "Light",
  dark: "Dark",
};

function Icon({ mode }: { mode: Mode }) {
  const common = { width: 16, height: 16, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  if (mode === "light")
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2.5v2.5M12 19v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M2.5 12H5M19 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

/**
 * Theme: Light or Dark, as one labelled group of two radios, so the
 * current state is visible and arrow keys work. Light is the default on
 * every page whatever the system preference; dark only when chosen here,
 * remembered in localStorage "bw-theme". `compact` draws icons only (each
 * keeps its name for assistive tech and as a tooltip) for the header.
 */
export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const [mode, setMode] = useState<Mode>("light");
  const name = useId();

  useEffect(() => {
    try {
      if (localStorage.getItem("bw-theme") === "dark") setMode("dark");
    } catch {
      // storage unavailable; stay light
    }
    // The header and the menu each draw a toggle; keep them in step.
    const sync = () => setMode(document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");
    window.addEventListener("bw-theme", sync);
    return () => window.removeEventListener("bw-theme", sync);
  }, []);

  const apply = (next: Mode) => {
    setMode(next);
    document.documentElement.setAttribute("data-theme", next);
    window.dispatchEvent(new Event("bw-theme"));
    try {
      if (next === "dark") localStorage.setItem("bw-theme", "dark");
      else localStorage.removeItem("bw-theme");
    } catch {
      // ignore: the choice holds for this page view
    }
  };

  return (
    <fieldset className="seg m-0 min-w-0" data-size={compact ? undefined : "lg"}>
      <legend className="sr-only">Theme</legend>
      {ORDER.map((m) => (
        <label key={m} title={compact ? `${LABEL[m]} theme` : undefined}>
          <input type="radio" name={name} value={m} checked={mode === m} onChange={() => apply(m)} aria-label={compact ? `${LABEL[m]} theme` : undefined} />
          <Icon mode={m} />
          {compact ? null : <span>{LABEL[m]}</span>}
        </label>
      ))}
    </fieldset>
  );
}
