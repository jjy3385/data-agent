from typing import Any

from pydantic import BaseModel


class ColumnMetadata(BaseModel):
    column_name: str
    data_type: str
    is_nullable: bool
    ordinal_position: int
    description: str | None = None


class PrimaryKeyMetadata(BaseModel):
    columns: list[str]


class TableMetadata(BaseModel):
    table_name: str
    description: str | None = None
    columns: list[ColumnMetadata]
    primary_key: PrimaryKeyMetadata | None = None


class SchemaMetadata(BaseModel):
    schema_name: str
    tables: list[TableMetadata]


class ForeignKeyMetadata(BaseModel):
    foreign_key_name: str
    source_schema: str
    source_table: str
    source_columns: list[str]
    target_schema: str
    target_table: str
    target_columns: list[str]


class PhysicalMetadataCatalog(BaseModel):
    """inspect_schema 결과로 구성한 in-memory Physical Metadata Catalog. Admin DB에 저장하지 않는다."""

    schemas: list[SchemaMetadata]
    foreign_keys: list[ForeignKeyMetadata]

    def get_table(self, schema_name: str, table_name: str) -> TableMetadata | None:
        for schema in self.schemas:
            if schema.schema_name == schema_name:
                for table in schema.tables:
                    if table.table_name == table_name:
                        return table
        return None


def build_physical_metadata_catalog(inspect_schema_result: dict[str, Any]) -> PhysicalMetadataCatalog:
    return PhysicalMetadataCatalog(
        schemas=inspect_schema_result.get("schemas", []),
        foreign_keys=inspect_schema_result.get("foreign_keys", []),
    )
