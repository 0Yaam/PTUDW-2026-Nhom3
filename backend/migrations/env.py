from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from culinary_blog_api.auth import RefreshToken, User  # noqa: F401
from culinary_blog_api.categories import Category  # noqa: F401
from culinary_blog_api.config import get_settings
from culinary_blog_api.db import Base
from culinary_blog_api.recipes import Recipe  # noqa: F401

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    get_settings().database_url.replace("postgresql+asyncpg", "postgresql+psycopg"),
)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
