class AdminDBUnavailableError(RuntimeError):
    """Admin DB 경로 접근, Engine 생성, Migration 또는 Schema 확인 실패 시 발생한다."""
