from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


SessionFactory = sessionmaker[Session]


def create_session_factory(database_url: str) -> tuple[Engine, SessionFactory]:
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, factory


def get_database_session(request: Request) -> Generator[Session, None, None]:
    session_factory: SessionFactory = request.app.state.session_factory
    with session_factory() as session:
        yield session
