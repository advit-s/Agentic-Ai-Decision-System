// __tests__/PermissionGuard.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { PermissionProvider } from "../src/hooks/usePermission";
import PermissionGuard from "../src/components/PermissionGuard";

describe("PermissionGuard", () => {
  it("renders children when user has permission (demo mode allows all)", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(PermissionGuard, { permission: "settings.manage" },
        React.createElement("div", { "data-testid": "protected-content" }, "Secret Settings")
      )
    ));
    // Wait for permission loading to complete
    await waitFor(() => {
      expect(screen.getByTestId("protected-content")).toBeDefined();
    });
    expect(screen.getByText("Secret Settings")).toBeDefined();
  });

  it("renders children for any permission in demo mode", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(PermissionGuard, { permission: "nonexistent.stuff" },
        React.createElement("div", { "data-testid": "content" }, "Should Show")
      )
    ));
    await waitFor(() => {
      expect(screen.getByTestId("content")).toBeDefined();
    });
  });

  it("shows loading state before permissions resolve", () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(PermissionGuard, { permission: "settings.manage" },
        React.createElement("div", { "data-testid": "protected" }, "Secret")
      )
    ));
    // Initially shows loading state
    expect(screen.getByText("Loading permissions…")).toBeDefined();
  });
});
