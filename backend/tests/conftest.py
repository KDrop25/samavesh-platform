import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from app import security
from app.crypto import EncryptedText
from app.db import Base, get_db, make_engine, utcnow
from app.main import app
from app.models.user import DevEmail, Role, User


class Widget(Base):
    """Test-only audited model, so the audit listener can be tested before real modules exist."""

    __tablename__ = "test_widgets"
    __audited__ = True

    name: Mapped[str] = mapped_column(String(50))
    secret: Mapped[str | None] = mapped_column(EncryptedText)


@pytest.fixture(autouse=True)
def fast_scrypt(monkeypatch):
    monkeypatch.setitem(security.SCRYPT, "n", 2**4)


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    from app.routers.grievances import _hits

    _hits.clear()


@pytest.fixture
def engine():
    # CI sets TEST_DATABASE_URL to Postgres to prove the same code runs on both databases.
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    kwargs = {"poolclass": StaticPool} if url.startswith("sqlite") else {}
    engine = make_engine(url, **kwargs)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(engine):
    def override():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db):
    """Create a verified user directly and return (user, auth headers)."""

    def _make(role: Role, email: str | None = None, **kw):
        user = User(
            email=email or f"{role.value}@example.com",
            full_name=kw.pop("full_name", role.value.replace("_", " ").title()),
            role=role,
            password_hash=security.hash_password("correct horse battery"),
            email_verified_at=utcnow(),
            **kw,
        )
        db.add(user)
        db.commit()
        return user, {"Authorization": f"Bearer {security.create_token(user)}"}

    return _make


@pytest.fixture
def last_code(db):
    """Read the newest 6-digit code out of the dev outbox."""

    def _code(email: str) -> str:
        body = db.scalar(select(DevEmail.body).where(DevEmail.to == email).order_by(DevEmail.id.desc()))
        return re.search(r"\b\d{6}\b", body).group()

    return _code
