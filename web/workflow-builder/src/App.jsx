// App.jsx — Root component
import React, { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { ReactFlowProvider, useReactFlow } from "reactflow";
import WorkflowCanvas from "./components/WorkflowCanvas";
import WorkflowToolbar from "./components/WorkflowToolbar";
import NodePalette from "./components/NodePalette";
import ConfigPanel from "./components/ConfigPanel";
import ExecutionPanel from "./components/ExecutionPanel";
import TrustDashboard from "./components/TrustDashboard";
import ExecutionHistory from "./components/ExecutionHistory";
import ExecutionCompare from "./components/ExecutionCompare";
import WorkflowDiff from "./components/WorkflowDiff";
import ScheduleManager from "./components/ScheduleManager";
import ProviderManager from "./components/ProviderManager";
import TemplateDialog from "./components/TemplateDialog";
import NodeComponent from "./components/NodeComponent";
import ResizablePanel from "./components/ResizablePanel";
import ShortcutsHelp from "./components/ShortcutsHelp";
import ValidationDialog from "./components/ValidationDialog";
import OnboardingPanel from "./components/OnboardingPanel";
import { ToastProvider, useToast } from "./components/Toast";
import useKeyboardShortcuts from "./hooks/useKeyboardShortcuts";
import {
  fetchNodeTypes,
  listWorkflows,
  getWorkflow,
  saveWorkflow,
  executeWorkflow,
  streamExecutionEvents,
  streamReplayEvents,
  listExecutionHistory,
  listWorkflowVersions,
  getWorkflowVersion,
} from "./api";
import { getNodeCategoryConfig } from "./nodeTypes";
import { validateWorkflow } from "./workflowValidation";
import "./App.css";

const ERROR_POLICIES = ["fail_workflow", "fail_node", "retry", "skip"];

const initialNodes = [];
const initialEdges = [];

function idGen() {
  return `node-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function CanvasInner() {
  const reactFlow = useReactFlow();
  const { nodes, setNodes, edges, setEdges, onNodesChange, onEdgesChange } =
    useWorkflowState();

  const [nodeTypes, setNodeTypes] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [currentWorkflowId, setCurrentWorkflowId] = useState(null);
  const [currentWorkflowName, setCurrentWorkflowName] = useState("Untitled Workflow");
  const [selectedNode, setSelectedNode] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionPanel, setExecutionPanel] = useState(false);
  const [historyPanel, setHistoryPanel] = useState(false);
  const [compareRuns, setCompareRuns] = useState(null);
  const [schedulePanel, setSchedulePanel] = useState(false);
  const [providerPanel, setProviderPanel] = useState(false);
  const [trustPanel, setTrustPanel] = useState(false);
  const [nodeStatuses, setNodeStatuses] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [lastExecutionId, setLastExecutionId] = useState(null);
  const [editReplayNodeId, setEditReplayNodeId] = useState(null);
  const [dirtyAfterExecution, setDirtyAfterExecution] = useState(false);
  const [diffView, setDiffView] = useState(null);
  const [shortcutsHelpOpen, setShortcutsHelpOpen] = useState(false);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [showValidationDialog, setShowValidationDialog] = useState(false);
  const { showToast } = useToast();
  const timerRef = useRef(null);

  // Load node types and workflows on mount
  useEffect(() => {
    fetchNodeTypes().then(setNodeTypes).catch(() => {});
    listWorkflows().then(setWorkflows).catch(() => {});
  }, []);

  // Apply theme on mount from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("wfBuilderTheme");
      if (stored === "dark" || stored === "light") {
        document.documentElement.dataset.theme = stored;
      }
    } catch {
      // localStorage unavailable
    }
  }, []);

  // Build custom node type map for React Flow
  const nodeTypeMap = { custom: NodeComponent };

  function getNodeTypeInfo(type) {
    return nodeTypes.find((nt) => nt.type === type);
  }

  function workflowToReactNodes(wf) {
    return wf.nodes.map((n, i) => {
      const nt = getNodeTypeInfo(n.type);
      const cat = nt?.categories?.[0] || "utility";
      const inputPorts = nt
        ? Object.keys(nt.input_schema?.properties || {})
        : [];
      const outputPorts = nt
        ? Object.keys(nt.output_schema?.properties || {})
        : [];
      return {
        id: n.id,
        type: "custom",
        position: { x: n.position_x || 200, y: n.position_y || 100 + i * 120 },
        data: {
          label: n.label,
          typeLabel: nt?.label || n.type,
          category: cat,
          config: n.config || {},
          inputPorts,
          outputPorts,
          status: "idle",
        },
      };
    });
  }

  function reactEdgesToConnections(es) {
    return es.map((e) => ({
      source_node: e.source,
      source_output: e.sourceHandle || "default",
      target_node: e.target,
      target_input: e.targetHandle || "default",
    }));
  }

  function findDownstreamNodes(nodeId, edgeList) {
    const adjacency = {};
    (edgeList || []).forEach(e => {
      const src = e.source || e.source_node;
      const tgt = e.target || e.target_node;
      if (!adjacency[src]) adjacency[src] = [];
      adjacency[src].push(tgt);
    });

    const visited = new Set();
    const queue = [nodeId];
    while (queue.length > 0) {
      const current = queue.shift();
      if (visited.has(current)) continue;
      visited.add(current);
      const neighbors = adjacency[current] || [];
      neighbors.forEach(n => {
        if (!visited.has(n)) queue.push(n);
      });
    }
    return Array.from(visited);
  }

  function handleNew() {
    setNodes([]);
    setEdges([]);
    setCurrentWorkflowId(null);
    setCurrentWorkflowName("Untitled Workflow");
    setSelectedNode(null);
    setExecutionPanel(false);
    setHasUnsavedChanges(false);
  }

  async function handleSave() {
    try {
      const wf = {
        id: currentWorkflowId || `wf-${Date.now()}`,
        name: currentWorkflowName,
        description: "",
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.data.typeLabel
            ? nodeTypes.find((nt) => nt.label === n.data.typeLabel)?.type ||
              "decision_system.trigger_manual"
            : "decision_system.trigger_manual",
          label: n.data.label,
          config: n.data.config || {},
          error_policy: n.data.config?.error_policy || "fail_workflow",
          position_x: n.position?.x || 0,
          position_y: n.position?.y || 0,
        })),
        connections: reactEdgesToConnections(edges),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      const saved = await saveWorkflow(wf);
      setCurrentWorkflowId(saved.id);
      setHasUnsavedChanges(false);
      showToast("Workflow saved", "success");
      listWorkflows().then(setWorkflows);
    } catch (err) {
      showToast(`Save failed: ${err.message}`, "error");
    }
  }

  async function handleLoad(id) {
    try {
      const wf = await getWorkflow(id);
      setCurrentWorkflowId(wf.id);
      setCurrentWorkflowName(wf.name);
      setSelectedNode(null);
      setExecutionPanel(false);

      const rn = workflowToReactNodes(wf);
      const re = (wf.connections || []).map((c) => ({
        id: `${c.source_node}-${c.target_node}`,
        source: c.source_node,
        target: c.target_node,
        sourceHandle: c.source_output,
        targetHandle: c.target_input,
      }));

      setNodes(rn);
      setEdges(re);
      setHasUnsavedChanges(false);
      showToast(`Loaded: ${wf.name}`, "info");
    } catch (err) {
      showToast(`Load failed: ${err.message}`, "error");
    }
  }

  function handleValidate() {
    const result = validateWorkflow(
      { nodes: nodes, connections: edges },
      nodeTypes
    );
    setValidationResult(result);
    setShowValidationDialog(true);
    if (result.valid) {
      showToast("Workflow is valid - no errors found", "success");
    } else {
      showToast(
        `Validation: ${result.errors.length} error(s), ${result.warnings.length} warning(s)`,
        result.errors.length > 0 ? "error" : "warning"
      );
    }
  }

  async function handleExecute() {

    if (nodes.length === 0) {
      showToast("Add at least one node to the workflow", "warning");
      return;
    }
    if (!currentWorkflowId) {
      await handleSave();
    }

    setIsExecuting(true);
    setExecutionPanel(true);
    setWorkflowStatus("running");
    setElapsed(0);

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed((Date.now() - startTime) / 1000);
    }, 100);

    const initialStatuses = nodes.map((n) => ({
      nodeId: n.id,
      label: n.data.label,
      status: "pending",
    }));
    setNodeStatuses(initialStatuses);

    try {
      const execState = await executeWorkflow(currentWorkflowId);
      setLastExecutionId(execState.execution_id);
      setEditReplayNodeId(null);
      setDirtyAfterExecution(false);

      // Subscribe to events (WebSocket in real mode, simulated in mock mode)
      const unsub = streamExecutionEvents(execState.execution_id, (event) => {
        // Handle terminal workflow events
        if (event.event_type === "workflow_completed") {
          clearInterval(timerRef.current);
          setIsExecuting(false);
          setWorkflowStatus("completed");
          return;
        }
        if (event.event_type === "workflow_failed") {
          clearInterval(timerRef.current);
          setIsExecuting(false);
          setWorkflowStatus("failed");
          return;
        }

        // Update per-node statuses
        setNodeStatuses((prev) => {
          const updated = [...prev];
          const idx = updated.findIndex((n) => n.nodeId === event.node_id);
          if (idx >= 0) {
            const statusMap = {
              node_started: "running",
              node_completed: "completed",
              node_failed: "failed",
            };
            const newStatus = statusMap[event.event_type] || updated[idx].status;
            // Use event duration when available, otherwise compute from start
            const dur = event.data?.duration ?? (
              event.event_type === "node_completed"
                ? (Date.now() - startTime) / 1000
                : updated[idx].duration
            );
            updated[idx] = {
              ...updated[idx],
              status: newStatus,
              duration: dur,
              inputs: event.data?.inputs ?? updated[idx].inputs,
              outputs: event.data?.outputs ?? updated[idx].outputs,
              error: event.data?.error,
            };
          }

          // Update node status on canvas
          if (event.node_id) {
            const canvasStatusMap = {
              node_started: "running",
              node_completed: "completed",
              node_failed: "failed",
            };
            const cs = canvasStatusMap[event.event_type];
            if (cs) {
              setNodes((nds) =>
                nds.map((n) =>
                  n.id === event.node_id
                    ? { ...n, data: { ...n.data, status: cs } }
                    : n
                )
              );
            }
          }
          return updated;
        });
      });

      // Safety fallback: stop checking after 60s
      setTimeout(() => {
        if (isExecuting) {
          clearInterval(timerRef.current);
          setIsExecuting(false);
          setWorkflowStatus("completed");
          unsub();
        }
      }, 60000);
    } catch (err) {
      clearInterval(timerRef.current);
      setIsExecuting(false);
      setWorkflowStatus("failed");
      showToast(`Execution failed: ${err.message}`, "error");
    }
  }

  function handleEditNode(nodeId) {
    setEditReplayNodeId(nodeId);
    // Select the node to open its config panel
    const node = nodes.find((n) => n.id === nodeId);
    if (node) setSelectedNode(node);
  }

  async function handleReplayFrom(nodeId) {
    if (!lastExecutionId) {
      showToast("No execution to replay from", "warning");
      return;
    }

    // Find all downstream nodes
    const downstream = findDownstreamNodes(nodeId, edges);
    if (downstream.length === 0) {
      showToast("No downstream nodes to replay", "warning");
      return;
    }

    setEditReplayNodeId(null);
    setDirtyAfterExecution(false);

    // Reset downstream node statuses
    setNodeStatuses((prev) =>
      prev.map((n) =>
        downstream.includes(n.nodeId)
          ? { ...n, status: "pending", outputs: null, error: null, duration: undefined }
          : n
      )
    );

    setIsExecuting(true);
    setWorkflowStatus("running");

    const replayStart = Date.now();
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsed((Date.now() - replayStart) / 1000);
    }, 100);

    // Subscribe to filtered events for downstream nodes only
    const unsub = streamReplayEvents(lastExecutionId, downstream, (event) => {
      if (event.event_type === "workflow_completed") {
        clearInterval(timerRef.current);
        setIsExecuting(false);
        setWorkflowStatus("completed");
        showToast("Replay completed", "success");
        return;
      }
      if (event.event_type === "workflow_failed") {
        clearInterval(timerRef.current);
        setIsExecuting(false);
        setWorkflowStatus("failed");
        showToast("Replay failed", "error");
        return;
      }

      setNodeStatuses((prev) => {
        const updated = [...prev];
        const idx = updated.findIndex((n) => n.nodeId === event.node_id);
        if (idx >= 0) {
          const statusMap = {
            node_started: "running",
            node_completed: "completed",
            node_failed: "failed",
          };
          const newStatus = statusMap[event.event_type] || updated[idx].status;
          const dur =
            event.data?.duration ??
            (event.event_type === "node_completed"
              ? (Date.now() - replayStart) / 1000
              : updated[idx].duration);
          updated[idx] = {
            ...updated[idx],
            status: newStatus,
            duration: dur,
            inputs: event.data?.inputs ?? updated[idx].inputs,
            outputs: event.data?.outputs ?? updated[idx].outputs,
            error: event.data?.error,
          };
        }

        if (event.node_id) {
          const canvasStatusMap = {
            node_started: "running",
            node_completed: "completed",
            node_failed: "failed",
          };
          const cs = canvasStatusMap[event.event_type];
          if (cs) {
            setNodes((nds) =>
              nds.map((n) =>
                n.id === event.node_id
                  ? { ...n, data: { ...n.data, status: cs } }
                  : n
              )
            );
          }
        }
        return updated;
      });
    });

    // Safety fallback
    setTimeout(() => {
      if (isExecuting) {
        clearInterval(timerRef.current);
        setIsExecuting(false);
        setWorkflowStatus("completed");
        unsub();
      }
    }, 60000);
  }

  function handleShowHistory() {
    setHistoryPanel(!historyPanel);
    setExecutionPanel(false);
    setSchedulePanel(false);
    setProviderPanel(false);
    setCompareRuns(null);
  }

  const handleZoomToFit = useCallback(() => {
    if (reactFlow && reactFlow.fitView) {
      reactFlow.fitView({ padding: 0.2, duration: 300 });
    }
  }, [reactFlow]);

  function handleToggleShortcuts() {
    setShortcutsHelpOpen((prev) => !prev);
  }

  function handleImport() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target?.result);
          if (!data.nodes || !data.connections) {
            throw new Error("Invalid workflow JSON: missing nodes or connections");
          }
          // Convert imported connections to edges
          const importConnections = data.connections.map((c, idx) => ({
            id: `edge-import-${idx}`,
            source: c.source_node || c.source,
            target: c.target_node || c.target,
            sourceHandle: c.source_output || null,
            targetHandle: c.target_input || null,
          }));
          // Convert imported nodes to react-flow format
          const importNodes = data.nodes.map((n) => {
            const nt = nodeTypes.find((t) => t.type === n.type);
            const cat = nt?.categories?.[0] || "utility";
            return {
              id: n.id || `node-import-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              type: "custom",
              position: { x: n.position_x || 200, y: n.position_y || 100 },
              data: {
                label: n.label || n.type,
                typeLabel: nt?.label || n.type,
                category: cat,
                config: n.config || {},
                inputPorts: nt ? Object.keys(nt.input_schema?.properties || {}) : [],
                outputPorts: nt ? Object.keys(nt.output_schema?.properties || {}) : [],
              },
            };
          });
          setNodes(importNodes);
          setEdges(importConnections);
          setCurrentWorkflowName(data.name || "Imported Workflow");
          setHasUnsavedChanges(true);
          showToast(`Imported workflow: "${data.name || "Untitled"}" with ${importNodes.length} nodes`, "success");
        } catch (err) {
          showToast("Import failed: " + err.message, "error");
        }
      };
      reader.readAsText(file);
    };
    input.click();
  }


  function handleExport() {
    const data = {
      name: currentWorkflowName,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data.typeLabel
          ? nodeTypes.find((nt) => nt.label === n.data.typeLabel)?.type || "unknown"
          : "unknown",
        label: n.data.label,
        config: n.data.config,
      })),
      connections: reactEdgesToConnections(edges),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentWorkflowName.replace(/\s+/g, "-").toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleApplyTemplate(template) {
    const idMap = {};
    const freshNodes = template.nodes.map((n) => {
      const newId = idGen();
      idMap[n.id] = newId;
      const nt = getNodeTypeInfo(n.type);
      const cat = nt?.categories?.[0] || "utility";
      const inputPorts = nt
        ? Object.keys(nt.input_schema?.properties || {})
        : [];
      const outputPorts = nt
        ? Object.keys(nt.output_schema?.properties || {})
        : [];
      return {
        id: newId,
        type: "custom",
        position: { x: n.position_x || 100, y: n.position_y || 100 },
        data: {
          label: n.label || nt?.label || n.type,
          typeLabel: nt?.label || n.type,
          category: cat,
          icon: nt?.icon,
          color: nt?.color,
          description: nt?.description,
          config: n.config || {},
          inputPorts,
          outputPorts,
          status: "idle",
        },
      };
    });

    const freshEdges = template.connections.map((c) => ({
      id: `${idMap[c.source_node]}-${idMap[c.target_node]}`,
      source: idMap[c.source_node],
      target: idMap[c.target_node],
      sourceHandle: c.source_output || "default",
      targetHandle: c.target_input || "default",
    }));

    setNodes(freshNodes);
    setEdges(freshEdges);
    setCurrentWorkflowId(null);
    setCurrentWorkflowName(template.name);
    setHasUnsavedChanges(true);
    setSelectedNode(null);
    setTemplateDialogOpen(false);
    showToast(`Loaded template: ${template.name}`, "info");
  }

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const data = event.dataTransfer.getData("application/json");
      if (!data) return;

      try {
        const nt = JSON.parse(data);
        const cat = nt.categories?.[0] || "utility";
        const position = reactFlow.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
        const newNode = {
          id: idGen(),
          type: "custom",
          position,
          data: {
            label: nt.label,
            typeLabel: nt.label,
            category: cat,
            icon: nt.icon,
            color: nt.color,
            description: nt.description,
            config: {},
            inputPorts: Object.keys(nt.input_schema?.properties || {}),
            outputPorts: Object.keys(nt.output_schema?.properties || {}),
            status: "idle",
          },
        };
        setNodes((nds) => [...nds, newNode]);
        setHasUnsavedChanges(true);
      } catch {
        // ignore invalid drops
      }
    },
    [reactFlow, setNodes]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  function handleNodeClick(_, node) {
    setSelectedNode(node);
  }

  function handlePaneClick() {
    setSelectedNode(null);
  }

  function handleUpdateConfig(nodeId, config) {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, config } } : n
      )
    );
    setHasUnsavedChanges(true);
    if (lastExecutionId) setDirtyAfterExecution(true);
  }

  function handleUpdateLabel(nodeId, label) {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, label } } : n))
    );
    setHasUnsavedChanges(true);
  }

  function handleDeleteNode(nodeId) {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
    setHasUnsavedChanges(true);
  }

  // Derive selected node type info
  const selectedNodeTypeInfo = selectedNode
    ? nodeTypes.find((nt) => nt.label === selectedNode.data.typeLabel) || null
    : null;

  // Derive execution-aware edge IDs for animated canvas edges
  const executingEdgeIds = useMemo(() => {
    if (!nodeStatuses || nodeStatuses.length === 0) return new Set();
    const activeNodeIds = new Set(
      nodeStatuses
        .filter((ns) => ns.status === "running" || ns.status === "completed")
        .map((ns) => ns.nodeId)
    );
    return new Set(
      edges
        .filter((e) => activeNodeIds.has(e.source) || activeNodeIds.has(e.target))
        .map((e) => e.id)
    );
  }, [nodeStatuses, edges]);

  // Connection handler
  const onConnect = useCallback(
    (params) => {
      setEdges((eds) => [...eds, { ...params, id: `${params.source}-${params.target}` }]);
      setHasUnsavedChanges(true);
    },
    [setEdges]
  );

  // Track changes
  useEffect(() => {
    if (currentWorkflowId && !hasUnsavedChanges) setHasUnsavedChanges(true);
  }, [nodes, edges, currentWorkflowId, hasUnsavedChanges]);

  // Keyboard shortcuts
  const shortcutHandlers = useMemo(
    () => ({
      "ctrl+s": () => handleSave(),
      "delete": () => {
        if (selectedNode) handleDeleteNode(selectedNode.id);
      },
      "backspace": () => {
        if (selectedNode) handleDeleteNode(selectedNode.id);
      },
      "escape": () => {
        setSelectedNode(null);
        setExecutionPanel(false);
        setSchedulePanel(false);
        setProviderPanel(false);
        setShortcutsHelpOpen(false);
      },
      "space": () => {
        if (!isExecuting) handleExecute();
      },
      "shift+?": () => {
        setShortcutsHelpOpen((prev) => !prev);
      },
      "ctrl+shift+e": () => handleExport(),
    }),
    [handleSave, selectedNode, handleDeleteNode, isExecuting, handleExecute, handleExport]
  );

  useKeyboardShortcuts(shortcutHandlers);

  return (
    <div className="app-layout">
      <WorkflowToolbar
        onNew={handleNew}
        onSave={handleSave}
        onLoad={handleLoad}
        onExecute={handleExecute}
        onValidate={handleValidate}
        validationResult={validationResult}
        showValidationDialog={showValidationDialog}
        setShowValidationDialog={setShowValidationDialog}
        onExport={handleExport}
        onImport={handleImport}

        onHistory={handleShowHistory}
        historyPanel={historyPanel}
        onSchedules={() => {
          setSchedulePanel(!schedulePanel);
          setExecutionPanel(false);
          setProviderPanel(false);
          setHistoryPanel(false);
        }}
        onProviders={() => {
          setProviderPanel(!providerPanel);
          setSchedulePanel(false);
          setExecutionPanel(false);
          setHistoryPanel(false);
        }}
        onTemplates={() => setTemplateDialogOpen(true)}
        onTrust={() => {
          setTrustPanel(!trustPanel);
          setSchedulePanel(false);
          setExecutionPanel(false);
          setProviderPanel(false);
          setHistoryPanel(false);
        }}
        schedulePanel={schedulePanel}
        providerPanel={providerPanel}
        trustPanel={trustPanel}
        workflows={workflows}
        currentWorkflowName={currentWorkflowName}
        isExecuting={isExecuting}
        hasUnsavedChanges={hasUnsavedChanges}
        onShortcuts={handleToggleShortcuts}
      />
      <div className="app-main">
        <NodePalette nodeTypes={nodeTypes} onDragStart={() => {}} />
        <WorkflowCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypeMap}
          onZoomToFit={handleZoomToFit}
          executingEdgeIds={executingEdgeIds}
        />
        <ResizablePanel initialWidth={380} minWidth={280} maxWidth={900}>
          {diffView ? (
            <WorkflowDiff
              workflowA={diffView.workflowA}
              workflowB={diffView.workflowB}
              onClose={() => setDiffView(null)}
            />
          ) : compareRuns ? (
            <ExecutionCompare
              runIdA={compareRuns.runIdA}
              runIdB={compareRuns.runIdB}
              onClose={() => setCompareRuns(null)}
            />
          ) : historyPanel ? (
            <ExecutionHistory
              onClose={() => {
                setHistoryPanel(false);
              }}
              onSelectRun={(id) => {}}
              onCompare={(idA, idB) => setCompareRuns({ runIdA: idA, runIdB: idB })}
              onCompareVersions={async () => {
                if (currentWorkflowId) {
                  try {
                    const versions = await listWorkflowVersions(currentWorkflowId);
                    if (versions.length >= 2) {
                      setDiffView({
                        workflowA: versions[0],
                        workflowB: versions[versions.length - 1],
                      });
                      setHistoryPanel(false);
                    } else {
                      showToast("Need at least 2 versions to compare", "warning");
                    }
                  } catch {
                    showToast("Failed to load versions", "error");
                  }
                }
              }}
            />
          ) : executionPanel ? (
            <ExecutionPanel
              nodeStatuses={nodeStatuses}
              workflowStatus={workflowStatus}
              elapsed={elapsed}
              onClose={() => {
                setExecutionPanel(false);
                setWorkflowStatus(null);
              }}
              onEditNode={handleEditNode}
              onReplayFrom={handleReplayFrom}
              editReplayNodeId={editReplayNodeId}
            />
          ) : schedulePanel ? (
            <ScheduleManager
              workflowId={currentWorkflowId}
              onClose={() => setSchedulePanel(false)}
            />
          ) : providerPanel ? (
            <ProviderManager onClose={() => setProviderPanel(false)} />
          ) : trustPanel ? (
            <TrustDashboard workspaceId="ws-1" onClose={() => setTrustPanel(false)} />
          ) : (
            <ConfigPanel
              selectedNode={selectedNode}
              nodeType={selectedNodeTypeInfo}
              onUpdateConfig={handleUpdateConfig}
              onUpdateLabel={handleUpdateLabel}
              onDelete={handleDeleteNode}
              errorPolicies={ERROR_POLICIES}
            />
          )}
        </ResizablePanel>
      </div>
      <OnboardingPanel onDismiss={() => {}} />

      <ShortcutsHelp
        isOpen={shortcutsHelpOpen}
        onClose={() => setShortcutsHelpOpen(false)}
      />
      <ValidationDialog
        isOpen={showValidationDialog}
        result={validationResult}
        onClose={() => setShowValidationDialog(false)}
      />
      <TemplateDialog
        isOpen={templateDialogOpen}
        onSelect={handleApplyTemplate}
        onClose={() => setTemplateDialogOpen(false)}
      />
    </div>
  );
}

// Workflow state hook (separated to work inside ReactFlowProvider)
function useWorkflowState() {
  const reactFlow = useReactFlow();
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => {
        let updated = [...nds];
        for (const change of changes) {
          if (change.type === "remove") {
            updated = updated.filter((n) => n.id !== change.id);
          }
        }
        return reactFlow.applyNodeChanges(changes, updated);
      });
    },
    [reactFlow]
  );

  const onEdgesChange = useCallback(
    (changes) => {
      setEdges((eds) => reactFlow.applyEdgeChanges(changes, eds));
    },
    [reactFlow]
  );

  return { nodes, setNodes, edges, setEdges, onNodesChange, onEdgesChange };
}

function App() {
  return (
    <ReactFlowProvider>
      <ToastProvider>
        <CanvasInner />
      </ToastProvider>
    </ReactFlowProvider>
  );
}

export default App;
