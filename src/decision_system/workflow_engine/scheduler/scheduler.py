"""Background scheduler service — runs alongside the FastAPI server.

The scheduler is a single asyncio task that polls all enabled schedules
periodically and executes workflows when trigger conditions are met.

Typical usage::

    scheduler = SchedulerService(schedule_store, dag_engine)
    await scheduler.start()   # begins the background polling loop
    ...
    await scheduler.stop()    # clean shutdown
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.scheduler.models import (
    TriggerType,
    ScheduleDefinition,
)
from decision_system.workflow_engine.scheduler.store import ScheduleStore
from decision_system.workflow_engine.scheduler.triggers import (
    evaluate_cron,
    scan_directory,
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background scheduler that polls schedules and fires workflows.

    Parameters
    ----------
    schedule_store:
        Store for ``ScheduleDefinition`` objects.
    dag_engine:
        The DAG execution engine used to run workflows.
    poll_interval:
        Seconds between schedule evaluation cycles (default 60).
    watch_interval:
        Seconds between file-watch scans (default 15).
    """

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

        # Track known files per file-watch schedule for diff detection
        self._known_files: dict[str, set[str]] = {}

    @property
    def is_running(self) -> bool:
        """Whether the scheduler loop is currently active."""
        return self._running

    async def start(self) -> None:
        """Start the scheduler background loop as an asyncio task."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Scheduler started (poll=%ss, watch=%ss)",
            self._poll_interval,
            self._watch_interval,
        )

    async def stop(self) -> None:
        """Stop the scheduler background loop and clean up."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop — runs until ``stop()`` is called."""
        try:
            while self._running:
                try:
                    await self._check_schedules()
                except Exception as exc:
                    logger.error("Scheduler check failed: %s", exc, exc_info=True)
                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass

    async def _check_schedules(self) -> None:
        """Evaluate all enabled schedules and fire matching triggers."""
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
                    schedule.trigger_config["_changed_files"] = new_files

            # Webhook triggers are handled via the API route, not polling

            if should_fire:
                await self._fire(schedule)

    async def _fire(self, schedule: ScheduleDefinition) -> None:
        """Execute the workflow associated with *schedule*."""
        wf = self._engine.workflow_store.load(schedule.workflow_id)
        if wf is None:
            logger.warning(
                "Schedule %s: workflow %s not found",
                schedule.id,
                schedule.workflow_id,
            )
            return

        logger.info(
            "Firing schedule %s -> workflow %s (trigger=%s)",
            schedule.id,
            schedule.workflow_id,
            schedule.trigger_type.value,
        )

        inputs: dict = {}
        if "_changed_files" in schedule.trigger_config:
            inputs["_changed_files"] = schedule.trigger_config.pop("_changed_files")

        state = await self._engine.execute(wf, global_inputs=inputs)

        self._store.update_last_fired(schedule.id, datetime.now(timezone.utc))

        if state.status == "failed":
            logger.error(
                "Schedule %s: workflow execution failed: %s",
                schedule.id,
                state.error,
            )
