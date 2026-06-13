# Phase 4: Scheduling & Triggers — Implementation Plan [COMPLETED 2026-06-13]

> **Status:** All 11 implementation tasks complete. 28 files changed, ~3300 lines added. 68 new tests (916 total). Version bumped to 1.11.0.

**Goal:** Transform the workflow engine from a "run manually" tool into an autonomous automation engine by adding cron-based scheduling, webhook triggers, and file-watch triggers. Workflows can now start automatically without user intervention.

**Architecture:** A lightweight background scheduler runs inside the FastAPI process. It polls a schedule store, evaluates cron expressions, watches filesystem changes, and listens for webhook POSTs — then dispatches executions via the existing `DAGEngine`. Three new trigger node types join the existing ManualTrigger and InputText. The scheduler is a single asyncio task, not a separate process.

**Tech Stack:** Python 3.11+ (asyncio, `croniter` for cron parsing, `watchdog` for file watching), FastAPI, React 18, React Flow 11

---

## File Structure

```
src/decision_system/workflow_engine/
    scheduler/
        __init__.py                       # Exports SchedulerService
        models.py                         # ScheduleDefinition, TriggerType, TriggerConfigs
        store.py                          # ScheduleStore (JSON file persistence)
        scheduler.py                      # Background scheduler loop + lifecycle
        triggers.py                       # CronEvaluator, WebhookHandler, FileWatchHandler
    nodes/builtin/
        trigger_nodes.py                  # MODIFY: add CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode
    api.py                                # MODIFY: add schedule CRUD, webhook receiver
    cli.py                                # MODIFY: add schedule management commands
    stores/
        json_store.py                     # MODIFY: if extending store base
tests/
    test_workflow_engine/
        test_scheduler.py                  # NEW: scheduler unit + integration tests
        test_trigger_nodes.py              # NEW: trigger node execution tests
    test_web_ui.py                         # MODIFY: if nav changes
web/workflow-builder/
    src/
        api.js                             # MODIFY: add schedule + webhook API calls
        mockData.js                        # MODIFY: add 3 new trigger node type definitions
```

---

## Task Dependency Graph

```
Task 1 (scheduler models + store)
    ├──> Task 2 (trigger evaluators)
    │        └──> Task 3 (scheduler loop)
    ├──> Task 4 (trigger node types)
    │        └──> Task 5 (engine integration)
    ├──> Task 6 (schedule API routes)
    ├──> Task 7 (webhook receiver)
    └──> Task 8 (CLI commands)
             └──> Task 9 (integration tests)
    Task 10 (frontend: API + mockData)
              └──> Task 11 (frontend: schedule UI)
    Task 12 (end-to-end test)
```

---

### Task 1: Schedule Models and Store

**Files:**
- Create: `src/decision_system/workflow_engine/scheduler/__init__.py`
- Create: `src/decision_system/workflow_engine/scheduler/models.py`
- Create: `src/decision_system/workflow_engine/scheduler/store.py`

- [ ] **Step 1: Create scheduler package**

```bash
mkdir -p src/decision_system/workflow_engine/scheduler
```

Create `src/decision_system/workflow_engine/scheduler/__init__.py`:
```python
"""Scheduler — cron, webhook, and file-watch triggers for workflow automation."""
from decision_system.workflow_engine.scheduler.scheduler import SchedulerService
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_workflow_engine/test_scheduler.py` with these test classes:

**TestScheduleDefinition:**
- `test_default_fields` — ScheduleDefinition with id + workflow_id only
- `test_cron_trigger` — ScheduleDefinition with trigger_type="cron", trigger_config={"expression": "0 9 * * 1-5"}
- `test_webhook_trigger` — ScheduleDefinition with trigger_type="webhook", trigger_config={"path": "/hooks/my-webhook"}
- `test_file_watch_trigger` — ScheduleDefinition with trigger_type="file_watch", trigger_config={"directory": "company_docs/", "pattern": "*.md"}
- `test_default_enabled` — enabled defaults to True

**TestScheduleStore:**
- `test_save_and_load` — save a schedule, load it back, verify fields match
- `test_list_schedules` — save 3 schedules, list returns all 3
- `test_list_by_workflow` — save schedules for 2 workflows, filter by workflow_id
- `test_list_by_trigger_type` — filter by trigger_type="cron"
- `test_delete` — save then delete, load returns None
- `test_update_last_fired` — update last_fired timestamp, verify on load
- `test_nonexistent_load` — load returns None for unknown id
- `test_list_empty` — fresh store lists 0 schedules
- `test_persist_across_instances` — save in one instance, load in another with same path

- [ ] **Step 3: Implement models.py**

