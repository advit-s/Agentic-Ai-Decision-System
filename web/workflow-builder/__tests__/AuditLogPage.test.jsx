// __tests__/AuditLogPage.test.jsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { PermissionProvider } from "../src/hooks/usePermission";
import AuditLogPage from "../src/components/AuditLogPage";

describe("AuditLogPage", () => {
  beforeEach(() => {
    localStorage.removeItem("wfBuilderApiBaseUrl");
  });

  it("shows no-workspace message when workspaceId is not provided", () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(AuditLogPage, { workspaceId: null })
    ));
    expect(screen.getByText(/No Workspace Selected/i)).toBeDefined();
  });

  it("shows audit log header when workspaceId is provided", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(AuditLogPage, { workspaceId: "ws-1" })
    ));
    await waitFor(() => {
      expect(screen.getByText("📋 Audit Log")).toBeDefined();
    });
  });

  it("shows filter dropdowns after loading", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(AuditLogPage, { workspaceId: "ws-1" })
    ));
    await waitFor(() => {
      expect(screen.getByText(/All Event Types/i)).toBeDefined();
    });
    expect(screen.getByText(/All Actors/i)).toBeDefined();
  });

  it("shows back button when onNavigate is provided", async () => {
    const onNavigate = () => {};
    render(React.createElement(PermissionProvider, null,
      React.createElement(AuditLogPage, { workspaceId: "ws-1", onNavigate })
    ));
    await waitFor(() => {
      expect(screen.getByText(/Back to Settings/i)).toBeDefined();
    });
  });

  it("shows total events counter after loading", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(AuditLogPage, { workspaceId: "ws-1" })
    ));
    await waitFor(() => {
      expect(screen.getByText("Total Events")).toBeDefined();
    });
  });
});
