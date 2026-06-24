// AuditLogPage.jsx — View workspace audit events with filtering
import React, { useState, useEffect, useCallback } from "react";
import { getWorkspaceAuditEvents, getWorkspaceAuditSummary } from "../api";
import { usePermission } from "../hooks/usePermission";
import PermissionGuard from "./PermissionGuard";
import ForbiddenPage from "./ForbiddenPage";

function AuditLogPage({ workspaceId, onNavigate }) {
  const { can, currentUser } = usePermission();
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState("");
  const [filterActor, setFilterActor] = useState("");

  const loadEvents = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (filterType) filters.event_type = filterType;
      if (filterActor) filters.actor = filterActor;
      const data = await getWorkspaceAuditEvents(workspaceId, filters);
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, filterType, filterActor]);

  const loadSummary = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await getWorkspaceAuditSummary(workspaceId);
      setSummary(data);
    } catch {
      // Summary is non-critical
    }
  }, [workspaceId]);

  useEffect(() => { loadEvents(); }, [loadEvents]);
  useEffect(() => { loadSummary(); }, [loadSummary]);

  // Derive unique event types and actors for filters
  const eventTypes = [...new Set(events.map((e) => e.event_type))];
  const actors = [...new Set(events.map((e) => e.actor))];

  if (!workspaceId) {
    return React.createElement("div", { className: "section-page" },
      React.createElement("div", { className: "section-header" },
        React.createElement("h2", null, "📋 Audit Log"),
        React.createElement("p", { className: "section-subtitle" }, "Select a workspace to view audit events.")
      ),
      React.createElement("div", { className: "section-content" },
        React.createElement("div", { className: "placeholder-card" },
          React.createElement("h3", null, "No Workspace Selected"),
          React.createElement("p", { className: "text-muted" }, "Select a workspace in Settings to view audit logs.")
        )
      )
    );
  }

  if (!can("audit.read")) {
    return React.createElement("div", { className: "section-page" },
      React.createElement("div", { className: "section-header" },
        React.createElement("h2", null, "📋 Audit Log"),
        React.createElement("p", { className: "section-subtitle" }, "View workspace audit events")
      ),
      React.createElement(ForbiddenPage, {
        action: "view audit logs",
        requiredPermission: "audit.read",
      })
    );
  }

  return React.createElement("div", { className: "section-page" },
    React.createElement("div", { className: "section-header" },
      React.createElement("h2", null, "📋 Audit Log"),
      React.createElement("p", { className: "section-subtitle" }, "Track actions across the workspace"),
      onNavigate && React.createElement("button", {
        className: "toolbar-btn",
        onClick: () => onNavigate("settings"),
        style: { marginLeft: "auto" }
      }, "← Back to Settings")
    ),
    React.createElement("div", { className: "section-content" },

      // Summary stats
      summary && React.createElement("div", {
        style: {
          display: "flex", gap: "16px", marginBottom: "16px",
          flexWrap: "wrap"
        }
      },
        React.createElement("div", {
          style: {
            background: "#f5f5f5", borderRadius: "8px", padding: "12px 20px",
            flex: "1", minWidth: "120px"
          }
        },
          React.createElement("div", { style: { fontSize: "24px", fontWeight: 700 } }, summary.total_events),
          React.createElement("div", { style: { fontSize: "12px", color: "#888" } }, "Total Events")
        ),
        summary.by_type && Object.entries(summary.by_type).slice(0, 4).map(([type, count]) =>
          React.createElement("div", {
            key: type,
            style: {
              background: "#f5f5f5", borderRadius: "8px", padding: "12px 20px",
              flex: "1", minWidth: "120px"
            }
          },
            React.createElement("div", { style: { fontSize: "24px", fontWeight: 700 } }, count),
            React.createElement("div", { style: { fontSize: "12px", color: "#888" } }, type.replace(/_/g, " "))
          )
        )
      ),

      // Error
      error && React.createElement("div", { className: "workspace-error", style: { marginBottom: "12px" } }, error),

      // Filters
      React.createElement("div", {
        style: { display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap", alignItems: "center" }
      },
        React.createElement("select", {
          value: filterType,
          onChange: (e) => setFilterType(e.target.value),
          style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px" }
        },
          React.createElement("option", { value: "" }, "All Event Types"),
          eventTypes.map((t) => React.createElement("option", { key: t, value: t }, t.replace(/_/g, " ")))
        ),
        React.createElement("select", {
          value: filterActor,
          onChange: (e) => setFilterActor(e.target.value),
          style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px" }
        },
          React.createElement("option", { value: "" }, "All Actors"),
          actors.map((a) => React.createElement("option", { key: a, value: a }, a))
        ),
        React.createElement("button", {
          onClick: () => { setFilterType(""); setFilterActor(""); },
          style: { padding: "6px 12px", borderRadius: "6px", border: "1px solid #ddd", background: "#fff", cursor: "pointer", fontSize: "13px" }
        }, "Clear Filters"),
        React.createElement("span", { style: { fontSize: "12px", color: "#888", marginLeft: "auto" } },
          `${events.length} event(s)`
        )
      ),

      // Loading
      loading && React.createElement("div", { style: { textAlign: "center", padding: "40px", color: "#888" } },
        "Loading audit events…"
      ),

      // Events list
      !loading && events.length === 0 && React.createElement("div", {
        style: { textAlign: "center", padding: "40px", color: "#888" }
      },
        React.createElement("div", { style: { fontSize: "32px", marginBottom: "8px" } }, "📋"),
        React.createElement("p", null, "No audit events found.")
      ),

      !loading && events.length > 0 && React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } },
        events.map((event) =>
          React.createElement("div", {
            key: event.event_id,
            style: {
              background: "#fff", border: "1px solid #eee", borderRadius: "8px",
              padding: "12px 16px", fontSize: "13px", lineHeight: 1.6
            }
          },
            React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" } },
              React.createElement("strong", { style: { textTransform: "capitalize" } },
                (event.event_type || "").replace(/_/g, " ")
              ),
              React.createElement("span", { style: { color: "#888", fontSize: "12px" } },
                event.created_at ? new Date(event.created_at).toLocaleString() : "—"
              )
            ),
            React.createElement("div", { style: { color: "#555" } },
              `By: ${event.actor}`
            ),
            event.metadata && Object.keys(event.metadata).length > 0 && React.createElement("div", {
              style: { color: "#999", fontSize: "12px", marginTop: "2px" }
            },
              Object.entries(event.metadata).map(([k, v]) =>
                React.createElement("span", {
                  key: k,
                  style: { marginRight: "12px" }
                }, `${k}: ${String(v).slice(0, 40)}`)
              )
            )
          )
        )
      )
    )
  );
}

export default AuditLogPage;
