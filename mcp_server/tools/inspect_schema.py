from typing import Any

import anyio
import pyodbc

from mcp_server import db

_SCHEMA_EXCLUSION_CLAUSE = (
    "s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest') AND s.name NOT LIKE 'db\\_%' ESCAPE '\\'"
)

_COLUMNS_QUERY = f"""
SELECT s.name, t.name, t.object_id, c.column_id, c.name, ty.name,
       c.max_length, c.precision, c.scale, c.is_nullable
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types ty ON c.system_type_id = ty.system_type_id AND ty.user_type_id = ty.system_type_id
WHERE t.is_ms_shipped = 0 AND {_SCHEMA_EXCLUSION_CLAUSE}
ORDER BY s.name, t.name, c.column_id
"""

_PRIMARY_KEY_QUERY = f"""
SELECT s.name, t.name, c.name, ic.key_ordinal
FROM sys.key_constraints kc
JOIN sys.tables t ON kc.parent_object_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE kc.type = 'PK' AND t.is_ms_shipped = 0 AND {_SCHEMA_EXCLUSION_CLAUSE}
ORDER BY s.name, t.name, ic.key_ordinal
"""

_FOREIGN_KEY_QUERY = f"""
SELECT fk.object_id, fk.name, ps.name, pt.name, pc.name, rs.name, rt.name, rc.name, fkc.constraint_column_id
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.tables pt ON fkc.parent_object_id = pt.object_id
JOIN sys.schemas ps ON pt.schema_id = ps.schema_id
JOIN sys.columns pc ON fkc.parent_object_id = pc.object_id AND fkc.parent_column_id = pc.column_id
JOIN sys.tables rt ON fkc.referenced_object_id = rt.object_id
JOIN sys.schemas rs ON rt.schema_id = rs.schema_id
JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id
WHERE pt.is_ms_shipped = 0 AND rt.is_ms_shipped = 0
  AND {_SCHEMA_EXCLUSION_CLAUSE.replace('s.name', 'ps.name')}
  AND {_SCHEMA_EXCLUSION_CLAUSE.replace('s.name', 'rs.name')}
ORDER BY fk.object_id, fkc.constraint_column_id
"""

_DESCRIPTION_QUERY = f"""
SELECT s.name, t.name, ep.minor_id, CAST(ep.value AS NVARCHAR(MAX))
FROM sys.extended_properties ep
JOIN sys.tables t ON ep.major_id = t.object_id
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE ep.class = 1 AND ep.name = 'MS_Description' AND t.is_ms_shipped = 0 AND {_SCHEMA_EXCLUSION_CLAUSE}
"""


def _format_data_type(type_name: str, max_length: int, precision: int, scale: int) -> str:
    lname = type_name.lower()
    if lname in ("nvarchar", "nchar"):
        return f"{type_name}(max)" if max_length == -1 else f"{type_name}({max_length // 2})"
    if lname in ("varchar", "char", "binary", "varbinary"):
        return f"{type_name}(max)" if max_length == -1 else f"{type_name}({max_length})"
    if lname in ("decimal", "numeric"):
        return f"{type_name}({precision},{scale})"
    if lname in ("datetime2", "time", "datetimeoffset"):
        return f"{type_name}({scale})"
    return type_name


def _inspect_schema_sync(correlation_id: str) -> dict[str, Any]:
    connection = db.get_connection()
    try:
        try:
            connection.timeout = db.SCHEMA_INSPECTION_TIMEOUT_SECONDS
            cursor = connection.cursor()

            cursor.execute(_COLUMNS_QUERY)
            column_rows = cursor.fetchall()

            cursor.execute(_PRIMARY_KEY_QUERY)
            pk_rows = cursor.fetchall()

            cursor.execute(_FOREIGN_KEY_QUERY)
            fk_rows = cursor.fetchall()

            cursor.execute(_DESCRIPTION_QUERY)
            description_rows = cursor.fetchall()
        except pyodbc.Error as exc:
            if db.is_timeout_error(exc):
                raise TimeoutError("Schema inspection timeout exceeded") from exc
            raise RuntimeError("Schema inspection failed") from exc
    finally:
        connection.close()

    table_descriptions: dict[tuple[str, str], str] = {}
    column_descriptions: dict[tuple[str, str, int], str] = {}
    for schema_name, table_name, minor_id, description in description_rows:
        if minor_id == 0:
            table_descriptions[(schema_name, table_name)] = description
        else:
            column_descriptions[(schema_name, table_name, minor_id)] = description

    tables: dict[tuple[str, str], dict[str, Any]] = {}
    table_order: list[tuple[str, str]] = []
    for (
        schema_name,
        table_name,
        _object_id,
        column_id,
        column_name,
        type_name,
        max_length,
        precision,
        scale,
        is_nullable,
    ) in column_rows:
        key = (schema_name, table_name)
        if key not in tables:
            tables[key] = {
                "table_name": table_name,
                "description": table_descriptions.get(key),
                "columns": [],
                "primary_key": None,
            }
            table_order.append(key)

        ordinal_position = len(tables[key]["columns"]) + 1
        tables[key]["columns"].append(
            {
                "column_name": column_name,
                "data_type": _format_data_type(type_name, max_length, precision, scale),
                "is_nullable": bool(is_nullable),
                "ordinal_position": ordinal_position,
                "description": column_descriptions.get((schema_name, table_name, column_id)),
            }
        )

    primary_keys: dict[tuple[str, str], list[str]] = {}
    for schema_name, table_name, column_name, _key_ordinal in pk_rows:
        primary_keys.setdefault((schema_name, table_name), []).append(column_name)

    for key, columns in primary_keys.items():
        if key in tables:
            tables[key]["primary_key"] = {"columns": columns}

    schemas: dict[str, list[dict[str, Any]]] = {}
    schema_order: list[str] = []
    for schema_name, table_name in table_order:
        if schema_name not in schemas:
            schemas[schema_name] = []
            schema_order.append(schema_name)
        schemas[schema_name].append(tables[(schema_name, table_name)])

    schemas_list = [{"schema_name": name, "tables": schemas[name]} for name in schema_order]

    foreign_keys_map: dict[int, dict[str, Any]] = {}
    fk_order: list[int] = []
    for (
        fk_object_id,
        fk_name,
        source_schema,
        source_table,
        source_column,
        target_schema,
        target_table,
        target_column,
        _constraint_column_id,
    ) in fk_rows:
        if fk_object_id not in foreign_keys_map:
            foreign_keys_map[fk_object_id] = {
                "foreign_key_name": fk_name,
                "source_schema": source_schema,
                "source_table": source_table,
                "source_columns": [],
                "target_schema": target_schema,
                "target_table": target_table,
                "target_columns": [],
            }
            fk_order.append(fk_object_id)
        foreign_keys_map[fk_object_id]["source_columns"].append(source_column)
        foreign_keys_map[fk_object_id]["target_columns"].append(target_column)

    foreign_keys = [foreign_keys_map[object_id] for object_id in fk_order]

    return {
        "correlation_id": correlation_id,
        "schemas": schemas_list,
        "foreign_keys": foreign_keys,
        "summary": {
            "schema_count": len(schemas_list),
            "table_count": sum(len(schema["tables"]) for schema in schemas_list),
        },
    }


async def inspect_schema(correlation_id: str) -> dict[str, Any]:
    return await anyio.to_thread.run_sync(_inspect_schema_sync, correlation_id)
