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

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage unavailable
    }
  }, [theme]);

  function handleToggle() {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }

  return (
    <button
      className="toolbar-btn"
      onClick={handleToggle}
      title={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
      style={{ fontSize: "16px", padding: "4px 10px" }}
    >
      {theme === "light" ? "\u{1F31E}" : "\u{1F319}"}
    </button>
  );
}
