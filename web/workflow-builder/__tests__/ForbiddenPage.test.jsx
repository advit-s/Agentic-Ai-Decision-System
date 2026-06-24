// __tests__/ForbiddenPage.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { PermissionProvider } from "../src/hooks/usePermission";
import ForbiddenPage from "../src/components/ForbiddenPage";

describe("ForbiddenPage", () => {
  it("renders action not allowed message", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ForbiddenPage, { action: "view audit logs", requiredPermission: "audit.read" })
    ));
    await waitFor(() => {
      expect(screen.getByText(/Action Not Allowed/i)).toBeDefined();
    });
    expect(screen.getByText(/view audit logs/i)).toBeDefined();
  });

  it("shows required permission when provided", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ForbiddenPage, { action: "export reports", requiredPermission: "report.export" })
    ));
    await waitFor(() => {
      expect(screen.getByText(/report.export/i)).toBeDefined();
    });
    expect(screen.getByText(/Required Permission/i)).toBeDefined();
  });

  it("shows back button when onBack is provided", async () => {
    const onBack = () => {};
    render(React.createElement(PermissionProvider, null,
      React.createElement(ForbiddenPage, { action: "test", onBack })
    ));
    await waitFor(() => {
      expect(screen.getByText(/Go Back/i)).toBeDefined();
    });
  });

  it("shows user role from context", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ForbiddenPage, { action: "test" })
    ));
    await waitFor(() => {
      expect(screen.getByText(/Your Role:/i)).toBeDefined();
    });
  });

  it("shows security mode from context", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ForbiddenPage, { action: "test" })
    ));
    await waitFor(() => {
      expect(screen.getByText(/Security Mode:/i)).toBeDefined();
    });
  });
});
