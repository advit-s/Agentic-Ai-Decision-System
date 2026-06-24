// PermissionGuard.jsx — Wraps UI sections that require specific permissions
import React from "react";
import { usePermission } from "../hooks/usePermission";
import ForbiddenPage from "./ForbiddenPage";

function PermissionGuard({ permission, children, fallback = null }) {
  const { can, loading } = usePermission();

  if (loading) {
    return React.createElement("div", { className: "pg-loading" }, "Loading permissions…");
  }

  if (can(permission)) {
    return children;
  }

  // If fallback is provided, render it instead
  if (fallback !== null) {
    return fallback;
  }

  // Default forbidden UI inline
  return React.createElement("div", {
    className: "pg-blocked",
    style: { padding: "24px", textAlign: "center", color: "#888" }
  },
    React.createElement("div", { style: { fontSize: "32px", marginBottom: "8px" } }, "🚫"),
    React.createElement("h3", null, "Action Not Available"),
    React.createElement("p", { style: { fontSize: "13px", maxWidth: "400px", margin: "8px auto" } },
      `You need the "${permission}" permission to access this feature.`
    ),
    React.createElement("p", { style: { fontSize: "12px", color: "#999" } },
      "Contact your workspace owner to request access."
    )
  );
}

export default PermissionGuard;
