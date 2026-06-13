// App.jsx — Root component
import React, { useState, useCallback, useEffect, useRef } from "react";
import { ReactFlowProvider, useReactFlow } from "reactflow";
import WorkflowCanvas from "./components/WorkflowCanvas";
import WorkflowToolbar from "./components/WorkflowToolbar";
import NodePalette from "./components/NodePalette";
import ConfigPanel from "./components/ConfigPanel";
import ExecutionPanel from "./components/ExecutionPanel";
import ExecutionHistory from "./components/ExecutionHistory";
import ExecutionCompare from "./components/ExecutionCompare";
import ScheduleManager from "./components/ScheduleManager";
import ProviderManager from "./components/ProviderManager";
import NodeComponent from "./components/NodeComponent";
import { ToastProvider, useToast } from "./components/Toast";
import {
  fetchNodeTypes,
  listWorkflows,
  getWorkflow,
  saveWorkflow,
  executeWorkflow,
  streamExecutionEvents,
  listExecutionHistory,
} from "./api";
import { getNodeCategoryConfig } from "./nodeTypes";
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
  const [nodeStatuses, setNodeStatuses] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const { showToast } = useToast();
  const timerRef = useRef(null);

  // Load node types and workflows on mount
  useEffect(() => {
    fetchNodeTypes().then(setNodeTypes).catch(() => {});
    listWorkflows().then(setWorkflows).catch(() => {});
  }, []);

  // Build custom node type map for React Flow
  const nodeTypeMap = { custom: NodeComponent };

  function getNodeTypeInfo(type) {
    return nodeTypes.find((nt) => nt.type === type);
  }

  function workflowToReactNodes(wf) {
    return wf.nodes.map((n, i) => {
      const nt = getNodeTypeInfo(n.type);
      const cat = nt?.categories?.[0] || "flow";
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

  function handleShowHistory() {
    setHistoryPanel(!historyPanel);
    setExecutionPanel(false);
    setSchedulePanel(false);
    setProviderPanel(false);
    setCompareRuns(null);
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

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const data = event.dataTransfer.getData("application/json");
      if (!data) return;

      try {
        const nt = JSON.parse(data);
        const cat = nt.categories?.[0] || "flow";
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

  return (
    <div className="app-layout">
      <WorkflowToolbar
        onNew={handleNew}
        onSave={handleSave}
        onLoad={handleLoad}
        onExecute={handleExecute}
        onExport={handleExport}
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
        schedulePanel={schedulePanel}
        providerPanel={providerPanel}
        workflows={workflows}
        currentWorkflowName={currentWorkflowName}
        isExecuting={isExecuting}
        hasUnsavedChanges={hasUnsavedChanges}
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
        />
        {compareRuns ? (
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
          />
        ) : schedulePanel ? (
          <ScheduleManager
            workflowId={currentWorkflowId}
            onClose={() => setSchedulePanel(false)}
          />
        ) : providerPanel ? (
          <ProviderManager onClose={() => setProviderPanel(false)} />
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
      </div>
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
