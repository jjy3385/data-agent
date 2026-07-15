import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

load_dotenv(env_path)

host = os.environ["TARGET_DB_HOST"]
port = os.environ["TARGET_DB_PORT"]
database = os.environ["TARGET_DB_NAME"]
user = os.environ["TARGET_DB_USER"]
driver = os.environ["TARGET_DB_DRIVER"]
password = os.environ["TARGET_DB_PASSWORD"]
encrypt = os.environ["TARGET_DB_ENCRYPT"]
trust_server_certificate = os.environ[
    "TARGET_DB_TRUST_SERVER_CERTIFICATE"
]

connection_string = (
    f"DRIVER={{{driver}}};"
    f"SERVER={host},{port};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={{{password}}};"
    f"Encrypt={encrypt};"
    f"TrustServerCertificate={trust_server_certificate};"
    "ApplicationIntent=ReadOnly;"
)

def get_connection() -> pyodbc.Connection:
    return pyodbc.connect(
        connection_string,
        timeout=5,
        autocommit=True,
    )

if __name__ == "__main__":
    connection = get_connection()

    try:
        print("database connection: OK")
    finally:
        connection.close()