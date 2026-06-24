// __tests__/usePermission.test.jsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { PermissionProvider, usePermission } from "../src/hooks/usePermission";

// Helper component that reads the context
function ContextDisplay() {
  const { currentUser, currentRole, roleLabel, isDemoMode, isGovernedMode, can, loading, error } = usePermission();
  if (loading) return React.createElement("div", { "data-testid": "loading" }, "Loading…");
  return React.createElement("div", null,
    React.createElement("span", { "data-testid": "user-name" }, currentUser.display_name),
    React.createElement("span", { "data-testid": "user-role" }, currentRole),
    React.createElement("span", { "data-testid": "role-label" }, roleLabel),
    React.createElement("span", { "data-testid": "mode" }, isDemoMode ? "demo" : "governed"),
    React.createElement("span", { "data-testid": "can-settings" }, String(can("settings.manage"))),
    React.createElement("span", { "data-testid": "can-unknown" }, String(can("nonexistent.permission"))),
  );
}

describe("PermissionProvider / usePermission", () => {
  beforeEach(() => {
    localStorage.removeItem("wfBuilderApiBaseUrl");
  });

  it("provides default identity when no backend responds", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ContextDisplay)
    ));
    // Should fall back to DEFAULT_IDENTITY
    await waitFor(() => {
      expect(screen.getByTestId("user-name").textContent).toBe("Local Owner");
    });
    expect(screen.getByTestId("user-role").textContent).toBe("owner");
    expect(screen.getByTestId("role-label").textContent).toBe("Owner");
  });

  it("defaults to demo mode", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ContextDisplay)
    ));
    await waitFor(() => {
      expect(screen.getByTestId("mode").textContent).toBe("demo");
    });
  });

  it("allows all permissions in demo mode", async () => {
    render(React.createElement(PermissionProvider, null,
      React.createElement(ContextDisplay)
    ));
    await waitFor(() => {
      expect(screen.getByTestId("can-settings").textContent).toBe("true");
      expect(screen.getByTestId("can-unknown").textContent).toBe("true");
    });
  });

  it("usePermission returns defaults when used outside provider", () => {
    function OutsideTest() {
      const ctx = usePermission();
      expect(ctx.currentUser.display_name).toBe("Local Owner");
      expect(ctx.currentRole).toBe("owner");
      expect(ctx.isDemoMode).toBe(true);
      expect(ctx.can("anything")).toBe(true);
      return React.createElement("div", null, "OK");
    }
    render(React.createElement(OutsideTest));
    expect(screen.getByText("OK")).toBeDefined();
  });
});
