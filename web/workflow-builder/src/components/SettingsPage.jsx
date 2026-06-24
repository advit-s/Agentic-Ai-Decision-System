// SettingsPage.jsx — General settings, security settings, user/membership management, and audit log
import React, { useState, useEffect, useCallback } from "react";
import WorkspaceSelector from "./WorkspaceSelector";
import AuditLogPage from "./AuditLogPage";
import { usePermission } from "../hooks/usePermission";
import PermissionGuard from "./PermissionGuard";
import ForbiddenPage from "./ForbiddenPage";
import {
  getSecuritySettings,
  updateSecuritySettings,
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listWorkspaceMemberships,
  createWorkspaceMembership,
  updateWorkspaceMembership,
  deleteWorkspaceMembership,
} from "../api";

function SettingsPage({ workspaceId, onWorkspaceChange, onNavigate }) {
  const { currentUser, currentRole, roleLabel, securityMode, isDemoMode, can } = usePermission();
  const [tab, setTab] = useState("general");
  const [settings, setSettings] = useState(null);
  const [settingsLoading, setSettingsLoading] = useState(true);
  const [settingsError, setSettingsError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  // Security settings form
  const [formMode, setFormMode] = useState("demo");
  const [formExportsAdmin, setFormExportsAdmin] = useState(false);
  const [formReviewReviewer, setFormReviewReviewer] = useState(true);
  const [formRetention, setFormRetention] = useState(90);

  // Users & Memberships
  const [users, setUsers] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [showAddUser, setShowAddUser] = useState(false);
  const [addUserName, setAddUserName] = useState("");
  const [addUserRole, setAddUserRole] = useState("viewer");
  const [addMembershipUserId, setAddMembershipUserId] = useState("");
  const [addMembershipRole, setAddMembershipRole] = useState("viewer");

  const loadSettings = useCallback(async () => {
    setSettingsLoading(true);
    setSettingsError(null);
    try {
      const data = await getSecuritySettings();
      setSettings(data);
      setFormMode(data.security_mode || "demo");
      setFormExportsAdmin(data.exports_require_admin || false);
      setFormReviewReviewer(data.review_requires_reviewer_role !== false);
      setFormRetention(data.audit_retention_days || 90);
    } catch (err) {
      setSettingsError(err.message);
      // Use defaults
      setSettings({ security_mode: "demo", exports_require_admin: false, review_requires_reviewer_role: true, audit_retention_days: 90 });
    } finally {
      setSettingsLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await listUsers();
      setUsers(data || []);
    } catch {
      setUsers([]);
    }
    try {
      if (workspaceId) {
        const data = await listWorkspaceMemberships(workspaceId);
        setMemberships(data || []);
      }
    } catch {
      setMemberships([]);
    } finally {
      setUsersLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => { loadSettings(); }, [loadSettings]);
  useEffect(() => { if (tab === "users") loadUsers(); }, [tab, loadUsers]);

  const handleSaveSettings = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      const result = await updateSecuritySettings({
        security_mode: formMode,
        exports_require_admin: formExportsAdmin,
        review_requires_reviewer_role: formReviewReviewer,
        audit_retention_days: formRetention,
      });
      setSettings(result);
      setSaveMsg({ type: "success", text: "Settings saved successfully." });
    } catch (err) {
      setSaveMsg({ type: "error", text: `Failed to save: ${err.message}` });
    } finally {
      setSaving(false);
    }
  };

  const handleAddUser = async () => {
    if (!addUserName.trim()) return;
    try {
      await createUser(addUserName.trim(), addUserRole);
      setAddUserName("");
      setAddUserRole("viewer");
      setShowAddUser(false);
      await loadUsers();
    } catch (err) {
      setSaveMsg({ type: "error", text: `Failed to create user: ${err.message}` });
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      await deleteUser(userId);
      await loadUsers();
    } catch (err) {
      setSaveMsg({ type: "error", text: `Failed to delete user: ${err.message}` });
    }
  };

  const handleAddMembership = async () => {
    if (!addMembershipUserId || !workspaceId) return;
    try {
      await createWorkspaceMembership(workspaceId, addMembershipUserId, addMembershipRole);
      setAddMembershipUserId("");
      setAddMembershipRole("viewer");
      await loadUsers();
    } catch (err) {
      setSaveMsg({ type: "error", text: `Failed to add membership: ${err.message}` });
    }
  };

  const handleRemoveMembership = async (userId) => {
    try {
      await deleteWorkspaceMembership(workspaceId, userId);
      await loadUsers();
    } catch (err) {
      setSaveMsg({ type: "error", text: `Failed to remove membership: ${err.message}` });
    }
  };

  // Get available users not yet in this workspace
  const availableUsers = users.filter(
    (u) => !memberships.find((m) => m.user_id === u.user_id)
  );

  const tabs = [
    { id: "general", label: "General" },
    { id: "users", label: "Users & Memberships" },
    { id: "audit", label: "Audit Log" },
  ];

  // Only show Security tab if user can manage settings
  if (can("settings.manage")) {
    tabs.push({ id: "security", label: "Security" });
  }

  return React.createElement("div", { className: "section-page" },
    React.createElement("div", { className: "section-header" },
      React.createElement("h2", null, "⚙️ Settings"),
      React.createElement("p", { className: "section-subtitle" }, "Manage workspaces, security, users, and applications")
    ),

    // Tabs
    React.createElement("div", {
      style: { display: "flex", gap: "4px", borderBottom: "1px solid #eee", padding: "0 24px", marginBottom: "16px" }
    },
      tabs.map((t) =>
        React.createElement("button", {
          key: t.id,
          onClick: () => setTab(t.id),
          style: {
            padding: "10px 16px",
            border: "none",
            borderBottom: tab === t.id ? "2px solid #3b82f6" : "2px solid transparent",
            background: "none",
            cursor: "pointer",
            fontWeight: tab === t.id ? 600 : 400,
            color: tab === t.id ? "#3b82f6" : "#666",
            fontSize: "13px",
          }
        }, t.label)
      )
    ),

    React.createElement("div", { className: "section-content" },

      // === General Tab ===
      tab === "general" && React.createElement("div", null,
        React.createElement("div", { className: "placeholder-card" },
          React.createElement(WorkspaceSelector, {
            workspaceId,
            onWorkspaceChange: onWorkspaceChange || (() => {}),
          })
        ),
        React.createElement("div", { className: "placeholder-card" },
          React.createElement("h3", null, "Your Identity"),
          React.createElement("table", { style: { width: "100%", fontSize: "13px", lineHeight: 2 } },
            React.createElement("tbody", null,
              React.createElement("tr", null,
                React.createElement("td", { style: { color: "#888", paddingRight: "16px", width: "140px" } }, "User"),
                React.createElement("td", null, currentUser?.display_name || "—")
              ),
              React.createElement("tr", null,
                React.createElement("td", { style: { color: "#888" } }, "User ID"),
                React.createElement("td", null, currentUser?.user_id || "—")
              ),
              React.createElement("tr", null,
                React.createElement("td", { style: { color: "#888" } }, "Role"),
                React.createElement("td", null, `${roleLabel} (${currentRole})`)
              ),
              React.createElement("tr", null,
                React.createElement("td", { style: { color: "#888" } }, "Security Mode"),
                React.createElement("td", null, isDemoMode ? "🟡 Demo" : "🟢 Governed")
              ),
            )
          ),
          React.createElement("p", { className: "text-muted", style: { marginTop: "12px", fontSize: "12px" } },
            "This is a local identity system. No passwords or external authentication."
          )
        ),
        React.createElement("div", { className: "placeholder-card" },
          React.createElement("h3", null, "About"),
          React.createElement("p", { className: "text-muted" },
            "Agentic Decision System — v1.27.1-dev"
          ),
          React.createElement("p", { className: "text-muted", style: { marginTop: "4px" } },
            "Local-first Company Intelligence Engine"
          ),
          React.createElement("p", { className: "text-muted", style: { marginTop: "8px", fontSize: "12px", fontStyle: "italic" } },
            "This is a local governance foundation, not a full enterprise authentication system."
          )
        )
      ),

      // === Security Tab ===
      tab === "security" && React.createElement("div", null,
        !can("settings.manage")
          ? React.createElement(ForbiddenPage, { action: "change security settings", requiredPermission: "settings.manage" })
          : React.createElement("div", null,
            settingsLoading && React.createElement("div", { style: { textAlign: "center", padding: "40px", color: "#888" } }, "Loading settings…"),
            !settingsLoading && React.createElement("div", null,
              saveMsg && React.createElement("div", {
                style: {
                  padding: "8px 16px", borderRadius: "6px", marginBottom: "12px",
                  background: saveMsg.type === "success" ? "#d4edda" : "#f8d7da",
                  color: saveMsg.type === "success" ? "#155724" : "#721c24",
                  fontSize: "13px"
                }
              }, saveMsg.text),

              React.createElement("div", { className: "placeholder-card" },
                React.createElement("h3", null, "Security Mode"),
                React.createElement("div", { style: { marginTop: "8px", lineHeight: 1.8 } },
                  React.createElement("label", { style: { display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" } },
                    React.createElement("input", {
                      type: "radio", name: "secmode", value: "demo",
                      checked: formMode === "demo",
                      onChange: () => setFormMode("demo")
                    }),
                    React.createElement("span", null,
                      React.createElement("strong", null, "Demo Mode"),
                      " — All actions allowed, no permission enforcement"
                    )
                  ),
                  React.createElement("label", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                    React.createElement("input", {
                      type: "radio", name: "secmode", value: "governed",
                      checked: formMode === "governed",
                      onChange: () => setFormMode("governed")
                    }),
                    React.createElement("span", null,
                      React.createElement("strong", null, "Governed Mode"),
                      " — Role-based permissions enforced"
                    )
                  ),
                  React.createElement("p", { style: { marginTop: "8px", fontSize: "12px", color: "#e67e22", fontStyle: "italic" } },
                    "Demo mode is for local evaluation. Governed mode enforces role-based permissions."
                  )
                )
              ),

              React.createElement("div", { className: "placeholder-card" },
                React.createElement("h3", null, "Governance Rules"),
                React.createElement("div", { style: { marginTop: "8px", lineHeight: 2 } },
                  React.createElement("label", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                    React.createElement("input", {
                      type: "checkbox",
                      checked: formExportsAdmin,
                      onChange: (e) => setFormExportsAdmin(e.target.checked)
                    }),
                    "Require admin/owner role to export reports"
                  ),
                  React.createElement("label", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                    React.createElement("input", {
                      type: "checkbox",
                      checked: formReviewReviewer,
                      onChange: (e) => setFormReviewReviewer(e.target.checked)
                    }),
                    "Require reviewer role (or higher) to resolve review gates"
                  ),
                  React.createElement("div", { style: { marginTop: "8px", display: "flex", alignItems: "center", gap: "8px" } },
                    React.createElement("label", null, "Audit retention (days):"),
                    React.createElement("input", {
                      type: "number", min: 1, max: 365,
                      value: formRetention,
                      onChange: (e) => setFormRetention(parseInt(e.target.value) || 90),
                      style: { width: "80px", padding: "4px 8px", borderRadius: "4px", border: "1px solid #ddd", fontSize: "13px" }
                    })
                  )
                )
              ),

              React.createElement("button", {
                onClick: handleSaveSettings,
                disabled: saving,
                style: {
                  padding: "10px 20px", borderRadius: "6px", border: "none",
                  background: saving ? "#ccc" : "#3b82f6", color: "#fff",
                  cursor: saving ? "default" : "pointer", fontWeight: 600, fontSize: "13px"
                }
              }, saving ? "Saving…" : "Save Security Settings")
            )
          )
      ),

      // === Users & Memberships Tab ===
      tab === "users" && React.createElement("div", null,
        React.createElement("div", { className: "placeholder-card" },
          React.createElement("h3", null, "Local Users"),
          React.createElement("p", { className: "text-muted", style: { fontSize: "12px", marginBottom: "12px" } },
            "This is a local identity system. No passwords or external authentication."
          ),

          !can("settings.manage")
            ? React.createElement("p", { style: { color: "#888", fontSize: "13px" } }, "You need settings.manage permission to manage users.")
            : React.createElement("div", null,
              React.createElement("button", {
                onClick: () => setShowAddUser(!showAddUser),
                style: {
                  padding: "6px 12px", borderRadius: "6px", border: "1px solid #3b82f6",
                  background: "#fff", color: "#3b82f6", cursor: "pointer", fontSize: "13px", marginBottom: "12px"
                }
              }, showAddUser ? "Cancel" : "+ Add User"),

              showAddUser && React.createElement("div", {
                style: {
                  background: "#f9f9f9", borderRadius: "8px", padding: "12px",
                  marginBottom: "12px", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center"
                }
              },
                React.createElement("input", {
                  placeholder: "Display name", value: addUserName,
                  onChange: (e) => setAddUserName(e.target.value),
                  style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px", flex: "1", minWidth: "150px" }
                }),
                React.createElement("select", {
                  value: addUserRole,
                  onChange: (e) => setAddUserRole(e.target.value),
                  style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px" }
                },
                  React.createElement("option", { value: "viewer" }, "Viewer"),
                  React.createElement("option", { value: "analyst" }, "Analyst"),
                  React.createElement("option", { value: "reviewer" }, "Reviewer"),
                  React.createElement("option", { value: "admin" }, "Admin"),
                  React.createElement("option", { value: "owner" }, "Owner"),
                ),
                React.createElement("button", {
                  onClick: handleAddUser, disabled: !addUserName.trim(),
                  style: {
                    padding: "6px 12px", borderRadius: "6px", border: "none",
                    background: !addUserName.trim() ? "#ccc" : "#3b82f6", color: "#fff",
                    cursor: !addUserName.trim() ? "default" : "pointer", fontSize: "13px"
                  }
                }, "Create")
              ),

              usersLoading && React.createElement("div", { style: { textAlign: "center", padding: "20px", color: "#888", fontSize: "13px" } }, "Loading users…"),

              !usersLoading && users.length === 0 && React.createElement("div", { style: { textAlign: "center", padding: "20px", color: "#888", fontSize: "13px" } }, "No users found."),

              !usersLoading && users.length > 0 && React.createElement("div", { style: { overflowX: "auto" } },
                React.createElement("table", { style: { width: "100%", fontSize: "13px", borderCollapse: "collapse" } },
                  React.createElement("thead", null,
                    React.createElement("tr", { style: { borderBottom: "2px solid #eee" } },
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "Display Name"),
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "User ID"),
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "Role"),
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "Created"),
                      React.createElement("th", { style: { textAlign: "right", padding: "8px" } }, "Actions"),
                    )
                  ),
                  React.createElement("tbody", null,
                    users.map((u) =>
                      React.createElement("tr", {
                        key: u.user_id,
                        style: { borderBottom: "1px solid #f0f0f0" }
                      },
                        React.createElement("td", { style: { padding: "8px" } }, u.display_name),
                        React.createElement("td", { style: { padding: "8px", color: "#888", fontSize: "12px" } }, u.user_id),
                        React.createElement("td", { style: { padding: "8px" } }, u.role),
                        React.createElement("td", { style: { padding: "8px", color: "#888", fontSize: "12px" } },
                          u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"
                        ),
                        React.createElement("td", { style: { padding: "8px", textAlign: "right" } },
                          u.user_id !== "local/system" && React.createElement("button", {
                            onClick: () => handleDeleteUser(u.user_id),
                            style: {
                              padding: "4px 8px", borderRadius: "4px", border: "1px solid #e74c3c",
                              background: "#fff", color: "#e74c3c", cursor: "pointer", fontSize: "12px"
                            }
                          }, "Delete")
                        )
                      )
                    )
                  )
                )
              )
            )
        ),

        // Workspace Memberships
        React.createElement("div", { className: "placeholder-card" },
          React.createElement("h3", null, "Workspace Memberships"),
          React.createElement("p", { className: "text-muted", style: { fontSize: "12px", marginBottom: "12px" } },
            `Workspace: ${workspaceId || "—"}`
          ),

          !can("settings.manage")
            ? React.createElement("p", { style: { color: "#888", fontSize: "13px" } }, "You need settings.manage permission to manage memberships.")
            : React.createElement("div", null,
              // Add membership form
              React.createElement("div", {
                style: {
                  background: "#f9f9f9", borderRadius: "8px", padding: "12px",
                  marginBottom: "12px", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center"
                }
              },
                React.createElement("select", {
                  value: addMembershipUserId,
                  onChange: (e) => setAddMembershipUserId(e.target.value),
                  style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px", flex: "1", minWidth: "150px" }
                },
                  React.createElement("option", { value: "" }, "Select user…"),
                  availableUsers.map((u) =>
                    React.createElement("option", { key: u.user_id, value: u.user_id }, u.display_name)
                  )
                ),
                React.createElement("select", {
                  value: addMembershipRole,
                  onChange: (e) => setAddMembershipRole(e.target.value),
                  style: { padding: "6px 10px", borderRadius: "6px", border: "1px solid #ddd", fontSize: "13px" }
                },
                  React.createElement("option", { value: "viewer" }, "Viewer"),
                  React.createElement("option", { value: "analyst" }, "Analyst"),
                  React.createElement("option", { value: "reviewer" }, "Reviewer"),
                  React.createElement("option", { value: "admin" }, "Admin"),
                  React.createElement("option", { value: "owner" }, "Owner"),
                ),
                React.createElement("button", {
                  onClick: handleAddMembership, disabled: !addMembershipUserId,
                  style: {
                    padding: "6px 12px", borderRadius: "6px", border: "none",
                    background: !addMembershipUserId ? "#ccc" : "#3b82f6", color: "#fff",
                    cursor: !addMembershipUserId ? "default" : "pointer", fontSize: "13px"
                  }
                }, "Add to Workspace")
              ),

              memberships.length === 0 && React.createElement("div", { style: { textAlign: "center", padding: "20px", color: "#888", fontSize: "13px" } }, "No memberships."),

              memberships.length > 0 && React.createElement("div", { style: { overflowX: "auto" } },
                React.createElement("table", { style: { width: "100%", fontSize: "13px", borderCollapse: "collapse" } },
                  React.createElement("thead", null,
                    React.createElement("tr", { style: { borderBottom: "2px solid #eee" } },
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "User ID"),
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "Role"),
                      React.createElement("th", { style: { textAlign: "left", padding: "8px" } }, "Joined"),
                      React.createElement("th", { style: { textAlign: "right", padding: "8px" } }, "Actions"),
                    )
                  ),
                  React.createElement("tbody", null,
                    memberships.map((m) =>
                      React.createElement("tr", {
                        key: m.user_id,
                        style: { borderBottom: "1px solid #f0f0f0" }
                      },
                        React.createElement("td", { style: { padding: "8px" } }, m.user_id),
                        React.createElement("td", { style: { padding: "8px" } }, m.role),
                        React.createElement("td", { style: { padding: "8px", color: "#888", fontSize: "12px" } },
                          m.joined_at ? new Date(m.joined_at).toLocaleDateString() : "—"
                        ),
                        React.createElement("td", { style: { padding: "8px", textAlign: "right" } },
                          m.user_id !== "local/system" && React.createElement("button", {
                            onClick: () => handleRemoveMembership(m.user_id),
                            style: {
                              padding: "4px 8px", borderRadius: "4px", border: "1px solid #e74c3c",
                              background: "#fff", color: "#e74c3c", cursor: "pointer", fontSize: "12px"
                            }
                          }, "Remove")
                        )
                      )
                    )
                  )
                )
              )
            )
        )
      ),

      // === Audit Log Tab ===
      tab === "audit" && React.createElement(AuditLogPage, { workspaceId, onNavigate })
    )
  );
}

export default SettingsPage;
