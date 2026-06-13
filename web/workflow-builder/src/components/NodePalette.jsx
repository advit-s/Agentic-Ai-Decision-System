// components/NodePalette.jsx
import React, { useState } from "react";
import { getNodeCategoryConfig, getCategories } from "../nodeTypes";
import "../styles/palette.css";

function NodePalette({ nodeTypes, onDragStart }) {
  const [collapsed, setCollapsed] = useState(false);

  // Group node types by category
  const grouped = {};
  for (const nt of nodeTypes) {
    const cat = nt.categories?.[0] || "flow";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(nt);
  }

  if (collapsed) {
    return (
      <button
        className="palette-toggle"
        onClick={() => setCollapsed(false)}
        title="Show palette"
      >
        📋
      </button>
    );
  }

  return (
    <div className="node-palette">
      <div className="palette-header">
        <span className="palette-title">Nodes</span>
        <button
          className="palette-close"
          onClick={() => setCollapsed(true)}
          title="Hide palette"
        >
          ✕
        </button>
      </div>
      <div className="palette-scroll">
        {getCategories().map((cat) => {
          const items = grouped[cat.id] || [];
          if (!items.length) return null;
          return (
            <div key={cat.id} className="palette-category">
              <div className="palette-category-title" style={{ color: cat.color }}>
                {cat.icon} {cat.label}
              </div>
              {items.map((nt) => (
                <div
                  key={nt.type}
                  className="palette-item"
                  style={{ borderLeftColor: cat.color }}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/json", JSON.stringify(nt));
                    if (onDragStart) onDragStart(nt);
                  }}
                >
                  <span className="palette-item-label">{nt.label}</span>
                  <span className="palette-item-desc">{nt.description}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default NodePalette;
