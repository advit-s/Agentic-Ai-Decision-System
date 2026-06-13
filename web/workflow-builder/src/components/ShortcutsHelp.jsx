// components/ShortcutsHelp.jsx
import React, { useEffect } from "react";
import { SHORTCUTS } from "../hooks/useKeyboardShortcuts";

const KEY_LABELS = {
  ctrl: "Ctrl",
  shift: "Shift",
  escape: "Esc",
  space: "Space",
  delete: "Del",
  backspace: "Bksp",
};

function ShortcutKeys({ combo }) {
  const parts = combo.split("+");
  return (
    <span className="shortcut-keys">
      {parts.map((part, i) => (
        <React.Fragment key={i}>
          {i > 0 && (
            <span style={{ margin: "0 1px", color: "var(--color-text-muted)" }}>+</span>
          )}
          <kbd className="shortcut-key">
            {KEY_LABELS[part] || part.toUpperCase()}
          </kbd>
        </React.Fragment>
      ))}
    </span>
  );
}

export default function ShortcutsHelp({ isOpen, onClose }) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Group shortcuts by category
  const groups = {};
  Object.entries(SHORTCUTS).forEach(([combo, info]) => {
    if (!groups[info.category]) groups[info.category] = [];
    groups[info.category].push({ combo, label: info.label });
  });

  return (
    <div className="shortcuts-overlay" onClick={onClose}>
      <div className="shortcuts-dialog" onClick={(e) => e.stopPropagation()}>
        <h2>Keyboard Shortcuts</h2>
        {Object.entries(groups).map(([category, items]) => (
          <div className="shortcuts-group" key={category}>
            <h3>{category}</h3>
            {items.map((item) => (
              <div className="shortcut-row" key={item.combo}>
                <span className="shortcut-label">{item.label}</span>
                <ShortcutKeys combo={item.combo} />
              </div>
            ))}
          </div>
        ))}
        <button className="shortcuts-close-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
