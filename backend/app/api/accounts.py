"""账号管理 API"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.database import get_db
from app.models import Account, AccountCreate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("")
async def create_account(req: AccountCreate):
    """添加账号"""
    account_id = f"{req.platform.value}-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    async with await get_db() as db:
        await db.execute(
            "INSERT INTO accounts (id, platform, display_name, profile_dir, proxy, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (account_id, req.platform.value, req.display_name,
             req.profile_dir or f"./data/profiles/{account_id}",
             req.proxy, json.dumps(req.tags), now, now)
        )
        await db.commit()

    logger.info(f"账号创建: {account_id} ({req.display_name})")
    return {"id": account_id, "message": "账号已创建"}


@router.get("")
async def list_accounts():
    """账号列表"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM accounts ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "platform": row["platform"],
                "display_name": row["display_name"],
                "profile_dir": row["profile_dir"],
                "proxy": row["proxy"],
                "tags": json.loads(row["tags"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


@router.get("/{account_id}")
async def get_account(account_id: str):
    """账号详情"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="账号不存在")
        return {
            "id": row["id"],
            "platform": row["platform"],
            "display_name": row["display_name"],
            "profile_dir": row["profile_dir"],
            "proxy": row["proxy"],
            "tags": json.loads(row["tags"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


@router.put("/{account_id}")
async def update_account(account_id: str, req: AccountCreate):
    """更新账号"""
    now = datetime.utcnow().isoformat()
    async with await get_db() as db:
        cursor = await db.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="账号不存在")

        await db.execute(
            "UPDATE accounts SET platform=?, display_name=?, profile_dir=?, proxy=?, tags=?, updated_at=? WHERE id=?",
            (req.platform.value, req.display_name, req.profile_dir,
             req.proxy, json.dumps(req.tags), now, account_id)
        )
        await db.commit()
    return {"message": "已更新"}


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """删除账号"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="账号不存在")
        await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await db.commit()
    return {"message": "已删除"}
