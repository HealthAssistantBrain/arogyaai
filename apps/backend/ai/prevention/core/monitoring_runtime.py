from __future__ import annotations

import asyncio
from typing import Iterable

from sqlalchemy.orm import Session

from models import User

from .preventive_engine import PreventiveEngine


class MonitoringRuntime:
    def __init__(self, engine: PreventiveEngine | None = None) -> None:
        self.engine = engine or PreventiveEngine()

    async def run_once(
        self,
        db: Session,
        user: User,
        *,
        force_refresh: bool = False,
        persist: bool = True,
    ) -> dict:
        return await asyncio.to_thread(
            self.engine.generate,
            db,
            user,
            force_refresh=force_refresh,
            persist=persist,
        )

    async def run_batch(self, db: Session, users: Iterable[User]) -> list[dict]:
        tasks = [
            asyncio.to_thread(self.engine.generate, db, user, force_refresh=False, persist=True)
            for user in users
        ]
        return await asyncio.gather(*tasks)
