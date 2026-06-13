// nodeTypes.js — Converts API node types to visual configs

const CATEGORY_CONFIG = {
  trigger: { color: "#3b82f6", bg: "#eff6ff", label: "Triggers", icon: "⚡" },
  data:   { color: "#f59e0b", bg: "#fffbeb", label: "Data", icon: "📊" },
  ai:     { color: "#8b5cf6", bg: "#f5f3ff", label: "AI / Analysis", icon: "🤖" },
  output: { color: "#22c55e", bg: "#f0fdf4", label: "Output", icon: "📄" },
  flow:   { color: "#6b7280", bg: "#f9fafb", label: "Flow Control", icon: "🔀" },
};

function getNodeCategoryConfig(type) {
  const entry = CATEGORY_CONFIG[type];
  return entry || CATEGORY_CONFIG.flow;
}

function getCategories() {
  return Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => ({
    id: key,
    ...cfg,
  }));
}

export { CATEGORY_CONFIG, getNodeCategoryConfig, getCategories };
