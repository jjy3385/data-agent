import db
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("adventureworks-db")


@mcp.tool()
def get_product_by_id(product_id: int) -> dict[str, object]:
    """제품 ID로 AdventureWorks 제품 기본 정보를 조회한다.

    Args:
        product_id: 조회할 제품의 양수 ID
    """
    product = db.get_product_by_id(product_id)

    if product is None:
        return {
            "found": False,
            "product_id": product_id,
        }

    return {
        "found": True,
        "product": product,
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
