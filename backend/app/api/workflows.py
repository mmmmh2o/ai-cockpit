"""工作流管理 API — Phase 3 完整版"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.database import get_db
from app.models import WorkflowCreate, WorkflowMode, WorkflowStep
from app.workflow.runner import workflow_runner
from app.workflow.templates import list_templates, get_template

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ── 模板 ──────────────────────────────────────────

@router.get("/templates")
async def get_templates():
    """获取预置工作流模板"""
    return list_templates()


@router.get("/templates/{template_id}")
async def get_template_detail(template_id: str):
    """获取模板详情"""
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {
        "id": template_id,
        "name": tmpl["name"],
        "description": tmpl["description"],
        "mode": tmpl["mode"].value,
        "steps": [s.model_dump() for s in tmpl["steps"]],
    }


# ── 工作流 CRUD ──────────────────────────────────

@router.get("")
async def list_workflows():
    """工作流列表"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM workflows ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "mode": row["mode"],
                "steps": json.loads(row["steps"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


@router.post("")
async def create_workflow(req: WorkflowCreate):
    """创建工作流"""
    wf_id = f"wf-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    async with await get_db() as db:
        await db.execute(
            "INSERT INTO workflows (id, name, mode, steps, created_at) VALUES (?, ?, ?, ?, ?)",
            (wf_id, req.name, req.mode.value,
             json.dumps([s.model_dump() for s in req.steps], default=str), now)
        )
        await db.commit()

    logger.info(f"工作流创建: {wf_id} ({req.name})")
    return {"id": wf_id, "message": "工作流已创建"}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    """工作流详情"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="工作流不存在")
        return {
            "id": row["id"],
            "name": row["name"],
            "mode": row["mode"],
            "steps": json.loads(row["steps"]),
            "created_at": row["created_at"],
        }


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowCreate):
    """更新工作流"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT id FROM workflows WHERE id = ?", (workflow_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="工作流不存在")
        await db.execute(
            "UPDATE workflows SET name=?, mode=?, steps=? WHERE id=?",
            (req.name, req.mode.value,
             json.dumps([s.model_dump() for s in req.steps], default=str), workflow_id)
        )
        await db.commit()
    return {"message": "已更新"}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """删除工作流"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT id FROM workflows WHERE id = ?", (workflow_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="工作流不存在")
        await db.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        await db.commit()
    return {"message": "已删除"}


# ── 执行 ──────────────────────────────────────────

@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, body: dict):
    """执行工作流"""
    user_input = body.get("input", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="需要提供 input")

    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="工作流不存在")

    steps_data = json.loads(row["steps"])
    steps = [WorkflowStep(**s) for s in steps_data]
    mode = WorkflowMode(row["mode"])

    run_id = await workflow_runner.execute(
        workflow_id=workflow_id,
        workflow_name=row["name"],
        mode=mode,
        steps=steps,
        user_input=user_input,
    )

    return {"run_id": run_id, "message": "工作流已启动"}


@router.get("/run/{run_id}")
async def get_run_status(run_id: str):
    """获取执行状态"""
    run = workflow_runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return run.to_dict()


@router.post("/run/{run_id}/pause")
async def pause_run(run_id: str):
    """暂停执行"""
    success = await workflow_runner.pause(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法暂停")
    return {"message": "已暂停"}


@router.post("/run/{run_id}/resume")
async def resume_run(run_id: str):
    """恢复执行"""
    success = await workflow_runner.resume(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法恢复")
    return {"message": "已恢复"}


@router.post("/run/{run_id}/abort")
async def abort_run(run_id: str):
    """终止执行"""
    success = await workflow_runner.abort(run_id)
    if not success:
        raise HTTPException(status_code=400, detail="无法终止")
    return {"message": "已终止"}


@router.post("/run/{run_id}/inject")
async def inject_message(run_id: str, body: dict):
    """注入消息"""
    content = body.get("message", "")
    if not content:
        raise HTTPException(status_code=400, detail="需要提供 message")
    success = await workflow_runner.inject_message(run_id, content)
    if not success:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {"message": "已注入"}


@router.get("/run/{run_id}/logs")
async def get_run_logs(run_id: str):
    """获取执行日志"""
    run = workflow_runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return run.logs


# ── 执行列表 ──────────────────────────────────────

@router.get("/runs")
async def list_runs(workflow_id: str = None):
    """执行记录列表"""
    return workflow_runner.list_runs(workflow_id)
