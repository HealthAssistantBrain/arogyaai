import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://user:password@postgres:5432/arogyaai"
ANALYTICS_TABLES = {
    "baseline_metrics",
    "feature_snapshots",
    "health_scores",
    "recommendations",
    "risk_scores",
    "shap_values",
    "user_vitals",
    "wearable_metrics",
}
VALID_ANALYTICS_MODES = {"primary", "dual_write", "analytics"}
logger = logging.getLogger("database.session")
_tracking_lock = threading.Lock()
_active_session_count = 0
_peak_session_count = 0
_last_pool_log_at: dict[str, float] = {}


def _normalize_mode(value: str | None) -> str:
    normalized = (value or "primary").strip().lower().replace("-", "_")
    aliases = {
        "disabled": "primary",
        "legacy": "primary",
        "mirror": "dual_write",
        "dual": "dual_write",
        "dualwrite": "dual_write",
        "shadow": "dual_write",
        "neon": "analytics",
        "timescale": "analytics",
        "timescaledb": "analytics",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in VALID_ANALYTICS_MODES:
        return "primary"
    return normalized


def _coerce_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _engine_label(application_name: str) -> str:
    return application_name.replace("arogyaai-", "")


def _pool_metrics(engine: Engine) -> dict[str, Any]:
    pool = getattr(engine, "pool", None)
    if pool is None:
        return {"size": None, "checked_out": None, "overflow": None}

    metrics: dict[str, Any] = {}
    for field, method_name in (("size", "size"), ("checked_out", "checkedout"), ("overflow", "overflow")):
        method = getattr(pool, method_name, None)
        if callable(method):
            try:
                metrics[field] = int(method())
            except Exception:
                metrics[field] = None
        else:
            metrics[field] = None
    return metrics


def get_pool_metrics(engine: Engine) -> dict[str, Any]:
    return {
        "url": str(engine.url),
        **_pool_metrics(engine),
    }


def _log_pool_snapshot(engine: Engine, *, label: str, event_name: str, force: bool = False) -> None:
    if not _coerce_bool("DB_POOL_LOGGING_ENABLED", "true"):
        return

    metrics = _pool_metrics(engine)
    checked_out = metrics.get("checked_out")
    pool_size = metrics.get("size")
    min_interval = max(1, _coerce_int("DB_POOL_LOG_MIN_INTERVAL_SECONDS", 15))
    threshold = max(1, _coerce_int("DB_POOL_LOG_WARN_THRESHOLD", 4))
    now = time.monotonic()
    last_logged = _last_pool_log_at.get(label, 0.0)
    near_limit = checked_out is not None and checked_out >= threshold
    force = force or near_limit or (pool_size is not None and checked_out is not None and pool_size and checked_out >= pool_size)
    if not force and now - last_logged < min_interval:
        return

    _last_pool_log_at[label] = now
    logger.info(
        "[DBPool] %s event=%s checked_out=%s size=%s overflow=%s active_sessions=%s peak_sessions=%s",
        label,
        event_name,
        checked_out,
        metrics.get("size"),
        metrics.get("overflow"),
        _active_session_count,
        _peak_session_count,
    )


def _register_pool_event_listeners(engine: Engine, *, label: str) -> None:
    if getattr(engine, "_arogyaai_pool_listeners_registered", False):
        return

    setattr(engine, "_arogyaai_pool_listeners_registered", True)

    @event.listens_for(engine, "checkout")
    def _on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:  # pragma: no cover - event hook
        _log_pool_snapshot(engine, label=label, event_name="checkout")

    @event.listens_for(engine, "checkin")
    def _on_checkin(dbapi_connection, connection_record) -> None:  # pragma: no cover - event hook
        _log_pool_snapshot(engine, label=label, event_name="checkin")

    @event.listens_for(engine, "invalidate")
    def _on_invalidate(dbapi_connection, connection_record, exception) -> None:  # pragma: no cover - event hook
        _log_pool_snapshot(engine, label=label, event_name="invalidate", force=True)


def _build_engine(url: str, *, application_name: str) -> Engine:
    engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("postgresql"):
        connect_args: dict[str, Any] = {
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "3")),
            "application_name": application_name,
            "keepalives": 1,
            "keepalives_idle": max(15, _coerce_int("DB_TCP_KEEPALIVE_IDLE_SECONDS", 30)),
            "keepalives_interval": max(5, _coerce_int("DB_TCP_KEEPALIVE_INTERVAL_SECONDS", 10)),
            "keepalives_count": max(2, _coerce_int("DB_TCP_KEEPALIVE_COUNT", 5)),
        }
        if "sslmode=" in url and "sslmode=require" in url:
            connect_args["sslmode"] = "require"
        engine_kwargs["connect_args"] = connect_args
        engine_kwargs["pool_size"] = max(1, _coerce_int("DB_POOL_SIZE", 15))
        engine_kwargs["max_overflow"] = max(0, _coerce_int("DB_MAX_OVERFLOW", 25))
        engine_kwargs["pool_timeout"] = max(1, _coerce_int("DB_POOL_TIMEOUT_SECONDS", 10))
        engine_kwargs["pool_recycle"] = max(30, _coerce_int("DB_POOL_RECYCLE_SECONDS", 1800))
        engine_kwargs["pool_use_lifo"] = _coerce_bool("DB_POOL_USE_LIFO", "true")
        engine_kwargs["pool_reset_on_return"] = "rollback"
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **engine_kwargs)
    _register_pool_event_listeners(engine, label=_engine_label(application_name))
    return engine


