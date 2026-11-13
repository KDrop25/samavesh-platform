import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Always hands back timezone-aware UTC. SQLite drops tzinfo; Postgres keeps it."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class Base(DeclarativeBase):
    # Every Mapped[datetime] is UTC-aware; every enum is a plain VARCHAR on both databases.
    type_annotation_map = {
        datetime: UTCDateTime,
        enum.Enum: Enum(enum.Enum, native_enum=False, length=32),
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


def make_engine(url: str, **kwargs):
    sqlite = url.startswith("sqlite")
    engine = create_engine(url, connect_args={"check_same_thread": False} if sqlite else {}, **kwargs)
    if sqlite:
        # SQLite ignores foreign keys unless told otherwise; Postgres always enforces them.
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(get_settings().sqlalchemy_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
