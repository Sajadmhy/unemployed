"""Alembic environment. Pulls the DB URL and model metadata from the app."""
from sqlalchemy import engine_from_config, pool

from alembic import context

# Import Base + models so Base.metadata knows every table (for autogenerate).
import app.db.models  # noqa: F401
from app.config import settings
from app.db.session import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot ALTER a column - dropping one, changing a type or
            # adding a constraint all require rebuilding the table. Batch mode
            # makes Alembic do that rebuild automatically, so a future migration
            # can be written the same way it would be for any other backend.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
