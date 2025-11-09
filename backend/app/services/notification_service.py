"""Serviço responsável pela gestão de notificações in-app."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification, NotificationType
from ..models.user import User


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str | None = None,
        type_: NotificationType = NotificationType.INFO,
        extra_data: dict | None = None,
        auto_commit: bool = True,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type_,
            extra_data=extra_data,
        )
        self.session.add(notification)
        if auto_commit:
            await self.session.commit()
            await self.session.refresh(notification)
        else:
            await self.session.flush()
        return notification

    async def list_notifications(
        self,
        user: User,
        *,
        only_unread: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if only_unread:
            stmt = stmt.where(Notification.is_read.is_(False))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(self, user: User) -> int:
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        return int(result.scalar_one() or 0)

    async def mark_read(self, user: User, notification_ids: Iterable[UUID]) -> int:
        ids = list(notification_ids)
        if not ids:
            return 0
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.id.in_(ids),
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
            .returning(Notification.id)
        )
        updated = len(result.fetchall())
        await self.session.commit()
        return updated

    async def mark_all_read(self, user: User) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(
                and_(Notification.user_id == user.id, Notification.is_read.is_(False))
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
            .returning(Notification.id)
        )
        updated = len(result.fetchall())
        await self.session.commit()
        return updated


__all__ = ("NotificationService", "NotificationType")
