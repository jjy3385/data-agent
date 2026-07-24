import pytest

from app.services import metadata_service
from app.services.schema_collector import PhysicalMetadataCatalog
from tests.conftest import FAKE_INSPECT_SCHEMA_RESULT


def test_all_entries_covers_every_kind():
    entries = metadata_service.all_entries()
    kinds = {entry.kind for entry in entries}
    assert kinds == {"entity", "dimension", "metric", "filter", "grain", "join"}
    assert len(entries) == 8

    # 각 kind(entity/dimension/metric/filter/grain/join) 그룹 안에서는 id가 유일해야 한다.
    # entity와 grain은 서로 다른 MetadataContext 그룹이라 둘 다 "product"를 id로 써도 된다.
    ids_by_kind: dict[str, list[str]] = {}
    for entry in entries:
        ids_by_kind.setdefault(entry.kind, []).append(entry.id)
    for kind, ids in ids_by_kind.items():
        assert len(ids) == len(set(ids)), f"duplicate id within kind={kind}: {ids}"


def test_validate_physical_mapping_passes_with_fake_catalog():
    catalog = PhysicalMetadataCatalog(
        schemas=FAKE_INSPECT_SCHEMA_RESULT["schemas"],
        foreign_keys=FAKE_INSPECT_SCHEMA_RESULT["foreign_keys"],
    )
    metadata_service.validate_physical_mapping(catalog)


def test_validate_physical_mapping_rejects_missing_table():
    catalog = PhysicalMetadataCatalog(schemas=[], foreign_keys=[])
    with pytest.raises(metadata_service.BusinessMetadataMappingError, match="Product"):
        metadata_service.validate_physical_mapping(catalog)


def test_validate_physical_mapping_rejects_missing_column():
    schemas = [
        {
            "schema_name": "Production",
            "tables": [
                {
                    "table_name": "Product",
                    "description": None,
                    "columns": [
                        {
                            "column_name": "ProductID",
                            "data_type": "int",
                            "is_nullable": False,
                            "ordinal_position": 1,
                            "description": None,
                        }
                    ],
                    "primary_key": {"columns": ["ProductID"]},
                },
                FAKE_INSPECT_SCHEMA_RESULT["schemas"][0]["tables"][1],
            ],
        }
    ]
    catalog = PhysicalMetadataCatalog(
        schemas=schemas, foreign_keys=FAKE_INSPECT_SCHEMA_RESULT["foreign_keys"]
    )
    with pytest.raises(metadata_service.BusinessMetadataMappingError, match="Name"):
        metadata_service.validate_physical_mapping(catalog)


def test_validate_physical_mapping_rejects_missing_foreign_key():
    catalog = PhysicalMetadataCatalog(
        schemas=FAKE_INSPECT_SCHEMA_RESULT["schemas"], foreign_keys=[]
    )
    with pytest.raises(metadata_service.BusinessMetadataMappingError, match="foreign key"):
        metadata_service.validate_physical_mapping(catalog)
