"""Shared fixtures. Integration tests run against a throwaway `<dbname>_test` database."""

import os

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from chiral.config import get_settings


def _test_database_url() -> str:
    """TEST_DATABASE_URL if set, otherwise DATABASE_URL with `_test` added to the name."""
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    dev_url = get_settings().database_url
    dbname = conninfo_to_dict(dev_url).get("dbname", "chiral")
    return make_conninfo(dev_url, dbname=f"{dbname}_test")


@pytest.fixture(scope="session")
def database_url() -> str:
    """Create a fresh, empty test database and return its connection string."""
    url = _test_database_url()
    dbname = str(conninfo_to_dict(url)["dbname"])
    if not dbname.endswith("_test"):
        pytest.exit(f"Refusing to drop {dbname!r}: test database names must end in _test")

    try:
        with psycopg.connect(
            make_conninfo(url, dbname="postgres"), autocommit=True, connect_timeout=5
        ) as conn:
            name = sql.Identifier(dbname)
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
            conn.execute(sql.SQL("CREATE DATABASE {}").format(name))
    except psycopg.OperationalError as exc:
        if os.environ.get("CI"):
            pytest.fail(f"CI needs Postgres for the integration tests: {exc}")
        pytest.skip(f"Postgres is not reachable, start it with `make up` ({exc})")
    return url
