// components/TemplateDialog.jsx — Modal dialog for selecting workflow templates
import React from "react";
import TEMPLATES from "../templates";
import "../styles/template-dialog.css";

const CATEGORY_META = {
  starter:    { icon: "⬜", label: "Starter" },
  evidence:   { icon: "🔍", label: "Evidence" },
  full:       { icon: "🤖", label: "Full Pipeline" },
  compliance: { icon: "🛡️", label: "Risk & Compliance" },
  report:     { icon: "📄", label: "Report" },
  data:       { icon: "📊", label: "Data Analysis" },
  research:   { icon: "🔬", label: "Research" },
};

function nodeCountFor(tpl) {
  return tpl.nodes.length;
}

function edgeCountFor(tpl) {
  return tpl.connections.length;
}

function TemplateDialog({ isOpen, onSelect, onClose }) {
  if (!isOpen) return null;

  const grouped = {};
  TEMPLATES.forEach((t) => {
    const cat = t.category || "starter";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(t);
  });

  return (
    <div className="template-overlay" onClick={onClose}>
      <div className="template-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="template-dialog-header">
          <span className="template-dialog-title">📋 New from Template</span>
          <button className="template-close-btn" onClick={onClose} title="Close">
            ✕
          </button>
        </div>
        <div className="template-dialog-body">
          {Object.entries(grouped).map(([cat, tpls]) => {
            const meta = CATEGORY_META[cat] || { icon: "📄", label: cat };
            return (
              <div key={cat} className="template-group">
                <div className="template-group-label">
                  {meta.icon} {meta.label}
                </div>
                <div className="template-grid">
                  {tpls.map((tpl, i) => (
                    <button
                      key={`${cat}-${i}`}
                      className="template-card"
                      onClick={() => onSelect(tpl)}
                    >
                      <div className="template-card-icon">{tpl.icon}</div>
                      <div className="template-card-body">
                        <div className="template-card-name">{tpl.name}</div>
                        <div className="template-card-desc">{tpl.description}</div>
                        <div className="template-card-meta">
                          <span className="template-card-stat">
                            {nodeCountFor(tpl)} nodes
                          </span>
                          {edgeCountFor(tpl) > 0 && (
                            <>
                              <span className="template-card-stat-sep">·</span>
                              <span className="template-card-stat">
                                {edgeCountFor(tpl)} connections
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default TemplateDialog;
