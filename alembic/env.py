from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  모델 Metadata를 Base.metadata에 등록
from app.models.base import Base

# alembic.ini의 [loggers] 기반 fileConfig는 호출하지 않는다. fileConfig는 프로세스의
# Root Logger 핸들러를 재구성해 애플리케이션(FastAPI Lifespan)과 테스트의 로깅 설정을
# 깨뜨리므로, 이 Feature가 요구하지 않는 로깅 설정을 위해 그 부작용을 감수하지 않는다.
config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """애플리케이션이 이미 만든 Connection이 있으면 그대로 재사용하고, 없으면 alembic.ini의 URL로 새 Engine을 만든다."""
    connection = config.attributes.get("connection")

    if connection is not None:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return

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