def _resolve_table_name(mapper: Any = None, clause: Any = None) -> str | None:
    if mapper is not None:
        # SQLAlchemy Table/selectable objects do not support boolean coercion,
        # so mapper fallbacks must use explicit None checks rather than `A or B`.
        selectable = getattr(mapper, "persist_selectable", None)
        if selectable is None:
            selectable = getattr(mapper, "local_table", None)
        if selectable is not None:
            return getattr(selectable, "name", None)

    table = getattr(clause, "table", None)
    if table is not None:
        return getattr(table, "name", None)

    selectable = getattr(clause, "selectable", None)
    if selectable is not None:
        return getattr(selectable, "name", None)

    return getattr(clause, "name", None)


DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
NEON_DATABASE_URL = (
    os.getenv("NEON_DATABASE_URL", os.getenv("ANALYTICS_DATABASE_URL", ""))
    .strip()
)
NEON_DIRECT_URL = (
    os.getenv("NEON_DIRECT_URL", os.getenv("ANALYTICS_DIRECT_URL", ""))
    .strip()
)
ANALYTICS_DB_MODE = _normalize_mode(os.getenv("ANALYTICS_DB_MODE", "primary"))
TIMESCALE_ENABLED = _coerce_bool("TIMESCALE_ENABLED", "true")
ANALYTICS_DB_READ_FALLBACK = _coerce_bool("ANALYTICS_DB_READ_FALLBACK", "true")

primary_engine = _build_engine(DATABASE_URL, application_name="arogyaai-primary")
analytics_engine = _build_engine(NEON_DATABASE_URL or DATABASE_URL, application_name="arogyaai-analytics")
analytics_direct_engine = _build_engine(
    NEON_DIRECT_URL or NEON_DATABASE_URL or DATABASE_URL,
    application_name="arogyaai-analytics-admin",
)

# Backward-compatible alias used across the current codebase.
engine = primary_engine


def external_analytics_enabled() -> bool:
    return bool(NEON_DATABASE_URL)


def analytics_reads_from_primary() -> bool:
    return ANALYTICS_DB_MODE in {"primary", "dual_write"} or not external_analytics_enabled()


def analytics_reads_from_external() -> bool:
    return not analytics_reads_from_primary()


def analytics_dual_write_enabled() -> bool:
    return ANALYTICS_DB_MODE == "dual_write" and external_analytics_enabled()


def analytics_runtime_enabled() -> bool:
    return ANALYTICS_DB_MODE in {"dual_write", "analytics"} and external_analytics_enabled()


def get_analytics_read_engine() -> Engine:
    if analytics_reads_from_primary():
        return primary_engine
    return analytics_engine


