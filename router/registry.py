from __future__ import annotations

import os
from typing import List

import time
from sqlalchemy import Float, Integer, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/models.db")
# Recognised model types for routing
VALID_MODEL_TYPES = {
    "local",
    "openai",
    "llm-d",
    "anthropic",
    "google",
    "openrouter",
    "grok",
    "venice",
}


class Base(DeclarativeBase):
    pass


engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
SessionLocal = sessionmaker(bind=engine)


class ModelEntry(Base):  # type: ignore[misc]
    """ORM model for the registry."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)


class AgentEntry(Base):  # type: ignore[misc]
    """ORM model for registered agents."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    models: Mapped[str] = mapped_column(String, nullable=False)
    last_heartbeat: Mapped[float] = mapped_column(Float, nullable=False)


def create_tables() -> None:
    """Create registry tables if they do not exist."""

    Base.metadata.create_all(engine)


def get_session() -> Session:
    """Return a new SQLAlchemy session."""

    return SessionLocal()


def list_models(session: Session) -> List[ModelEntry]:
    """Return all model entries."""

    return session.query(ModelEntry).all()


def upsert_agent(session: Session, name: str, endpoint: str, models: List[str]) -> None:
    """Insert or update an agent entry."""

    now = time.time()
    agent = session.query(AgentEntry).filter_by(name=name).first()
    if agent is None:
        agent = AgentEntry(
            name=name,
            endpoint=endpoint,
            models=",".join(models),
            last_heartbeat=now,
        )
        session.add(agent)
    else:
        agent.endpoint = endpoint
        agent.models = ",".join(models)
        agent.last_heartbeat = now
    session.commit()


def update_heartbeat(session: Session, name: str) -> None:
    """Update an agent's heartbeat timestamp."""

    agent = session.query(AgentEntry).filter_by(name=name).first()
    if agent is not None:
        agent.last_heartbeat = time.time()
        session.commit()


def upsert_model(session: Session, name: str, type: str, endpoint: str) -> None:
    """Insert or update a model entry.

    Parameters
    ----------
    session:
        Active database session.
    name:
        Model identifier.
    type:
        Backend type (one of ``VALID_MODEL_TYPES``).
    endpoint:
        Base URL for the model backend.
    """

    model = session.query(ModelEntry).filter_by(name=name).first()
    if model is None:
        model = ModelEntry(name=name, type=type, endpoint=endpoint)
        session.add(model)
    else:
        model.type = type
        model.endpoint = endpoint
    session.commit()


def clear_models(session: Session) -> None:
    """Remove all model entries."""

    session.query(ModelEntry).delete()
    session.commit()


def list_agents(session: Session) -> List[AgentEntry]:
    """Return all registered agents."""

    return session.query(AgentEntry).all()
