// hooks/useKeyboardShortcuts.js
import { useEffect } from "react";

export const SHORTCUTS = {
  "ctrl+s": { label: "Save workflow", category: "Workflow" },
  "ctrl+z": { label: "Undo", category: "Edit" },
  "ctrl+shift+z": { label: "Redo", category: "Edit" },
  delete: { label: "Delete selected node", category: "Edit" },
  backspace: { label: "Delete selected node", category: "Edit" },
  "ctrl+c": { label: "Copy selected node", category: "Edit" },
  "ctrl+v": { label: "Paste node", category: "Edit" },
  "ctrl+d": { label: "Duplicate selected node", category: "Edit" },
  escape: { label: "Deselect / close panel", category: "View" },
  space: { label: "Execute workflow", category: "Workflow" },
  "shift+?": { label: "Toggle shortcuts help", category: "View" },
  "ctrl+shift+e": { label: "Export workflow", category: "Workflow" },
};

export default function useKeyboardShortcuts(handlers) {
  useEffect(() => {
    function handleKeyDown(e) {
      // Ignore when typing in an input/textarea
      const tag = e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      const key = e.key.toLowerCase();
      const ctrl = e.ctrlKey || e.metaKey;
      const shift = e.shiftKey;

      // Build shortcut key
      let combo = "";
      if (ctrl) combo += "ctrl+";
      if (shift) combo += "shift+";
      combo += key;

      // Check if shortcut is registered
      if (handlers[combo]) {
        e.preventDefault();
        handlers[combo]();
        return;
      }

      // Single keys (delete, backspace, escape, space)
      if (!ctrl && !shift && handlers[key]) {
        e.preventDefault();
        handlers[key]();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlers]);
}
