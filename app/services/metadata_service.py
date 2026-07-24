"""Week 1 고정 Demo Scope Business Metadata 정적 레지스트리.

대표 재고 질문("현재 재고가 안전재고보다 부족한 제품을 보여줘") 하나에 필요한 최소
Business Metadata만 등록한다. 관리 UI나 Admin DB Schema는 사용하지 않는다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.services.schema_collector import PhysicalMetadataCatalog


class BusinessMetadataMappingError(RuntimeError):
    """레지스트리가 가정하는 물리 Table·Column·FK가 실제 Physical Metadata Catalog에 없을 때 발생한다."""


class MetadataEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    description: str
    sql_hint: str


ENTITY_ALIASES: frozenset[str] = frozenset({"product", "제품", "품목", "상품"})
INVENTORY_CONCEPT_ALIASES: frozenset[str] = frozenset(
    {"inventory", "stock", "재고", "현재 재고", "재고량"}
)
SAFETY_STOCK_CONCEPT_ALIASES: frozenset[str] = frozenset(
    {"safety_stock", "safety stock", "안전재고", "안전 재고", "최소 재고"}
)

_ENTITY = MetadataEntry(
    id="product",
    kind="entity",
    description="제품(Production.Product 1건 = 결과 1행)",
    sql_hint="Production.Product",
)

_DIMENSIONS: tuple[MetadataEntry, ...] = (
    MetadataEntry(
        id="product_id",
        kind="dimension",
        description="제품 ID",
        sql_hint="p.ProductID AS ProductID",
    ),
    MetadataEntry(
        id="product_name",
        kind="dimension",
        description="제품명",
        sql_hint="p.Name AS Name",
    ),
)

_METRICS: tuple[MetadataEntry, ...] = (
    MetadataEntry(
        id="current_inventory",
        kind="metric",
        description=(
            "제품별 현재 재고. Production.ProductInventory에 재고 행이 하나 이상 있는 "
            "제품만 대상으로 위치별 Quantity를 ProductID 단위로 합산한 값이다. 행이 없는 "
            "제품은 모집단에서 제외하며 재고 0 값을 생성하거나 비교하지 않는다."
        ),
        sql_hint="SUM(pi.Quantity) AS CurrentInventory",
    ),
    MetadataEntry(
        id="safety_stock_level",
        kind="metric",
        description="안전재고 기준(Production.Product.SafetyStockLevel)",
        sql_hint="p.SafetyStockLevel AS SafetyStockLevel",
    ),
)

_FILTERS: tuple[MetadataEntry, ...] = (
    MetadataEntry(
        id="below_safety_stock",
        kind="filter",
        description="현재 재고 합계가 안전재고보다 부족한 제품만 남긴다",
        sql_hint="HAVING SUM(pi.Quantity) < p.SafetyStockLevel",
    ),
)

_GRAINS: tuple[MetadataEntry, ...] = (
    MetadataEntry(
        id="product",
        kind="grain",
        description="결과 1행 = 제품 1건",
        sql_hint="GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
    ),
)

_JOINS: tuple[MetadataEntry, ...] = (
    MetadataEntry(
        id="product_to_product_inventory",
        kind="join",
        description="Product와 ProductInventory 사이의 승인된 Physical FK Join",
        sql_hint=(
            "Production.Product AS p INNER JOIN Production.ProductInventory AS pi "
            "ON p.ProductID = pi.ProductID"
        ),
    ),
)


def all_entries() -> list[MetadataEntry]:
    """Week 1 고정 Demo Scope에 등록된 모든 Business Metadata를 반환한다."""
    return [_ENTITY, *_DIMENSIONS, *_METRICS, *_FILTERS, *_GRAINS, *_JOINS]


_REQUIRED_TABLE_COLUMNS: dict[tuple[str, str], tuple[str, ...]] = {
    ("Production", "Product"): ("ProductID", "Name", "SafetyStockLevel"),
    ("Production", "ProductInventory"): ("ProductID", "Quantity"),
}
_REQUIRED_FK = {
    "source_schema": "Production",
    "source_table": "ProductInventory",
    "source_columns": ("ProductID",),
    "target_schema": "Production",
    "target_table": "Product",
    "target_columns": ("ProductID",),
}


def validate_physical_mapping(catalog: PhysicalMetadataCatalog) -> None:
    """레지스트리가 가정하는 Table·Column·FK가 실제 Catalog에 있는지 확인한다.

    불일치하면 BusinessMetadataMappingError를 던져 ASGI Startup을 완료시키지 않는다(Fail Closed).
    """
    for (schema_name, table_name), required_columns in _REQUIRED_TABLE_COLUMNS.items():
        table = catalog.get_table(schema_name, table_name)
        if table is None:
            raise BusinessMetadataMappingError(
                f"Required table not found in Physical Metadata Catalog: {schema_name}.{table_name}"
            )
        actual_columns = {column.column_name for column in table.columns}
        missing_columns = [c for c in required_columns if c not in actual_columns]
        if missing_columns:
            raise BusinessMetadataMappingError(
                f"Required columns not found in {schema_name}.{table_name}: {missing_columns}"
            )

    for fk in catalog.foreign_keys:
        if (
            fk.source_schema == _REQUIRED_FK["source_schema"]
            and fk.source_table == _REQUIRED_FK["source_table"]
            and tuple(fk.source_columns) == _REQUIRED_FK["source_columns"]
            and fk.target_schema == _REQUIRED_FK["target_schema"]
            and fk.target_table == _REQUIRED_FK["target_table"]
            and tuple(fk.target_columns) == _REQUIRED_FK["target_columns"]
        ):
            return

    raise BusinessMetadataMappingError(
        "Required physical foreign key not found: "
        "Production.ProductInventory.ProductID -> Production.Product.ProductID"
    )
