// ForbiddenPage.jsx — Shared 403 permission error component
import React from "react";
import { usePermission } from "../hooks/usePermission";

function ForbiddenPage({ action = "this action", requiredPermission = null, onBack }) {
  const { currentRole, roleLabel, isDemoMode } = usePermission();

  return React.createElement("div", {
    className: "forbidden-page",
    style: {
      padding: "40px 24px",
      textAlign: "center",
      maxWidth: "500px",
      margin: "40px auto",
    }
  },
    React.createElement("div", { style: { fontSize: "64px", marginBottom: "16px" } }, "🚫"),
    React.createElement("h2", { style: { margin: "0 0 8px", fontSize: "20px", fontWeight: 600 } },
      "Action Not Allowed"
    ),
    React.createElement("p", { style: { color: "#888", fontSize: "14px", marginBottom: "16px", lineHeight: 1.6 } },
      `You do not have permission to ${action}.`
    ),
    React.createElement("div", {
      style: {
        background: "#f5f5f5",
        borderRadius: "8px",
        padding: "16px",
        marginBottom: "16px",
        textAlign: "left",
        fontSize: "13px",
        lineHeight: 1.8,
      }
    },
      React.createElement("div", null,
        React.createElement("strong", null, "Your Role: "),
        roleLabel,
        " (", currentRole, ")"
      ),
      requiredPermission && React.createElement("div", null,
        React.createElement("strong", null, "Required Permission: "),
        requiredPermission
      ),
      React.createElement("div", null,
        React.createElement("strong", null, "Security Mode: "),
        isDemoMode ? "Demo (all actions allowed)" : "Governed"
      ),
    ),
    React.createElement("p", { style: { fontSize: "12px", color: "#aaa" } },
      "This is a local governance system. Contact your workspace owner if you need elevated permissions."
    ),
    onBack && React.createElement("button", {
      onClick: onBack,
      style: {
        marginTop: "16px",
        padding: "8px 16px",
        border: "1px solid #ddd",
        borderRadius: "6px",
        background: "#fff",
        cursor: "pointer",
        fontSize: "13px",
      }
    }, "← Go Back"),
  );
}

export default ForbiddenPage;