```python
"""Schedule models for workflow triggers."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TriggerType(str, Enum):
    """Supported trigger types."""
    CRON = "cron"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"


class ScheduleDefinition(BaseModel):
    """A schedule that triggers a workflow automatically.
    
    Each schedule links a trigger type + config to a workflow_id.
    Multiple schedules can target the same workflow. A workflow
    can have at most one schedule of type 'webhook' (the webhook
    path is generated and bound to the schedule).
    """
    id: str = Field(default="", description="Unique schedule identifier")
    workflow_id: str = Field(..., description="Workflow to execute")
    trigger_type: TriggerType = Field(..., description="Type of trigger")
    trigger_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Trigger-specific configuration",
    )
    enabled: bool = Field(default=True, description="Whether schedule is active")
    last_fired: datetime | None = Field(default=None, description="Last execution time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 4: Implement store.py**

```python
"""Schedule store — persists schedule definitions as JSON files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from decision_system.workflow_engine.scheduler.models import (
    ScheduleDefinition, TriggerType,
)


class ScheduleStore:
    """JSON file-backed schedule store.
    
    Stores one JSON file per schedule under the configured directory.
    Pattern: <dir>/schedule_<id>.json
    """
    
    def __init__(self, store_dir: str | Path) -> None:
        self._dir = Path(store_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
    
    def _path(self, schedule_id: str) -> Path:
        return self._dir / f"schedule_{schedule_id}.json"
    
    def _all_paths(self) -> list[Path]:
        if not self._dir.exists():
            return []
        return sorted(self._dir.glob("schedule_*.json"))
    
    def save(self, schedule: ScheduleDefinition) -> ScheduleDefinition:
        """Save a schedule. Generates id if missing."""
        if not schedule.id:
            schedule.id = f"sch-{uuid4().hex[:12]}"
        schedule.updated_at = datetime.now(timezone.utc)
        self._path(schedule.id).write_text(
            schedule.model_dump_json(indent=2, default=str)
        )
        return schedule
    
    def load(self, schedule_id: str) -> Optional[ScheduleDefinition]:
        """Load a schedule by id. Returns None if not found."""
        path = self._path(schedule_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return ScheduleDefinition(**data)
    
    def list(
        self,
        workflow_id: Optional[str] = None,
        trigger_type: Optional[TriggerType] = None,
    ) -> list[ScheduleDefinition]:
        """List all schedules, optionally filtered."""
        results = []
        for path in self._all_paths():
            data = json.loads(path.read_text())
            sd = ScheduleDefinition(**data)
            if workflow_id and sd.workflow_id != workflow_id:
                continue
            if trigger_type and sd.trigger_type != trigger_type:
                continue
            results.append(sd)
        return results
    
    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule. Returns True if existed."""
        path = self._path(schedule_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def update_last_fired(self, schedule_id: str, timestamp: datetime) -> None:
        """Update last_fired timestamp without loading the full object."""
        sd = self.load(schedule_id)
        if sd:
            sd.last_fired = timestamp
            self.save(sd)
```

- [ ] **Step 5: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_scheduler.py -k "TestScheduleDefinition or TestScheduleStore"
```

Expected: All model + store tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/scheduler/ tests/test_workflow_engine/test_scheduler.py
git commit -m "feat(scheduler): add schedule definitions and JSON store"
```

---

### Task 2: Trigger Evaluators

**File:**
- Create: `src/decision_system/workflow_engine/scheduler/triggers.py`

The trigger evaluators determine WHEN a trigger should fire:
- **CronEvaluator** — parses cron expression and checks if the workflow should run at the current time window
- **WebhookHandler** — validates incoming webhook requests match a stored webhook schedule
- **FileWatchHandler** — watches a directory for file changes matching a pattern

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_workflow_engine/test_scheduler.py`:

**TestCronEvaluator:**
- `test_every_minute` — `* * * * *` matches current time window
- `test_daily_at_9am` — `0 9 * * *` matches at 09:00, not at 10:00
- `test_weekdays_only` — `0 9 * * 1-5` matches Monday, not Sunday
- `test_no_last_fired` — first evaluation returns True (should fire)
- `test_already_fired_recently` — last_fired within same minute returns False
- `test_invalid_expression` — raises ValueError for bad cron

**TestWebhookHandler:**
- `test_validate_path` — matches correct webhook path
- `test_validate_rejects_wrong_path` — returns False for different path
- `test_validate_with_headers` — optional header validation

**TestFileWatchHandler:**
- `test_snapshot_no_changes` — empty dir returns no new events
- `test_snapshot_new_file` — new file in dir returns one event
- `test_snapshot_pattern_filter` — only matches `*.md` files
- `test_snapshot_nonexistent_dir` — returns empty gracefully

- [ ] **Step 2: Implement triggers.py**

```python
"""Trigger evaluators for cron, webhook, and file-watch triggers."""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _parse_cron(expression: str) -> tuple:
    """Parse a cron expression into minute, hour, day-of-month, month, day-of-week.
    
    Returns a 5-tuple of sets for each field, or -1 for wildcards.
    Raises ValueError on invalid expressions.
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expression!r}. Expected 5 fields.")
    # Simplified parser for common patterns
    parsed = []
    for part in parts:
        if part == "*":
            parsed.append(-1)  # wildcard
        elif part.isdigit():
            parsed.append(int(part))
        else:
            raise ValueError(f"Unsupported cron field: {part!r}. Only * and digits supported.")
    return tuple(parsed)  # (minute, hour, day_of_month, month, day_of_week)


def _cron_matches(expression: str, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression."""
    try:
        minute, hour, dom, month, dow = _parse_cron(expression)
    except ValueError:
        return False
    
    if minute != -1 and dt.minute != minute:
        return False
    if hour != -1 and dt.hour != hour:
        return False
    if dom != -1 and dt.day != dom:
        return False
    if month != -1 and dt.month != month:
        return False
    if dow != -1 and dt.weekday() != dow:  # 0=Monday
        return False
    return True


def evaluate_cron(expression: str, last_fired: Optional[datetime] = None) -> bool:
    """Evaluate whether a cron trigger should fire now.
    
    Returns True if the current time matches the expression AND
    the trigger hasn't already fired in the current minute window.
    """
    now = datetime.now(timezone.utc)
    if not _cron_matches(expression, now):
        return False
    if last_fired is not None:
        # Don't fire again within the same minute
        if (now - last_fired).total_seconds() < 60:
            return False
    return True


def validate_webhook_path(received_path: str, stored_path: str) -> bool:
    """Validate an incoming webhook request path against a stored config."""
    return received_path.rstrip("/") == stored_path.rstrip("/")


def scan_directory(
    directory: str,
    pattern: str = "*",
    known_files: Optional[set[str]] = None,
) -> tuple[set[str], list[str]]:
    """Scan a directory for new files matching a pattern.
    
    Returns (current_files, new_files) tuple.
    known_files is the set of files from the last scan.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return set(), []
    
    current: set[str] = set()
    for entry in dir_path.iterdir():
        if entry.is_file() and fnmatch.fnmatch(entry.name, pattern):
            current.add(entry.name)
    
    if known_files is None:
        return current, []
    
    new_files = [f for f in current if f not in known_files]
    return current, new_files
```

- [ ] **Step 3: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_scheduler.py -k "TestCron or TestWebhook or TestFileWatch"
```

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/scheduler/triggers.py
git commit -m "feat(scheduler): add cron, webhook, and file-watch trigger evaluators"
```

---

### Task 3: Background Scheduler Service

**File:**
- Create: `src/decision_system/workflow_engine/scheduler/scheduler.py`

The scheduler is a long-lived asyncio task that:
1. Loads all enabled schedules from the ScheduleStore
2. For each schedule, evaluates whether it should fire
3. If fired, executes the associated workflow via DAGEngine
4. Updates `last_fired` timestamp
5. Sleeps for 60 seconds, then repeats

A separate poll interval is used for file-watch triggers (every 15 seconds).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_workflow_engine/test_scheduler.py`:

**TestSchedulerService:**
- `test_start_and_stop` — start scheduler, verify it begins polling, stop it
- `test_does_not_fire_disabled_schedule` — disabled schedule is not evaluated
- `test_fires_matching_schedule` — cron matches, schedule fires workflow
- `test_multiple_schedules_same_workflow` — two schedules for same workflow both fire
- `test_last_fired_updated` — verify last_fired is updated after firing

- [ ] **Step 2: Implement scheduler.py**

```python
"""Background scheduler service — runs alongside FastAPI.

The scheduler is an asyncio task that polls all enabled schedules
periodically and executes workflows when triggers match.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.scheduler.models import TriggerType, ScheduleDefinition
from decision_system.workflow_engine.scheduler.store import ScheduleStore
from decision_system.workflow_engine.scheduler.triggers import (
    evaluate_cron, scan_directory,
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background scheduler that polls schedules and fires workflows."""
    
    def __init__(
        self,
        schedule_store: ScheduleStore,
        dag_engine: DAGEngine,
        poll_interval: float = 60.0,
        watch_interval: float = 15.0,
    ) -> None:
        self._store = schedule_store
        self._engine = dag_engine
        self._poll_interval = poll_interval
        self._watch_interval = watch_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        # Track known files per watch schedule for diff detection
        self._known_files: dict[str, set[str]] = {}
    
    async def start(self) -> None:
        """Start the scheduler background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started (poll=%ss, watch=%ss)", 
                     self._poll_interval, self._watch_interval)
    
    async def stop(self) -> None:
        """Stop the scheduler background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped")
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        poll_cycles = 0
        try:
            while self._running:
                try:
                    await self._check_schedules()
                except Exception as exc:
                    logger.error("Scheduler check failed: %s", exc)
                
                poll_cycles += 1
                # File-watch triggers checked more frequently
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass
    
    async def _check_schedules(self) -> None:
        """Check all enabled schedules and fire matching ones."""
        schedules = self._store.list()
        
        for schedule in schedules:
            if not schedule.enabled:
                continue
            
            should_fire = False
            
            if schedule.trigger_type == TriggerType.CRON:
                expression = schedule.trigger_config.get("expression", "")
                if expression:
                    should_fire = evaluate_cron(expression, schedule.last_fired)
            
            elif schedule.trigger_type == TriggerType.FILE_WATCH:
                directory = schedule.trigger_config.get("directory", "")
                pattern = schedule.trigger_config.get("pattern", "*")
                known = self._known_files.get(schedule.id)
                current, new_files = scan_directory(directory, pattern, known)
                self._known_files[schedule.id] = current
                if new_files:
                    should_fire = True
                    # Pass changed files as workflow inputs
                    schedule.trigger_config["_changed_files"] = new_files
            
            # Webhook triggers are handled separately via API route, not here
            
            if should_fire:
                await self._fire(schedule)
    
    async def _fire(self, schedule: ScheduleDefinition) -> None:
        """Execute the workflow associated with a schedule."""
        wf = self._engine.workflow_store.load(schedule.workflow_id)
        if wf is None:
            logger.warning("Schedule %s: workflow %s not found", 
                          schedule.id, schedule.workflow_id)
            return
        
        logger.info("Firing schedule %s -> workflow %s (trigger=%s)",
                    schedule.id, schedule.workflow_id, schedule.trigger_type)
        
        inputs = schedule.trigger_config.get("_changed_files", {})
        state = await self._engine.execute(wf, global_inputs=inputs)
        
        self._store.update_last_fired(schedule.id, datetime.now(timezone.utc))
        
        if state.status == "failed":
            logger.error("Schedule %s: workflow execution failed: %s",
                        schedule.id, state.error)
```

- [ ] **Step 3: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_scheduler.py -k "TestSchedulerService"
```

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/scheduler/scheduler.py
git commit -m "feat(scheduler): add background scheduler service loop"
```

---

### Task 4: Trigger Node Types

**File:**
- Modify: `src/decision_system/workflow_engine/nodes/builtin/trigger_nodes.py`
- Create: `tests/test_workflow_engine/test_trigger_nodes.py`

Add three new built-in node types that serve as workflow entry points for automatic triggers. These nodes don't execute anything at runtime — they simply signal to the scheduler what kind of trigger this workflow needs.

**Design principle:** Trigger nodes are metadata markers for the scheduler. When a workflow is saved, the system scans for trigger nodes and creates/updates corresponding ScheduleDefinition entries. When the workflow actually runs (triggered by the scheduler), these nodes pass through the trigger config as output data.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_trigger_nodes.py`:

**TestCronTriggerNode:**
- `test_type_and_label` — verify type string and label
- `test_execute_returns_schedule_config` — execute returns the cron expression from config
- `test_config_schema` — schema has `expression` field (free text)
- `test_default_expression` — default cron expression is `0 9 * * *`
- `test_input_schema` — no inputs expected

**TestWebhookTriggerNode:**
- `test_type_and_label` — verify type string and label
- `test_execute_returns_path` — execute returns the generated webhook path
- `test_config_schema` — schema has no required fields (path is auto-generated)

**TestFileWatchTriggerNode:**
- `test_type_and_label` — verify type string and label
- `test_execute_returns_directory_and_pattern` — execute returns watched path + pattern
- `test_config_schema` — schema has `directory` and `pattern` fields
- `test_default_pattern` — pattern defaults to `*`

- [ ] **Step 2: Implement trigger_nodes.py additions**

Add to `src/decision_system/workflow_engine/nodes/builtin/trigger_nodes.py`:

```python
class CronTriggerNode(WorkflowNode):
    """Cron trigger — starts a workflow on a time-based schedule.
    
    The scheduler evaluates the cron expression and fires the workflow
    automatically. During manual execution, this node just returns the
    configured schedule info.
    """
    type: str = "decision_system.trigger_cron"
    label: str = "Cron Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        expression = self.config.get("expression", "0 9 * * *")
        return {
            "trigger_type": "cron",
            "expression": expression,
            "triggered": True,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "title": "Cron Expression",
                    "description": "Schedule in cron format: minute hour day-of-month month day-of-week",
                    "default": "0 9 * * *",
                    "examples": [
                        "0 9 * * 1-5",    # Weekdays at 9am
                        "*/30 * * * *",   # Every 30 minutes
                        "0 0 * * *",      # Daily at midnight
                        "0 8 * * 1",      # Mondays at 8am
                    ],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "trigger_type": {"type": "string"},
                "expression": {"type": "string"},
                "triggered": {"type": "boolean"},
            },
        }


class WebhookTriggerNode(WorkflowNode):
    """Webhook trigger — starts a workflow via HTTP POST.
    
    The scheduler registers a unique webhook URL for this node.
    POSTing to the webhook URL triggers the workflow with the
    POST body as workflow inputs.
    """
    type: str = "decision_system.trigger_webhook"
    label: str = "Webhook Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        path = self.config.get("webhook_path", "")
        return {
            "trigger_type": "webhook",
            "webhook_path": path,
            "triggered": True,
            **inputs,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "webhook_path": {
                    "type": "string",
                    "title": "Webhook Path",
                    "description": "Auto-generated unique path for this webhook",
                    "default": "",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "payload": {
                    "type": "object",
                    "title": "Webhook Payload",
                    "description": "JSON body from the webhook POST request",
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "trigger_type": {"type": "string"},
                "webhook_path": {"type": "string"},
                "triggered": {"type": "boolean"},
            },
        }


class FileWatchTriggerNode(WorkflowNode):
    """File Watch trigger — starts a workflow when files change in a directory.
    
    The scheduler monitors the configured directory for new or modified
    files matching the pattern. When detected, it fires the workflow.
    """
    type: str = "decision_system.trigger_file_watch"
    label: str = "File Watch Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        directory = self.config.get("directory", "")
        pattern = self.config.get("pattern", "*")
        changed_files = inputs.get("_changed_files", [])
        return {
            "trigger_type": "file_watch",
            "directory": directory,
            "pattern": pattern,
            "changed_files": changed_files,
            "triggered": True,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "title": "Directory to Watch",
                    "description": "Path to the directory to monitor for file changes",
                    "default": "company_docs/",
                },
                "pattern": {
                    "type": "string",
                    "title": "File Pattern",
                    "description": "Glob pattern for files to watch (e.g. *.md, *.csv)",
                    "default": "*",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "trigger_type": {"type": "string"},
                "directory": {"type": "string"},
                "pattern": {"type": "string"},
                "changed_files": {"type": "array"},
                "triggered": {"type": "boolean"},
            },
        }
```

- [ ] **Step 3: Update the built-in `__init__.py`**

In `src/decision_system/workflow_engine/nodes/builtin/__init__.py`:
```python
from .trigger_nodes import (
    ManualTriggerNode, InputTextNode,
    CronTriggerNode, WebhookTriggerNode, FileWatchTriggerNode,
)
```

- [ ] **Step 4: Register new node types**

In `src/decision_system/workflow_engine/nodes/registry.py`, update `create_default_registry()` to register the three new node types:

```python
registry.register(manual_trigger.ManualTriggerNode)
registry.register(input_text.InputTextNode)
registry.register(trigger_nodes.CronTriggerNode)
registry.register(trigger_nodes.WebhookTriggerNode)
registry.register(trigger_nodes.FileWatchTriggerNode)
```

- [ ] **Step 5: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_trigger_nodes.py
```

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/builtin/trigger_nodes.py tests/test_workflow_engine/test_trigger_nodes.py
git commit -m "feat(workflow): add CronTrigger, WebhookTrigger, FileWatchTrigger nodes"
```

---

### Task 5: Engine Integration — Schedule-Aware Execution

The DAGEngine needs minor changes to support scheduled executions:
- Accept an optional `schedule_id` parameter for provenance tracking
- When a workflow triggered by a schedule completes, update the schedule's `last_fired`

- [ ] **Step 1: Modify `DAGEngine.execute()` to accept optional `schedule_id`**

In `src/decision_system/workflow_engine/engine/executor.py`:

```python
async def execute(
    self,
    workflow: WorkflowDefinition,
    global_inputs: dict[str, Any] | None = None,
    schedule_id: str | None = None,
) -> ExecutionState:
```

Store `schedule_id` in the `ExecutionContext` so nodes can detect if they're running on a schedule vs manually.

- [ ] **Step 2: Update ExecutionContext to include `schedule_id`**

In `src/decision_system/workflow_engine/models.py`:

```python
class ExecutionContext(BaseModel):
    workflow_id: str
    execution_id: str
    schedule_id: str | None = None
    provider: str = "fake"
    global_config: dict[str, Any] = Field(default_factory=dict)
    log: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Write tests for schedule-aware execution**

Add to `tests/test_workflow_engine/test_executor.py`:

**TestScheduleExecution:**
- `test_execute_with_schedule_id` — schedule_id appears in node execution context
- `test_execute_without_schedule_id` — schedule_id is None for manual execution

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/engine/executor.py src/decision_system/workflow_engine/models.py
git commit -m "feat(engine): add schedule-aware execution with schedule_id in context"
```

---

### Task 6: Schedule API Routes

**File:**
- Modify: `src/decision_system/workflow_engine/api.py`

Add CRUD API endpoints for schedules and integrate the scheduler with the FastAPI server lifecycle.

- [ ] **Step 1: Write tests**

Add to `tests/test_workflow_engine/test_api.py` (or create `test_schedule_api.py`):

**TestScheduleAPI:**
- `test_create_schedule` — POST /schedules creates and returns schedule
- `test_list_schedules` — GET /schedules returns all schedules
- `test_get_schedule` — GET /schedules/{id} returns single schedule
- `test_update_schedule` — PUT /schedules/{id} updates fields
- `test_delete_schedule` — DELETE /schedules/{id} removes schedule
- `test_enable_disable_schedule` — PATCH /schedules/{id}/toggle toggles enabled
- `test_get_schedule_404` — GET unknown id returns 404
- `test_schedule_auto_create_on_workflow_save` — saving a workflow with trigger nodes auto-creates schedules

**TestWebhookExecution:**
- `test_webhook_receiver` — POST /webhooks/{path} triggers workflow
- `test_webhook_unknown_path` — POST to unknown path returns 404
- `test_webhook_with_payload` — POST body passed as workflow inputs

- [ ] **Step 2: Implement schedule routes**

Add to `src/decision_system/workflow_engine/api.py`:

```python
@router.get("/schedules")
def list_schedules(...):
    ...

@router.post("/schedules")
def create_schedule(...):
    ...

@router.get("/schedules/{schedule_id}")
def get_schedule(...):
    ...

@router.put("/schedules/{schedule_id}")
def update_schedule(...):
    ...

@router.delete("/schedules/{schedule_id}")
def delete_schedule(...):
    ...

@router.patch("/schedules/{schedule_id}/toggle")
def toggle_schedule(...):
    ...

@router.post("/webhooks/{path:path}")
async def webhook_receiver(path: str, request: Request):
    """Receive webhook calls and fire associated workflows."""
    ...
```

- [ ] **Step 3: Wire scheduler lifecycle into FastAPI app**

In `src/decision_system/api/app.py`, add lifespan hooks:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start scheduler
    scheduler = app.state.scheduler
    await scheduler.start()
    yield
    # Shutdown: stop scheduler
    await scheduler.stop()
```

- [ ] **Step 4: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_api.py -k "TestSchedule or TestWebhook"
```

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/api.py src/decision_system/api/app.py
git commit -m "feat(api): add schedule CRUD routes, webhook receiver, and scheduler lifecycle"
```

---

### Task 7: CLI Schedule Management Commands

**File:**
- Modify: `src/decision_system/workflow_engine/cli.py`

Add `schedule` sub-command group to the CLI:

```
decision-system workflow schedule list           — List all schedules
decision-system workflow schedule list --cron    — Filter by trigger type
decision-system workflow schedule list --workflow <id>  — Filter by workflow
decision-system workflow schedule create <wf_id> --cron "0 9 * * 1-5"  — Create cron schedule
decision-system workflow schedule create <wf_id> --file-watch --directory "company_docs/" --pattern "*.md"
decision-system workflow schedule delete <id>
decision-system workflow schedule toggle <id>    — Enable/disable
decision-system workflow schedule webhooks       — List registered webhook URLs
```

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_workflow_engine/test_cli.py`:

**TestScheduleCLI:**
- `test_list_empty` — no schedules shows empty message
- `test_create_cron_schedule` — creates schedule and prints id
- `test_create_webhook_schedule` — creates schedule and prints webhook URL
- `test_delete_schedule` — deletes schedule
- `test_toggle_schedule` — toggles enabled state
- `test_list_by_workflow` — filters by workflow_id

- [ ] **Step 2: Implement CLI commands**

```python
@app.group()
def schedule():
    """Manage workflow schedules and triggers."""

@schedule.command("list")
def list_schedules(
    workflow_id: Optional[str] = typer.Option(None, "--workflow", "-w"),
    trigger_type: Optional[str] = typer.Option(None, "--type", "-t"),
):
    ...

@schedule.command("create")
def create_schedule(
    workflow_id: str,
    cron: Optional[str] = typer.Option(None, "--cron", "-c"),
    webhook: bool = typer.Option(False, "--webhook", "-w"),
    file_watch: bool = typer.Option(False, "--file-watch", "-f"),
    directory: Optional[str] = typer.Option(None, "--directory", "-d"),
    pattern: Optional[str] = typer.Option("*", "--pattern", "-p"),
):
    ...

@schedule.command("delete")
def delete_schedule(schedule_id: str):
    ...

@schedule.command("toggle")
def toggle_schedule(schedule_id: str):
    ...

@schedule.command("webhooks")
def list_webhooks():
    """List all registered webhook URLs."""
    ...
```

- [ ] **Step 3: Verify tests pass**

```bash
python -m pytest -q tests/test_workflow_engine/test_cli.py -k "TestSchedule"
```

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/cli.py
git commit -m "feat(cli): add workflow schedule management commands"
```

---

### Task 8: Auto-Schedule on Workflow Save

When a workflow with trigger nodes is saved, the system should automatically create/update/delete corresponding schedules. This is the bridge between the node palette (trigger nodes in the visual editor) and the scheduler service.

- [ ] **Step 1: Implement schedule sync logic in `_sync_schedules_for_workflow()`**

In `src/decision_system/workflow_engine/api.py`:

```python
def _sync_schedules_for_workflow(workflow: WorkflowDefinition) -> list[str]:
    """Auto-create/update/delete schedules based on workflow's trigger nodes.
    
    Scans workflow nodes for trigger types (cron, webhook, file_watch).
    Creates or updates corresponding ScheduleDefinition entries.
    Deletes schedules for trigger nodes that were removed.
    Returns list of schedule IDs.
    """
    TRIGGER_TYPE_MAP = {
        "decision_system.trigger_cron": TriggerType.CRON,
        "decision_system.trigger_webhook": TriggerType.WEBHOOK,
        "decision_system.trigger_file_watch": TriggerType.FILE_WATCH,
    }
    
    # Find trigger nodes in the workflow
    trigger_nodes = [n for n in workflow.nodes if n.type in TRIGGER_TYPE_MAP]
    
    # Get existing schedules for this workflow
    existing = _schedule_store.list(workflow_id=workflow.id)
    existing_by_type = {s.trigger_type.value: s for s in existing}
    
    schedule_ids = []
    seen_types = set()
    
    for node in trigger_nodes:
        trigger_type = TRIGGER_TYPE_MAP[node.type]
        seen_types.add(trigger_type.value)
        
        trigger_config = dict(node.config)
        if trigger_type == TriggerType.WEBHOOK and not trigger_config.get("webhook_path"):
            # Auto-generate webhook path
            import uuid
            trigger_config["webhook_path"] = f"hooks/wf-{workflow.id[:8]}-{uuid.uuid4().hex[:8]}"
        
        if trigger_type.value in existing_by_type:
            # Update existing schedule
            sd = existing_by_type[trigger_type.value]
            sd.trigger_config = trigger_config
            sd = _schedule_store.save(sd)
            schedule_ids.append(sd.id)
        else:
            # Create new schedule
            sd = ScheduleDefinition(
                workflow_id=workflow.id,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
            )
            sd = _schedule_store.save(sd)
            schedule_ids.append(sd.id)
    
    # Delete schedules for removed trigger types
    for s in existing:
        if s.trigger_type.value not in seen_types:
            _schedule_store.delete(s.id)
    
    return schedule_ids
```

- [ ] **Step 2: Integrate into save workflow routes**

Call `_sync_schedules_for_workflow()` at the end of `create_workflow()` and `update_workflow()`.

- [ ] **Step 3: Write tests**

**TestScheduleSync:**
- `test_auto_create_schedule_on_save` — saving workflow with CronTriggerNode creates schedule
- `test_auto_update_on_config_change` — changing cron expression updates schedule config
- `test_auto_delete_on_node_removal` — removing trigger node deletes associated schedule
- `test_no_schedule_for_manual_trigger` — workflow with only ManualTriggerNode creates no schedule
- `test_multiple_trigger_nodes` — workflow with cron + webhook creates both schedules

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/api.py
git commit -m "feat(api): auto-create/update/delete schedules on workflow save"
```

---

### Task 9: Frontend API + Mock Data Updates

**Files:**
- Modify: `web/workflow-builder/src/api.js`
- Modify: `web/workflow-builder/src/mockData.js`

- [ ] **Step 1: Add 3 new trigger node types to mockData.js**

In `web/workflow-builder/src/mockData.js`, add to `MOCK_NODE_TYPES`:

```javascript
{
  type: "decision_system.trigger_cron",
  label: "Cron Trigger",
  description: "Schedule a workflow on a time-based cron expression",
  categories: ["trigger"],
  config_schema: {
    type: "object",
    properties: {
      expression: {
        type: "string",
        title: "Cron Expression",
        description: "Schedule in cron format: minute hour day-of-month month day-of-week",
        default: "0 9 * * *",
      },
    },
  },
  input_schema: { type: "object", properties: {} },
  output_schema: {
    type: "object",
    properties: {
      trigger_type: { type: "string" },
      expression: { type: "string" },
      triggered: { type: "boolean" },
    },
  },
},
{
  type: "decision_system.trigger_webhook",
  label: "Webhook Trigger",
  description: "Receive HTTP POST requests to start the workflow",
  categories: ["trigger"],
  config_schema: {
    type: "object",
    properties: {
      webhook_path: {
        type: "string",
        title: "Webhook Path",
        description: "Auto-generated unique path",
        default: "",
      },
    },
  },
  input_schema: {
    type: "object",
    properties: {
      payload: { type: "object", title: "Webhook Payload" },
    },
  },
  output_schema: {
    type: "object",
    properties: {
      trigger_type: { type: "string" },
      webhook_path: { type: "string" },
      triggered: { type: "boolean" },
    },
  },
},
{
  type: "decision_system.trigger_file_watch",
  label: "File Watch Trigger",
  description: "Start the workflow when files change in a directory",
  categories: ["trigger"],
  config_schema: {
    type: "object",
    properties: {
      directory: {
        type: "string",
        title: "Directory",
        description: "Directory path to watch",
        default: "company_docs/",
      },
      pattern: {
        type: "string",
        title: "File Pattern",
        description: "Glob pattern (e.g. *.md, *.csv)",
        default: "*",
      },
    },
  },
  input_schema: { type: "object", properties: {} },
  output_schema: {
    type: "object",
    properties: {
      trigger_type: { type: "string" },
      directory: { type: "string" },
      pattern: { type: "string" },
      changed_files: { type: "array" },
      triggered: { type: "boolean" },
    },
  },
},
```

- [ ] **Step 2: Add schedule CRUD functions to api.js**

```javascript
function listSchedules(filters = {}) {
  if (isMockMode()) {
    let results = [..._mockSchedules];
    if (filters.workflow_id) results = results.filter(s => s.workflow_id === filters.workflow_id);
    if (filters.trigger_type) results = results.filter(s => s.trigger_type === filters.trigger_type);
    return Promise.resolve(results);
  }
  const params = new URLSearchParams(filters);
  return apiFetch(`/schedules?${params}`);
}

function createSchedule(schedule) {
  if (isMockMode()) {
    const s = { ...schedule, id: `sch-mock-${Date.now()}`, enabled: true, created_at: new Date().toISOString() };
    _mockSchedules.push(s);
    return Promise.resolve(s);
  }
  return apiFetch("/schedules", { method: "POST", body: JSON.stringify(schedule) });
}

function deleteSchedule(id) {
  if (isMockMode()) {
    _mockSchedules = _mockSchedules.filter(s => s.id !== id);
    return Promise.resolve({ success: true });
  }
  return apiFetch(`/schedules/${id}`, { method: "DELETE" });
}

function toggleSchedule(id) {
  if (isMockMode()) {
    const s = _mockSchedules.find(s => s.id === id);
    if (s) s.enabled = !s.enabled;
    return Promise.resolve(s);
  }
  return apiFetch(`/schedules/${id}/toggle`, { method: "PATCH" });
}

function listWebhooks() {
  if (isMockMode()) return Promise.resolve([]);
  return apiFetch("/schedules/webhooks");
}
```

- [ ] **Step 3: Add mock schedule data**

```javascript
const MOCK_SCHEDULES = [
  {
    id: "sch-mock-001",
    workflow_id: "wf-sample-1",
    trigger_type: "cron",
    trigger_config: { expression: "0 9 * * 1-5" },
    enabled: true,
    last_fired: "2026-06-12T09:00:00Z",
    created_at: "2026-06-10T00:00:00Z",
    updated_at: "2026-06-12T09:00:00Z",
  },
];
let _mockSchedules = [...MOCK_SCHEDULES];
```

- [ ] **Step 4: Verify frontend tests pass**

```bash
cd web/workflow-builder && npx vitest run
```

- [ ] **Step 5: Commit**

```bash
git add web/workflow-builder/src/api.js web/workflow-builder/src/mockData.js
git commit -m "feat(ui): add trigger node types and schedule API to frontend"
```

---

### Task 10: Frontend Schedule Management UI

**Files:**
- New: `web/workflow-builder/src/components/ScheduleManager.jsx`
- New: `web/workflow-builder/src/styles/schedule-manager.css`
- New: `web/workflow-builder/__tests__/ScheduleManager.test.jsx`
- Modify: `web/workflow-builder/src/App.jsx`

Add a schedule management panel that shows all active schedules, their status (enabled/disabled), last-fired timestamps, and controls to toggle/delete them.

- [ ] **Step 1: Write failing tests**

**ScheduleManager test:**
- `test_shows_list_of_schedules` — renders schedule list with workflow name + trigger type
- `test_shows_enabled_badge` — enabled schedule shows green badge
- `test_shows_disabled_badge` — disabled schedule shows gray badge
- `test_toggle_schedule` — click toggle button calls API
- `test_delete_schedule` — click delete button removes from list
- `test_shows_cron_expression` — cron schedule displays expression
- `test_shows_webhook_url` — webhook schedule displays URL
- `test_shows_file_watch_config` — file watch schedule displays directory + pattern
- `test_empty_state` — no schedules shows "No schedules yet" message
- `test_refresh_list` — refreshes schedule list from API

- [ ] **Step 2: Implement ScheduleManager component**

```jsx
// components/ScheduleManager.jsx
import React, { useState, useEffect, useCallback } from "react";
import { listSchedules, toggleSchedule, deleteSchedule } from "../api";
import "../styles/schedule-manager.css";

const TRIGGER_LABELS = {
  cron: { icon: "⏰", label: "Cron" },
  webhook: { icon: "🔗", label: "Webhook" },
  file_watch: { icon: "👁", label: "File Watch" },
};

function ScheduleManager() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSchedules = useCallback(async () => {
    try {
      const data = await listSchedules();
      setSchedules(data);
    } catch (err) {
      console.error("Failed to load schedules:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSchedules(); }, [fetchSchedules]);

  const handleToggle = async (id) => {
    await toggleSchedule(id);
    await fetchSchedules();
  };

  const handleDelete = async (id) => {
    await deleteSchedule(id);
    await fetchSchedules();
  };

  if (loading) return <div className="schedule-manager"><p>Loading schedules...</p></div>;

  return (
    <div className="schedule-manager">
      <div className="schedule-header">
        <h3>Schedules</h3>
      </div>
      {schedules.length === 0 ? (
        <p className="schedule-empty">No schedules yet. Add a Cron/Webhook/File Watch trigger node to a workflow and save.</p>
      ) : (
        <div className="schedule-list">
          {schedules.map(s => {
            const t = TRIGGER_LABELS[s.trigger_type] || { icon: "?", label: s.trigger_type };
            return (
              <div key={s.id} className={`schedule-item ${s.enabled ? "enabled" : "disabled"}`}>
                <div className="schedule-item-header">
                  <span className="schedule-trigger-icon">{t.icon}</span>
                  <span className="schedule-trigger-label">{t.label}</span>
                  <span className={`schedule-status ${s.enabled ? "active" : "inactive"}`}>
                    {s.enabled ? "Active" : "Disabled"}
                  </span>
                </div>
                <div className="schedule-detail">{s.workflow_id}</div>
                <div className="schedule-config-detail">
                  {s.trigger_type === "cron" && <code>{s.trigger_config?.expression || "—"}</code>}
                  {s.trigger_type === "webhook" && <code>{s.trigger_config?.webhook_path || "—"}</code>}
                  {s.trigger_type === "file_watch" && (
                    <span>{s.trigger_config?.directory || "?"} ({s.trigger_config?.pattern || "*"})</span>
                  )}
                </div>
                <div className="schedule-last-fired">
                  {s.last_fired ? `Last: ${new Date(s.last_fired).toLocaleString()}` : "Never fired"}
                </div>
                <div className="schedule-actions">
                  <button className="schedule-toggle-btn" onClick={() => handleToggle(s.id)}>
                    {s.enabled ? "Disable" : "Enable"}
                  </button>
                  <button className="schedule-delete-btn" onClick={() => handleDelete(s.id)}>
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add CSS**

Create `web/workflow-builder/src/styles/schedule-manager.css` with styles for the schedule list, items, status badges, and action buttons.

- [ ] **Step 4: Integrate into App.jsx**

Add a "Schedules" button to the toolbar that opens a schedule management sidebar or modal.

- [ ] **Step 5: Verify frontend tests pass**

```bash
cd web/workflow-builder && npx vitest run
```

- [ ] **Step 6: Commit**

```bash
git add web/workflow-builder/src/components/ScheduleManager.jsx web/workflow-builder/src/styles/schedule-manager.css web/workflow-builder/__tests__/ScheduleManager.test.jsx web/workflow-builder/src/App.jsx
git commit -m "feat(ui): add ScheduleManager component for viewing and managing triggers"
```

---

### Task 11: End-to-End Integration Tests

**Files:**
- Modify: `tests/test_workflow_engine/test_integration.py`
- Modify: `web/workflow-builder/__tests__/integration.test.jsx`

- [ ] **Step 1: Backend integration tests**

Add to `tests/test_workflow_engine/test_integration.py`:

**TestSchedulerIntegration:**
- `test_cron_trigger_workflow_integration` — create cron schedule, start scheduler, verify workflow fires
- `test_webhook_trigger_workflow_integration` — POST to webhook URL, verify workflow executes
- `test_file_watch_trigger_integration` — create file in watched dir, verify workflow fires
- `test_schedule_disabled_does_not_fire` — disable schedule, verify no execution
- `test_auto_schedule_on_workflow_save_via_api` — create workflow with CronTriggerNode via API, verify schedule auto-created
- `test_workflow_with_trigger_nodes_executes_manually` — CronTriggerNode works as passthrough during manual execution (no scheduler needed)

**TestSchedulerLifecycle:**
- `test_scheduler_start_stop_via_api` — start/stop scheduler via API endpoint
- `test_scheduler_does_not_affect_manual_execution` — manual execution works independently of scheduler

- [ ] **Step 2: Frontend integration tests**

Add to `web/workflow-builder/__tests__/integration.test.jsx`:

**ScheduleIntegration:**
- `test_cron_trigger_node_appears_in_palette` — Cron Trigger is draggable from palette
- `test_trigger_node_config_in_config_panel` — selecting trigger node shows schedule config
- `test_schedule_manager_renders` — ScheduleManager appears and loads schedules

- [ ] **Step 3: Run all tests**

```bash
python -m pytest -q               # Backend: all pass
cd web/workflow-builder && npx vitest run   # Frontend: all pass
```

Expected: 810+ backend tests, 40+ frontend tests, all passing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_workflow_engine/test_integration.py web/workflow-builder/__tests__/integration.test.jsx
git commit -m "test(scheduler): add end-to-end integration tests for scheduling and triggers"
```

---

### Task 12: Self-Review and Final Verification

- [ ] **Step 1: Spec self-review**

Check for common issues:
- Placeholders? Any "TBD", "TODO", or empty sections in code?
- Consistency: Do all API routes follow the existing pattern (`/workflows`, `/executions`)?
- Edge cases: What happens when a workflow is deleted but has active schedules?
- Edge cases: What happens when the watched directory doesn't exist?
- Edge cases: What happens when webhook payload exceeds size limit?
- Edge cases: What happens when cron expression is invalid?
- Error paths: Are all API errors returning proper HTTP status codes?
- Are schedule stores cleaned up when workflow is deleted?
- Does the scheduler handle DST changes correctly? (cron expressions match wall clock)
- Does the scheduler survive the FastAPI server restart? (JSON file persistence)

- [ ] **Step 2: Run full test suite**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest -q --tb=short 2>&1 | tail -5
cd web/workflow-builder
npx vitest run --reporter=verbose 2>&1 | tail -10
```

- [ ] **Step 3: Run hygiene check**

```bash
decision-system check-hygiene
```

- [ ] **Step 4: Verify working tree**

```bash
git status
git log --oneline -5
```

- [ ] **Step 5: Build SPA and verify**

```bash
cd web/workflow-builder && npx vite build
```

- [ ] **Step 6: Update CHANGELOG.md**

Add v1.11.0 entry with Phase 4 features.

- [ ] **Step 7: Update pyproject.toml**

Bump version to `1.11.0`.

- [ ] **Step 8: Final commit**

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "release: v1.11.0 — Phase 4 scheduling, triggers, and webhook automation"
```

---

## Verification Checklist (all phases)

| Check | Expected |
|---|---|
| `python -m pytest -q` | 810+ passed |
| `cd web/workflow-builder && npx vitest run` | 40+ passed |
| `git status` | clean |
| `cd web/workflow-builder && npx vite build` | builds without error |
| New schedules persist after server restart | confirmed by JSON store tests |
| Scheduler fires workflow on cron match | confirmed by integration tests |
| Webhook POST triggers workflow execution | confirmed by integration tests |
| File watch detects new files and triggers | confirmed by integration tests |
| Disabled schedules don't fire | confirmed by integration tests |
| Manual execution still works | confirmed by existing tests |
| Auto-schedule on workflow save | confirmed by API integration tests |
