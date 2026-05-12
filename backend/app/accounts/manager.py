"""账号管理器 — CRUD + 状态机（Phase 2 完善）"""

from loguru import logger


class AccountManager:
    """账号管理器"""

    async def create(self, **kwargs):
        raise NotImplementedError

    async def list(self):
        raise NotImplementedError

    async def get(self, account_id: str):
        raise NotImplementedError

    async def update(self, account_id: str, **kwargs):
        raise NotImplementedError

    async def delete(self, account_id: str):
        raise NotImplementedError
