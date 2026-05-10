from __future__ import annotations

from typing import Any


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, Any] = {}
        self._aliases: dict[str, str] = {}

    def register(self, workflow: Any) -> Any:
        if not getattr(workflow, "name", ""):
            raise ValueError("workflow.name is required")
        self._workflows[workflow.name] = workflow
        for alias in sorted(getattr(workflow, "aliases", frozenset()) or []):
            self._aliases[alias] = workflow.name
        return workflow

    def get(self, name: str) -> Any | None:
        if name in self._workflows:
            return self._workflows.get(name)
        canonical = self._aliases.get(name)
        return self._workflows.get(canonical) if canonical else None

    def names(self) -> list[str]:
        return sorted(self._workflows)

    def resolve_name(self, name: str) -> str | None:
        if name in self._workflows:
            return name
        return self._aliases.get(name)

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": workflow.name,
                "aliases": sorted(getattr(workflow, "aliases", frozenset()) or []),
                "version": workflow.version,
                "timeout_seconds": workflow.timeout_seconds,
                "retryable_stages": sorted(getattr(workflow, "retryable_stages", [])),
                "timeline_enabled": workflow.timeline_enabled,
            }
            for workflow in sorted(self._workflows.values(), key=lambda item: item.name)
        ]