def get_analytics_write_engine() -> Engine:
    if analytics_runtime_enabled():
        return analytics_engine
    return primary_engine


def get_analytics_listener_engine() -> Engine:
    if analytics_runtime_enabled():
        return analytics_direct_engine
    return primary_engine


class SessionLifecycleMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.info.setdefault("session_id", uuid.uuid4().hex[:12])
        self.info.setdefault("opened_at_monotonic", time.monotonic())
        self.info.setdefault("closed", False)

        global _active_session_count, _peak_session_count
        with _tracking_lock:
            _active_session_count += 1
            _peak_session_count = max(_peak_session_count, _active_session_count)

    def close(self) -> None:
        closed = bool(self.info.get("closed"))
        try:
            super().close()
        finally:
            if not closed:
                self.info["closed"] = True
                global _active_session_count
                with _tracking_lock:
                    _active_session_count = max(0, _active_session_count - 1)


class TrackedSession(SessionLifecycleMixin, SQLAlchemySession):
    pass


class RoutingSession(SessionLifecycleMixin, SQLAlchemySession):
    def get_bind(self, mapper: Any = None, clause: Any = None, **kwargs: Any) -> Engine:
        table_name = _resolve_table_name(mapper=mapper, clause=clause)
        if table_name in ANALYTICS_TABLES:
            return get_analytics_read_engine()
        return primary_engine


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    class_=RoutingSession,
    expire_on_commit=False,
)
PrimarySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=primary_engine,
    class_=TrackedSession,
    expire_on_commit=False,
)
AnalyticsSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=analytics_engine,
    class_=TrackedSession,
    expire_on_commit=False,
)
AnalyticsReadSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_analytics_read_engine(),
    class_=TrackedSession,
    expire_on_commit=False,
)
AnalyticsDirectSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=analytics_direct_engine,
    class_=TrackedSession,
    expire_on_commit=False,
)
Base = declarative_base()


def log_pool_snapshot(*, force: bool = False) -> None:
    seen: set[str] = set()
    for label, target_engine in (
        ("primary", primary_engine),
        ("analytics", analytics_engine),
        ("analytics_direct", analytics_direct_engine),
    ):
        url = str(target_engine.url)
        if url in seen:
            continue
        seen.add(url)
        _log_pool_snapshot(target_engine, label=label, event_name="snapshot", force=force)


@contextmanager
def session_scope(
    *,
    factory: sessionmaker = SessionLocal,
    label: str | None = None,
) -> Iterator[SQLAlchemySession]:
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        if label:
            logger.warning("[DBSession] rollback label=%s session_id=%s", label, session.info.get("session_id"))
        raise
    finally:
        session.close()


@contextmanager
def primary_session_scope() -> Iterator[SQLAlchemySession]:
    with session_scope(factory=PrimarySessionLocal, label="primary") as session:
        yield session


@contextmanager
def analytics_session_scope(*, direct: bool = False) -> Iterator[SQLAlchemySession]:
    factory = AnalyticsDirectSessionLocal if direct else AnalyticsSessionLocal
    label = "analytics_direct" if direct else "analytics"
    with session_scope(factory=factory, label=label) as session:
        yield session


@contextmanager
def analytics_read_session_scope() -> Iterator[SQLAlchemySession]:
    with session_scope(factory=AnalyticsReadSessionLocal, label="analytics_read") as session:
        yield session


def get_listener_engines() -> list[Engine]:
    engines: list[Engine] = [primary_engine]
    if analytics_runtime_enabled():
        analytics_listener_engine = get_analytics_listener_engine()
        if str(analytics_listener_engine.url) != str(primary_engine.url):
            engines.append(analytics_listener_engine)
    return engines


def dispose_engines() -> None:
    seen: set[str] = set()
    for target_engine in (primary_engine, analytics_engine, analytics_direct_engine):
        url = str(target_engine.url)
        if url in seen:
            continue
        seen.add(url)
        try:
            target_engine.dispose()
        except Exception:
            logger.warning("[DBPool] Failed to dispose engine=%s", url, exc_info=True)


def get_db() -> Iterator[SQLAlchemySession]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
