"""Apply the plain-SQL migrations in backend/migrations, in filename order.

Each file runs in its own transaction and is recorded in `schema_migrations`,
so running this again only applies files it hasn't seen.

Usage: uv run python -m chiral.db.migrate
"""

from pathlib import Path

import psycopg

from chiral.config import get_settings

# backend/src/chiral/db/migrate.py -> parents[3] is backend/.
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def apply_migrations(database_url: str, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations and return the filenames this call applied."""
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        done = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
        for path in sorted(migrations_dir.glob("*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied


def main() -> None:
    applied = apply_migrations(get_settings().database_url)
    for name in applied:
        print(f"applied {name}")
    if not applied:
        print("database is up to date")


if __name__ == "__main__":
    main()
