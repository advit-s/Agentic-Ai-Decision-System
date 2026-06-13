// components/LoadDropdown.jsx
import React, { useState } from "react";

function LoadDropdown({ workflows, onSelect }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="load-dropdown" onMouseLeave={() => setOpen(false)}>
      <button className="toolbar-btn" onClick={() => setOpen(!open)}>
        Load ▾
      </button>
      {open && (
        <div className="dropdown-menu">
          {workflows.length === 0 && (
            <div className="dropdown-empty">No saved workflows</div>
          )}
          {workflows.map((wf) => (
            <button
              key={wf.id}
              className="dropdown-item"
              onClick={() => {
                onSelect(wf.id);
                setOpen(false);
              }}
            >
              {wf.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LoadDropdown;
