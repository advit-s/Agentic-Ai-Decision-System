// usePermission.jsx — Central permission context for the React app
// Provides current user, role, security mode, and can(permission) check.

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { getCurrentIdentity, getWorkspaceAuditSummary } from "../api";

const PermissionContext = createContext(null);

// Map roles from the backend to frontend display labels
const ROLE_LABELS = {
  owner: "Owner",
  admin: "Admin",
  analyst: "Analyst",
  reviewer: "Reviewer",
  viewer: "Viewer",
};

const DEFAULT_IDENTITY = {
  user: {
    user_id: "local/system",
    display_name: "Local Owner",
    role: "owner",
    created_at: new Date().toISOString(),
    metadata: {},
  },
  permissions: [
    "audit.read",
    "claim.manage",
    "claim.verify",
    "data_source.manage",
    "evidence.search",
    "export.report",
    "graph.manage",
    "provider.manage",
    "report.generate",
    "review.manage",
    "settings.manage",
    "workflow.manage",
    "workspace.manage",
  ],
  security_mode: "demo",
};

export function PermissionProvider({ children }) {
  const [identity, setIdentity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCurrentIdentity();
      setIdentity(data);
    } catch (err) {
      // Fall back to default identity
      setIdentity(DEFAULT_IDENTITY);
      setError(err.message || "Could not load identity");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(() => {
    const user = identity?.user || DEFAULT_IDENTITY.user;
    const permissions = identity?.permissions || DEFAULT_IDENTITY.permissions;
    const securityMode = identity?.security_mode || "demo";
    const role = user?.role || "owner";
    const isDemoMode = securityMode === "demo";
    const isGovernedMode = securityMode === "governed";

    const can = (permission) => {
      if (isDemoMode) return true; // Demo mode allows everything
      return permissions.includes(permission);
    };

    return {
      currentUser: user,
      currentRole: role,
      roleLabel: ROLE_LABELS[role] || role,
      permissions,
      securityMode,
      isDemoMode,
      isGovernedMode,
      can,
      loading,
      error,
      refresh,
    };
  }, [identity, loading, error, refresh]);

  return React.createElement(
    PermissionContext.Provider,
    { value },
    children
  );
}

export function usePermission() {
  const ctx = useContext(PermissionContext);
  if (!ctx) {
    // Return a default (permissive) context if used outside provider
    return {
      currentUser: DEFAULT_IDENTITY.user,
      currentRole: "owner",
      roleLabel: "Owner",
      permissions: DEFAULT_IDENTITY.permissions,
      securityMode: "demo",
      isDemoMode: true,
      isGovernedMode: false,
      can: () => true,
      loading: false,
      error: null,
      refresh: () => {},
    };
  }
  return ctx;
}

export { ROLE_LABELS };
