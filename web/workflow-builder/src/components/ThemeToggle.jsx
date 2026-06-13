// components/ThemeToggle.jsx
import React, { useState, useEffect } from "react";

const STORAGE_KEY = "wfBuilderTheme";

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    // localStorage unavailable
  }
  return "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(getInitialTheme);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage unavailable
    }
  }, [theme]);

  function handleToggle() {
    setAnimating(true);
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
    setTimeout(() => setAnimating(false), 300);
  }

  const isLight = theme === "light";

  return (
    <button
      className={`toolbar-btn theme-toggle-btn ${animating ? "theme-toggle-animating" : ""}`}
      onClick={handleToggle}
      title={`Current theme: ${theme}. Click to switch to ${isLight ? "dark" : "light"}`}
      aria-label={`Toggle theme (currently ${theme})`}
      role="button"
      style={{ fontSize: "16px", padding: "4px 10px", position: "relative" }}
    >
      <span className="theme-toggle-icon" aria-hidden="true">
        {isLight ? "☀️" : "\u{1F319}"}
      </span>
      <span className="theme-toggle-tooltip" role="tooltip">
        {isLight ? "Dark mode" : "Light mode"}
      </span>
    </button>
  );
}
