from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.db.schema import prepare_admin_db_schema
from app.db.session import build_admin_db_engine
from main import app as main_app

_REQUIRED_TABLES = {"users", "table_policies", "audit_logs", "error_reports"}


def test_startup_prepares_admin_db_and_shutdown_disposes_engine(admin_db_path):
    with TestClient(main_app) as client:
        response = client.get("/health")
        assert response.status_code == 200

        engine = main_app.state.admin_db_engine
        assert engine is not None
        assert main_app.state.admin_db_sessionmaker is not None

        existing_tables = set(inspect(engine).get_table_names())
        assert _REQUIRED_TABLES.issubset(existing_tables)

    assert admin_db_path.exists()


def test_repeated_migration_is_idempotent_and_preserves_existing_data(tmp_path):
    db_path = str(tmp_path / "admin.db")

    engine = build_admin_db_engine(db_path)
    prepare_admin_db_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (slack_user_id, is_active, role) "
                "VALUES ('U1', 1, 'supply_risk_analyst')"
            )
        )
    engine.dispose()

    # 두 번째 애플리케이션 시작을 흉내낸다: 같은 파일에 새 Engine으로 다시 Schema를 준비한다.
    engine2 = build_admin_db_engine(db_path)
    prepare_admin_db_schema(engine2)

    with engine2.connect() as connection:
        rows = connection.execute(text("SELECT slack_user_id FROM users")).fetchall()
    engine2.dispose()

    assert [row[0] for row in rows] == ["U1"]


def test_head_revision_matches_single_migration_script():
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    script = ScriptDirectory.from_config(config)
    assert script.get_current_head() == "0001"
