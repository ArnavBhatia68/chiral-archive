import psycopg
import pytest

from chiral.db.migrate import apply_migrations

pytestmark = pytest.mark.integration


def test_migrations_enable_pgvector(database_url):
    apply_migrations(database_url)

    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        assert row is not None, "pgvector extension was not created"
        # Phase 4's progress-filtered search relies on iterative index scans (pgvector 0.8+).
        major_minor = tuple(int(part) for part in row[0].split(".")[:2])
        assert major_minor >= (0, 8), f"pgvector {row[0]} is too old"

        (distance,) = conn.execute("SELECT '[1,0,0]'::vector <=> '[0,1,0]'::vector").fetchone()
        assert distance == pytest.approx(1.0)  # cosine distance of orthogonal vectors


def test_migrations_are_idempotent(database_url):
    apply_migrations(database_url)

    assert apply_migrations(database_url) == []


def test_a_migration_file_can_hold_several_statements(database_url, tmp_path):
    (tmp_path / "0001_two_tables.sql").write_text(
        "CREATE TABLE runner_check_a (id int);\nCREATE TABLE runner_check_b (id int);\n"
    )

    assert apply_migrations(database_url, tmp_path) == ["0001_two_tables.sql"]

    with psycopg.connect(database_url) as conn:
        tables = conn.execute(
            "SELECT to_regclass('runner_check_a'), to_regclass('runner_check_b')"
        ).fetchone()
        assert tables == ("runner_check_a", "runner_check_b")


def test_a_failed_migration_is_rolled_back(database_url, tmp_path):
    (tmp_path / "0001_broken.sql").write_text(
        "CREATE TABLE half_done (id int);\nSELECT * FROM no_such_table;\n"
    )

    with pytest.raises(psycopg.errors.UndefinedTable):
        apply_migrations(database_url, tmp_path)

    with psycopg.connect(database_url) as conn:
        (table,) = conn.execute("SELECT to_regclass('half_done')").fetchone()
        assert table is None, "the first statement should have been rolled back"
        (recorded,) = conn.execute(
            "SELECT count(*) FROM schema_migrations WHERE filename = '0001_broken.sql'"
        ).fetchone()
        assert recorded == 0
