from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, Callable, Mapping, Sequence


TaskLike = Callable[[], Any] | Awaitable[Any] | Any


class WorkflowTaskExecutor:
    async def run_parallel(self, tasks: Mapping[str, TaskLike]) -> dict[str, Any]:
        names = list(tasks.keys())
        results = await asyncio.gather(*(self._resolve(task) for task in tasks.values()))
        return dict(zip(names, results, strict=False))

    async def run_sequence(self, tasks: Sequence[TaskLike]) -> list[Any]:
        results: list[Any] = []
        for task in tasks:
            results.append(await self._resolve(task))
        return results

    async def run_conditional(
        self,
        predicate: bool | Callable[[], bool] | Callable[[], Awaitable[bool]],
        when_true: TaskLike,
        when_false: TaskLike | None = None,
    ) -> Any:
        decision = await self._resolve(predicate)
        if decision:
            return await self._resolve(when_true)
        if when_false is None:
            return None
        return await self._resolve(when_false)

    async def run_with_fallback(self, primary: TaskLike, fallbacks: Sequence[TaskLike]) -> Any:
        try:
            return await self._resolve(primary)
        except Exception:
            for candidate in fallbacks:
                try:
                    return await self._resolve(candidate)
                except Exception:
                    continue
            raise

    async def _resolve(self, task: TaskLike) -> Any:
        value = task() if callable(task) else task
        if inspect.isawaitable(value):
            return await value
        return value

