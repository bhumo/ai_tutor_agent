import sqlite3

import pytest
from sqlalchemy import create_engine, text

from database.models import enable_sqlite_foreign_keys, resolve_database_url


def test_database_defaults_to_local_sqlite():
    assert resolve_database_url({}) == "sqlite:///./ai_tutor.db"


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_postgres_urls_select_psycopg_driver(prefix):
    result = resolve_database_url({"DATABASE_URL": prefix + "u:p@db/app"})
    assert result == "postgresql+psycopg://u:p@db/app"


def test_production_rejects_sqlite():
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        resolve_database_url({"APP_ENV": "production", "DATABASE_URL": "sqlite:///prod.db"})


def test_sqlite_foreign_keys_are_enabled():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
