import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL, DATABASE_URL_ENV


def resolve_database_url(environ=None):
    environ = environ if environ is not None else os.environ
    return environ.get(DATABASE_URL_ENV) or DATABASE_URL


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
