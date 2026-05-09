from __future__ import annotations

from pathlib import Path
import sys

from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (REPO_ROOT, BACKEND_ROOT):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)

import database.session as session_module
from models import HealthScoreRecord, User


def test_resolve_table_name_handles_primary_mapper_without_boolean_coercion():
    assert session_module._resolve_table_name(mapper=inspect(User)) == "users"


def test_routing_session_uses_primary_engine_for_operational_tables():
    session = session_module.RoutingSession()
    try:
        assert session.get_bind(mapper=inspect(User)) is session_module.primary_engine
    finally:
        session.close()


def test_routing_session_uses_analytics_read_engine_for_analytics_tables():
    session = session_module.RoutingSession()
    try:
        assert session.get_bind(mapper=inspect(HealthScoreRecord)) is session_module.get_analytics_read_engine()
    finally:
        session.close()


def test_session_scope_rolls_back_and_closes_on_exception():
    session = MagicMock()
    factory = MagicMock(return_value=session)

    with pytest.raises(RuntimeError, match="boom"):
        with session_module.session_scope(factory=factory, label="test-scope"):
            raise RuntimeError("boom")

    session.rollback.assert_called_once()
    session.close.assert_called_once()
