import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL_ENV, DATABASE_URL_EXAMPLE


def resolve_database_url(environ=None):
    environ = environ if environ is not None else os.environ
    database_url = environ.get(DATABASE_URL_ENV)
    if not database_url:
        raise RuntimeError(
            f"{DATABASE_URL_ENV} is required. Example: {DATABASE_URL_EXAMPLE}"
        )
    return database_url


SQLALCHEMY_DATABASE_URL = resolve_database_url()


def create_engine_kwargs(database_url: str):
    if database_url.startswith('sqlite'):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(SQLALCHEMY_DATABASE_URL, **create_engine_kwargs(SQLALCHEMY_DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
