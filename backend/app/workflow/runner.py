"""工作流执行器 — 状态机，管理运行生命周期"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

from loguru import logger

from app.models import WorkflowMode, WorkflowStep
from app.workflow.bus import message_bus, BusMessage, MessageType
from app.workflow.engine import WorkflowEngine, StepResult


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"


class WorkflowRun:
    """一次工作流执行"""

    def __init__(self, run_id: str, workflow_id: str, workflow_name: str,
                 mode: WorkflowMode, steps: list[WorkflowStep]):
        self.run_id = run_id
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.mode = mode
        self.steps = steps
        self.status = RunStatus.PENDING
        self.results: list[StepResult] = []
        self.logs: list[dict] = []
        self.user_input: str = ""
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.start_time:
            end = self.end_time or datetime.utcnow()
            return (end - self.start_time).total_seconds()
        return 0

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0
        return len(self.results) / len(self.steps)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "mode": self.mode.value,
            "status": self.status.value,
            "progress": self.progress,
            "duration": self.duration,
            "user_input": self.user_input,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "instance_id": s.instance_id,
                    "status": "done" if any(r.step_id == s.id and r.success for r in self.results)
                             else "failed" if any(r.step_id == s.id for r in self.results)
                             else "pending",
                    "output": next((r.output for r in self.results if r.step_id == s.id), ""),
                    "error": next((r.error for r in self.results if r.step_id == s.id), None),
                }
                for s in self.steps
            ],
            "logs": self.logs[-100:],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error": self.error,
        }


class WorkflowRunner:
    """工作流执行器 — 管理所有工作流运行"""

    def __init__(self):
        self._runs: dict[str, WorkflowRun] = {}
        self._engine = WorkflowEngine()
        self._tasks: dict[str, asyncio.Task] = {}

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._runs.get(run_id)

    def list_runs(self, workflow_id: Optional[str] = None) -> list[dict]:
        runs = self._runs.values()
        if workflow_id:
            runs = [r for r in runs if r.workflow_id == workflow_id]
        return [r.to_dict() for r in sorted(runs, key=lambda r: r.start_time or datetime.min, reverse=True)]

    async def execute(self, workflow_id: str, workflow_name: str,
                      mode: WorkflowMode, steps: list[WorkflowStep],
                      user_input: str) -> str:
        """启动工作流执行"""
        run_id = uuid.uuid4().hex[:12]

        run = WorkflowRun(
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            mode=mode,
            steps=steps,
        )
        run.user_input = user_input
        run.status = RunStatus.RUNNING
        run.start_time = datetime.utcnow()
        self._runs[run_id] = run

        # 广播开始消息
        await message_bus.send(BusMessage(
            workflow_run_id=run_id,
            msg_type=MessageType.SYSTEM,
            content=f"工作流 [{workflow_name}] 开始执行",
        ))

        # 异步执行
        task = asyncio.create_task(self._run_workflow(run))
        self._tasks[run_id] = task

        return run_id

    async def _run_workflow(self, run: WorkflowRun):
        """执行工作流"""
        def on_log(step_id: str, message: str):
            log_entry = {
                "step_id": step_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
            run.logs.append(log_entry)
            logger.info(f"[WF:{run.run_id}] [{step_id}] {message}")

        try:
            if run.mode == WorkflowMode.PIPELINE:
                run.results = await self._engine.run_pipeline(
                    run.steps, run.user_input, run.run_id, on_log)
            elif run.mode == WorkflowMode.ROUNDTABLE:
                run.results = await self._engine.run_roundtable(
                    run.steps, run.user_input, rounds=2, workflow_run_id=run.run_id, on_log=on_log)
            elif run.mode == WorkflowMode.REVIEW_LOOP:
                run.results = await self._engine.run_review_loop(
                    run.steps, run.user_input, max_iterations=3, workflow_run_id=run.run_id, on_log=on_log)
            elif run.mode == WorkflowMode.DEBATE:
                run.results = await self._engine.run_debate(
                    run.steps, run.user_input, workflow_run_id=run.run_id, on_log=on_log)

            # 检查结果
            if all(r.success for r in run.results):
                run.status = RunStatus.SUCCESS
            else:
                run.status = RunStatus.FAILED
                run.error = "部分步骤失败"

        except asyncio.CancelledError:
            run.status = RunStatus.ABORTED
            run.error = "用户终止"
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error = str(e)
            logger.error(f"[WF:{run.run_id}] 执行异常: {e}")
        finally:
            run.end_time = datetime.utcnow()
            self._tasks.pop(run.run_id, None)

            # 广播结束消息
            await message_bus.send(BusMessage(
                workflow_run_id=run.run_id,
                msg_type=MessageType.SYSTEM,
                content=f"工作流 [{run.workflow_name}] {run.status.value}",
            ))

    async def pause(self, run_id: str) -> bool:
        """暂停工作流"""
        run = self._runs.get(run_id)
        if not run or run.status != RunStatus.RUNNING:
            return False
        run.status = RunStatus.PAUSED
        self._engine.pause()
        return True

    async def resume(self, run_id: str) -> bool:
        """恢复工作流"""
        run = self._runs.get(run_id)
        if not run or run.status != RunStatus.PAUSED:
            return False
        run.status = RunStatus.RUNNING
        self._engine.resume()
        return True

    async def abort(self, run_id: str) -> bool:
        """终止工作流"""
        run = self._runs.get(run_id)
        if not run or run.status not in (RunStatus.RUNNING, RunStatus.PAUSED):
            return False
        self._engine.abort()
        task = self._tasks.get(run_id)
        if task:
            task.cancel()
        return True

    async def inject_message(self, run_id: str, content: str) -> bool:
        """注入消息"""
        run = self._runs.get(run_id)
        if not run:
            return False
        await message_bus.send(BusMessage(
            workflow_run_id=run_id,
            msg_type=MessageType.SYSTEM,
            content=content,
        ))
        run.logs.append({
            "step_id": "_inject",
            "message": f"人工注入: {content}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        return True


# 全局执行器
workflow_runner = WorkflowRunner()
