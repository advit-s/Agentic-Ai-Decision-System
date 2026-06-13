// components/ResizablePanel.jsx
import React, { useState, useCallback, useRef, useEffect } from "react";

export default function ResizablePanel({
  children,
  initialWidth = 380,
  minWidth = 280,
  maxWidth = 900,
}) {
  const [width, setWidth] = useState(initialWidth);
  const [isDragging, setIsDragging] = useState(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const panelRef = useRef(null);

  const handleMouseDown = useCallback(
    (e) => {
      setIsDragging(true);
      startX.current = e.clientX;
      startWidth.current = width;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      e.preventDefault();
    },
    [width]
  );

  useEffect(() => {
    function handleMouseMove(e) {
      if (!isDragging) return;
      const delta = startX.current - e.clientX; // negative = wider (drag left)
      const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidth.current + delta));
      setWidth(newWidth);
    }

    function handleMouseUp() {
      if (!isDragging) return;
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, minWidth, maxWidth]);

  return (
    <div
      ref={panelRef}
      className={`resizable-panel${isDragging ? " resizable-panel-dragging" : ""}`}
      style={{ width: `${width}px` }}
    >
      <div className="resizable-handle" onMouseDown={handleMouseDown} />
      <div className="resizable-content">{children}</div>
    </div>
  );
}
