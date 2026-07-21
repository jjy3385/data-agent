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
trust_server_certificate = os.environ["TARGET_DB_TRUST_SERVER_CERTIFICATE"]

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


def get_product_by_id(product_id: int) -> dict[str, object] | None:
    if product_id <= 0:
        raise ValueError("product_id must be greater than 0")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT
                    ProductID,
                    Name,
                    ProductNumber,
                    Color,
                    ListPrice,
                    SellStartDate,
                    SellEndDate
                FROM Production.Product
                WHERE ProductID = ?;
                """,
                product_id,
            )

            row = cursor.fetchone()

            if row is None:
                return None

            (
                product_id,
                name,
                product_number,
                color,
                list_price,
                sell_start_date,
                sell_end_date,
            ) = row

            return {
                "product_id": product_id,
                "name": name,
                "product_number": product_number,
                "color": color,
                "list_price": str(list_price),
                "sell_start_date": sell_start_date.isoformat(),
                "sell_end_date": (
                    sell_end_date.isoformat() if sell_end_date is not None else None
                ),
            }
        finally:
            cursor.close()
    finally:
        connection.close()


if __name__ == "__main__":
    product = get_product_by_id(1)
    print(product)
