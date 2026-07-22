from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import health
from main import app as main_app


def test_health_returns_200_and_exact_ok_body():
    test_app = FastAPI()
    test_app.include_router(health.router)

    with TestClient(test_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_main_app_health_returns_200_and_exact_ok_body(admin_db_path):
    # main_app은 실제 Lifespan(Admin DB 준비 포함)을 실행하므로 ADMIN_DB_PATH를 임시 경로로
    # 격리해 저장소의 실제 data/admin.db를 오염시키지 않는다.
    with TestClient(main_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
