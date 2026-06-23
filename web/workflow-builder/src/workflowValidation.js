/**
 * workflowValidation.js — Pre-run workflow validation
 *
 * Validates a workflow before execution and returns errors and warnings.
 * Frontend validation is the first safety layer; backend also validates.
 */

import { getNodeCatalogEntry } from "./nodeTypes";

/**
 * Validate a workflow definition.
 *
 * @param {object} workflow - Workflow with { nodes, edges/connections }
 * @param {Array} nodeTypes - Node type definitions from the API
 * @returns {{ valid: boolean, errors: Array, warnings: Array, node_errors: object, node_warnings: object }}
 */
export function validateWorkflow(workflow, nodeTypes) {
  const errors = [];
  const warnings = [];
  const nodeErrors = {};
  const nodeWarnings = {};
  const nodes = workflow.nodes || [];
  const connections = workflow.connections || workflow.edges || [];

  // Build lookup maps
  const nodeMap = {};
  for (const n of nodes) {
    nodeMap[n.id] = n;
  }

  const typeMap = {};
  for (const nt of nodeTypes) {
    typeMap[nt.type] = nt;
  }

  // 1. Check for at least one start/trigger node
  const triggerNodes = nodes.filter((n) => {
    const nt = typeMap[n.type];
    if (!nt) return false;
    const cat = nt.categories?.[0];
    return cat === "core" || cat === "trigger";
  });

  if (triggerNodes.length === 0) {
    errors.push("No Start node found. Add a Start or trigger node to begin the workflow.");
  }

  // 2. Check for disconnected nodes
  const connectedNodeIds = new Set();
  for (const conn of connections) {
    connectedNodeIds.add(conn.source || conn.source_node);
    connectedNodeIds.add(conn.target || conn.target_node);
  }

  for (const n of nodes) {
    if (!connectedNodeIds.has(n.id) && triggerNodes.some((t) => t.id !== n.id)) {
      warnings.push(
        `Node "${n.label || n.id}" is not connected to any other node.`
      );
      nodeWarnings[n.id] = nodeWarnings[n.id] || [];
      nodeWarnings[n.id].push("Not connected to any other node.");
    }
  }

  // 3. Check required fields per node
  for (const n of nodes) {
    const catalogEntry = getNodeCatalogEntry(n.type);
    if (!catalogEntry) continue;

    const config = n.config || {};
    const missingRequired = catalogEntry.required_fields.filter(
      (field) => !config[field] && config[field] !== false
    );

    if (missingRequired.length > 0) {
      const msg = `Node "${n.label || n.id}": missing required field(s): ${missingRequired.join(", ")}`;
      errors.push(msg);
      nodeErrors[n.id] = nodeErrors[n.id] || [];
      nodeErrors[n.id].push(`Missing required field: ${missingRequired.join(", ")}`);
    }

    // 4. Check provider requirement
    if (catalogEntry.provider_required) {
      warnings.push(
        `Node "${n.label || n.id}" requires an AI provider. Ensure a provider is configured.`
      );
      nodeWarnings[n.id] = nodeWarnings[n.id] || [];
      nodeWarnings[n.id].push("Requires AI provider.");
    }

    // 5. Check safety warnings
    if (catalogEntry.safety_warning) {
      const msg = catalogEntry.safety_warning;
      if (msg.includes("DISABLED") || msg.includes("DANGER")) {
        errors.push(`Node "${n.label || n.id}": ${msg}`);
        nodeErrors[n.id] = nodeErrors[n.id] || [];
        nodeErrors[n.id].push(msg);
      } else {
        warnings.push(`Node "${n.label || n.id}": ${msg}`);
        nodeWarnings[n.id] = nodeWarnings[n.id] || [];
        nodeWarnings[n.id].push(msg);
      }
    }
  }

  // 6. Check workspace_id missing for core evidence/verification nodes
  for (const n of nodes) {
    const cat = typeMap[n.type];
    if (!cat) continue;
    const config = n.config || {};
    const needsWorkspace = ["evidence_search", "verify_claims", "claim_verifier_v2"].some(
      (t) => n.type.includes(t)
    );
    if (needsWorkspace && !config.workspace_id) {
      warnings.push(
        `Node "${n.label || n.id}" may need a workspace_id for full functionality.`
      );
      nodeWarnings[n.id] = nodeWarnings[n.id] || [];
      nodeWarnings[n.id].push("workspace_id not set.");
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    node_errors: nodeErrors,
    node_warnings: nodeWarnings,
  };
}

/**
 * Quick check if workflow can be executed (no blocking errors).
 */
export function canExecute(validation) {
  return validation.valid;
}
