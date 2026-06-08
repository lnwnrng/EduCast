"""审计日志服务。"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:

    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: str,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        details: str | None = None,
    ) -> None:
        """记录一条审计日志。"""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
        db.add(entry)

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        days: int | None = None,
    ) -> tuple[list[AuditLog], int]:
        """分页查询审计日志。"""
        query = select(AuditLog)
        if action:
            query = query.where(AuditLog.action == action)
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.where(AuditLog.created_at >= cutoff)
        query = query.order_by(AuditLog.created_at.desc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total