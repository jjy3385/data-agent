import pytest

from app.services import context_builder, metadata_service
from app.services.sql_guardrail import SqlRejectedError, validate

_CONTEXT = context_builder.build(metadata_service.all_entries())

_GOOD_SQL = (
    "SELECT TOP (100) p.ProductID AS ProductID, p.Name AS Name, "
    "SUM(pi.Quantity) AS CurrentInventory, p.SafetyStockLevel AS SafetyStockLevel\n"
    "FROM Production.Product AS p\n"
    "INNER JOIN Production.ProductInventory AS pi ON p.ProductID = pi.ProductID\n"
    "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n"
    "HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n"
    "ORDER BY p.ProductID ASC"
)


def test_representative_aggregate_sql_with_current_inventory_alias_is_accepted():
    """규칙 9 앞에서 규칙 10(출력 Alias 분류)이 먼저 실행되어야 CurrentInventory가 통과한다."""
    result = validate(_GOOD_SQL, _CONTEXT)
    assert "CurrentInventory" in result
    assert result.rstrip(";") == _GOOD_SQL


def test_trailing_semicolon_is_stripped():
    assert validate(_GOOD_SQL + ";", _CONTEXT) == _GOOD_SQL


def test_bracket_qualified_table_and_alias_is_accepted():
    sql = _GOOD_SQL.replace("Production.Product AS p", "[Production].[Product] AS p")
    validate(sql, _CONTEXT)


@pytest.mark.parametrize(
    ("name", "sql"),
    [
        ("multiple_statements", _GOOD_SQL + "; SELECT 1"),
        ("multiple_trailing_semicolons", _GOOD_SQL + ";;"),
        ("string_literal", _GOOD_SQL + " AND p.Name = 'x'"),
        ("line_comment", _GOOD_SQL + "\n-- comment"),
        ("block_comment", _GOOD_SQL.replace("SELECT TOP", "SELECT /* c */ TOP")),
        ("subquery_second_select", _GOOD_SQL.replace(
            "ON p.ProductID = pi.ProductID",
            "ON p.ProductID = (SELECT ProductID FROM Production.ProductInventory)",
        )),
        ("forbidden_keyword_insert", _GOOD_SQL.replace("SELECT TOP", "INSERT INTO x SELECT TOP")),
        ("forbidden_keyword_union", _GOOD_SQL + " UNION SELECT 1"),
        ("missing_top", _GOOD_SQL.replace("TOP (100) ", "")),
        ("top_above_maximum", _GOOD_SQL.replace("TOP (100)", "TOP (500)")),
        ("wildcard_select_star", _GOOD_SQL.replace("p.ProductID AS ProductID, ", "*, ")),
        ("wildcard_trailing", _GOOD_SQL.replace(
            "p.SafetyStockLevel AS SafetyStockLevel", "p.SafetyStockLevel AS SafetyStockLevel, p.*"
        )),
        ("disallowed_table", _GOOD_SQL.replace("Production.ProductInventory", "Production.SalesOrderHeader")),
        ("implicit_table_alias_no_as", _GOOD_SQL.replace("Production.Product AS p", "Production.Product p")),
        ("unapproved_output_alias", _GOOD_SQL.replace("AS CurrentInventory", "AS TotalStock")),
        ("unapproved_column", _GOOD_SQL.replace(
            "p.SafetyStockLevel AS SafetyStockLevel", "p.ListPrice AS SafetyStockLevel"
        )),
        ("unapproved_identifier_in_where", _GOOD_SQL + " AND p.Color IS NOT NULL"),
        ("missing_order_by", _GOOD_SQL.split("ORDER BY")[0].rstrip()),
        ("order_by_not_product_id_first", _GOOD_SQL.replace(
            "ORDER BY p.ProductID ASC", "ORDER BY p.Name ASC, p.ProductID ASC"
        )),
        ("order_by_wrong_direction", _GOOD_SQL.replace("ORDER BY p.ProductID ASC", "ORDER BY p.ProductID DESC")),
    ],
)
def test_rejected_sql_cases(name, sql):
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_blank_sql_is_rejected():
    with pytest.raises(SqlRejectedError):
        validate("   ", _CONTEXT)


# --- Codex 발견 3: 고정 Demo Scope 최소 의미 검증(기존 12개 구조 규칙을 보강) -----------------
# QueryPlan에서 below_safety_stock Filter를 강제해도(plan_validator) LLM이 SQL 생성 단계에서
# 그 조건을 SQL 문자열에 반영하지 않을 수 있으므로, 실제로 안전재고 미달 조건과 필수
# Table·Join·집계·출력 Alias가 SQL 문자열 자체에 있는지 별도로 확인한다.
@pytest.mark.parametrize(
    ("name", "sql"),
    [
        (
            "missing_having_clause",
            _GOOD_SQL.replace("HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n", ""),
        ),
        (
            "having_direction_reversed",
            _GOOD_SQL.replace(
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel",
                "HAVING SUM(pi.Quantity) > p.SafetyStockLevel",
            ),
        ),
        (
            "current_inventory_not_computed_with_sum",
            _GOOD_SQL.replace("SUM(pi.Quantity) AS CurrentInventory", "pi.Quantity AS CurrentInventory").replace(
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel", "HAVING pi.Quantity < p.SafetyStockLevel"
            ),
        ),
        (
            "missing_required_join",
            _GOOD_SQL.replace("INNER JOIN Production.ProductInventory AS pi ON p.ProductID = pi.ProductID\n", ""),
        ),
        (
            "missing_required_table_productinventory",
            _GOOD_SQL.replace("Production.ProductInventory", "Production.Product"),
        ),
        (
            "missing_current_inventory_output_alias",
            _GOOD_SQL.replace("SUM(pi.Quantity) AS CurrentInventory, ", ""),
        ),
        (
            "missing_safety_stock_level_output_alias",
            _GOOD_SQL.replace(", p.SafetyStockLevel AS SafetyStockLevel", ""),
        ),
    ],
)
def test_demo_scope_semantic_checks_reject_incomplete_sql(name, sql):
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_representative_sql_still_passes_after_demo_scope_semantic_checks():
    """정상 대표 SQL은 새로 추가된 고정 Demo Scope 의미 검증을 포함해 계속 통과해야 한다."""
    assert validate(_GOOD_SQL, _CONTEXT) == _GOOD_SQL


# --- Codex 재검토 발견: 잘못된 JOIN이 SQL Guardrail을 우회하는 문제 --------------------------
# Table Alias를 alias -> table 매핑으로 관리해, Alias 문자열이 등록되어 있다는 사실만으로
# Join·집계·HAVING을 인정하지 않고 실제로 어떤 물리 Table을 가리키는지 확인한다.
@pytest.mark.parametrize(
    ("name", "sql"),
    [
        (
            "self_join_disguises_product_inventory_join",
            # Codex가 제시한 원래 우회 시나리오: Product를 자기 자신과 Join해 겉보기엔
            # Product/ProductInventory Join처럼 보이게 하고, ProductInventory는 항등
            # 조건(p.ProductID = p.ProductID)으로만 붙여 실제로는 비제약 Cross Join이 된다.
            "SELECT TOP (100) p.ProductID AS ProductID, p.Name AS Name, "
            "SUM(pi.Quantity) AS CurrentInventory, p.SafetyStockLevel AS SafetyStockLevel\n"
            "FROM Production.Product AS p\n"
            "JOIN Production.Product AS p2 ON p.ProductID = p2.ProductID\n"
            "JOIN Production.ProductInventory AS pi ON p.ProductID = p.ProductID\n"
            "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n"
            "HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n"
            "ORDER BY p.ProductID ASC",
        ),
        (
            "reordered_dangling_productinventory_join",
            # 진짜 Product-ProductInventory Join을 먼저 두고, 참조되지 않는 두 번째
            # ProductInventory Alias를 항등 조건으로 매달아 비제약 Cross Join을 만든다.
            "SELECT TOP (100) p.ProductID AS ProductID, p.Name AS Name, "
            "SUM(pi.Quantity) AS CurrentInventory, p.SafetyStockLevel AS SafetyStockLevel\n"
            "FROM Production.Product AS p\n"
            "JOIN Production.ProductInventory AS pi ON p.ProductID = pi.ProductID\n"
            "JOIN Production.ProductInventory AS pi2 ON p.ProductID = p.ProductID\n"
            "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n"
            "HAVING SUM(pi.Quantity) < p.SafetyStockLevel\n"
            "ORDER BY p.ProductID ASC",
        ),
        (
            "product_inventory_alias_used_for_quantity_swapped_with_product_alias",
            _GOOD_SQL.replace("SUM(pi.Quantity)", "SUM(p.Quantity)"),
        ),
        (
            "product_alias_used_for_safety_stock_swapped_with_inventory_alias",
            _GOOD_SQL.replace(
                "p.SafetyStockLevel AS SafetyStockLevel", "pi.SafetyStockLevel AS SafetyStockLevel"
            ).replace(
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel", "HAVING SUM(pi.Quantity) < pi.SafetyStockLevel"
            ),
        ),
        (
            "duplicate_table_alias_declaration",
            _GOOD_SQL.replace("Production.ProductInventory AS pi", "Production.ProductInventory AS p"),
        ),
        (
            "duplicate_table_alias_declaration_case_insensitive",
            _GOOD_SQL.replace("Production.ProductInventory AS pi", "Production.ProductInventory AS P"),
        ),
    ],
)
def test_join_alias_impersonation_is_rejected(name, sql):
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_mixed_case_table_alias_still_matches_itself():
    """Table Alias 매칭은 SQL Server 기본 동작대로 대소문자를 구분하지 않아야 한다."""
    sql = (
        _GOOD_SQL.replace("AS pi", "AS PI")
        .replace("pi.Quantity", "PI.Quantity")
        .replace("pi.ProductID", "PI.ProductID")
    )
    assert validate(sql, _CONTEXT)


# --- Codex 3차 재검토 발견 D: JOIN/HAVING Predicate 의미 검증 우회 ----------------------------
# 기존 구현은 필수 JOIN/HAVING 표현식이 SQL "일부"에 포함됐는지만 확인해, `OR 1 = 1` 같은 추가
# 조건이 붙은 SQL도 통과했다. ON·HAVING Clause 전체(다음 Clause 경계 직전까지)가 승인된 단일
# Predicate와 정확히 일치해야 하며, OR·추가 AND Predicate·항등 조건 등 어떤 확장도 거부한다.
@pytest.mark.parametrize(
    ("name", "sql"),
    [
        (
            "join_predicate_with_or_1_equals_1",
            _GOOD_SQL.replace(
                "ON p.ProductID = pi.ProductID", "ON p.ProductID = pi.ProductID OR 1 = 1"
            ),
        ),
        (
            "having_predicate_with_or_1_equals_1",
            _GOOD_SQL.replace(
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel",
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel OR 1 = 1",
            ),
        ),
        (
            "join_predicate_with_unapproved_and_condition",
            _GOOD_SQL.replace(
                "ON p.ProductID = pi.ProductID", "ON p.ProductID = pi.ProductID AND p.ProductID = p.ProductID"
            ),
        ),
        (
            "having_predicate_with_unapproved_and_condition",
            _GOOD_SQL.replace(
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel",
                "HAVING SUM(pi.Quantity) < p.SafetyStockLevel AND 1 = 1",
            ),
        ),
    ],
)
def test_join_and_having_predicate_extensions_are_rejected(name, sql):
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_join_predicate_allows_reversed_alias_order_when_tables_are_correct():
    """Product/ProductInventory Alias의 좌우 순서가 바뀐 의미상 동등한 정상 Join은 허용한다."""
    sql = _GOOD_SQL.replace("ON p.ProductID = pi.ProductID", "ON pi.ProductID = p.ProductID")
    assert validate(sql, _CONTEXT)


# --- Codex 3차 재검토 발견 E: 출력 Alias와 물리 표현식 연결 미검증 -----------------------------
# 기존 구현은 ProductID/Name/CurrentInventory/SafetyStockLevel Alias가 존재하는지만 확인해,
# `pi.Quantity AS Name`처럼 승인된 Column을 잘못된 Alias에 연결한 SQL도 통과했다. 각 출력
# Alias가 승인된 물리 표현식과 정확히 연결됐는지, 4개 필수 Alias가 각각 정확히 한 번만
# 선언됐는지, 그 외 미승인 출력 표현식이 없는지를 확인한다.
def test_column_bound_to_wrong_output_alias_is_rejected():
    sql = _GOOD_SQL.replace("p.Name AS Name", "pi.Quantity AS Name")
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_product_and_inventory_columns_swapped_across_output_aliases_is_rejected():
    """ProductID와 Name에 연결된 표현식을 서로 맞바꾸면(Alias 이름 자체는 여전히 승인된 4개
    안에 있지만 물리 표현식이 잘못 연결됨) 거부해야 한다."""
    sql = _GOOD_SQL.replace("p.ProductID AS ProductID, p.Name AS Name", "p.Name AS ProductID, p.ProductID AS Name")
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_duplicate_required_output_alias_is_rejected():
    """ProductID를 중복 선언해 Name 자리를 대체하면(개수는 4개 그대로 유지) 거부해야 한다."""
    sql = _GOOD_SQL.replace("p.Name AS Name", "p.ProductID AS ProductID")
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_extra_unapproved_output_expression_is_rejected():
    """필수 4개 출력에 더해 미승인 5번째 출력 표현식이 추가되면 거부해야 한다."""
    sql = _GOOD_SQL.replace(
        "p.SafetyStockLevel AS SafetyStockLevel\nFROM",
        "p.SafetyStockLevel AS SafetyStockLevel, p.Name AS ExtraColumn\nFROM",
    )
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


# --- Codex 4차 재검토 발견 F: GROUP BY Grain 우회 ---------------------------------------------
# 기존 구현은 SELECT·JOIN·HAVING만 정확히 검증하고 GROUP BY의 의미는 검증하지 않았다.
# `pi.Quantity`가 그룹 키에 추가되면 ProductID 단위 전체 재고 합계가 Quantity별 부분
# 집계로 쪼개져 CurrentInventory와 안전재고 미달 판정이 Golden Query와 달라질 수 있다.
# GROUP BY Clause 전체(GROUP BY 바로 뒤부터 HAVING 직전까지)가 승인된 세 표현식
# (<Product alias>.ProductID/Name/SafetyStockLevel) 정확히 한 번씩으로만 구성돼야 한다.
@pytest.mark.parametrize(
    ("name", "sql"),
    [
        (
            "group_by_quantity_attack",
            # 발견 F가 지목한 원래 공격 SQL: pi.Quantity가 그룹 키에 추가된다.
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel, pi.Quantity",
            ),
        ),
        (
            "extra_approved_product_column_p_quantity",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel, p.Quantity",
            ),
        ),
        (
            "inventory_alias_productid_added",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel, pi.ProductID",
            ),
        ),
        (
            "missing_required_productid",
            _GOOD_SQL.replace("GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.Name, p.SafetyStockLevel"),
        ),
        (
            "missing_required_name",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.ProductID, p.SafetyStockLevel"
            ),
        ),
        (
            "missing_required_safety_stock_level",
            _GOOD_SQL.replace("GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.ProductID, p.Name"),
        ),
        (
            "duplicate_group_key",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.ProductID, p.ProductID, p.Name"
            ),
        ),
        (
            "numeric_literal_group_key",
            _GOOD_SQL.replace("GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.ProductID, p.Name, 1"),
        ),
        (
            "function_call_group_key",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
                "GROUP BY p.ProductID, p.Name, SUM(p.SafetyStockLevel)",
            ),
        ),
        (
            "missing_group_by_entirely",
            _GOOD_SQL.replace("GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n", ""),
        ),
        (
            "duplicate_group_by_clause",
            _GOOD_SQL.replace(
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\n",
                "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel\nGROUP BY pi.Quantity\n",
            ),
        ),
    ],
)
def test_group_by_grain_violations_are_rejected(name, sql):
    with pytest.raises(SqlRejectedError):
        validate(sql, _CONTEXT)


def test_group_by_allows_reordered_required_keys():
    """그룹 키 순서는 의미에 영향을 주지 않으므로 승인된 세 표현식의 순서 변경은 허용한다."""
    sql = _GOOD_SQL.replace(
        "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel", "GROUP BY p.SafetyStockLevel, p.ProductID, p.Name"
    )
    assert validate(sql, _CONTEXT)


def test_group_by_allows_bracket_notation():
    sql = _GOOD_SQL.replace(
        "GROUP BY p.ProductID, p.Name, p.SafetyStockLevel",
        "GROUP BY [p].[ProductID], [p].[Name], [p].[SafetyStockLevel]",
    )
    assert validate(sql, _CONTEXT)


def test_group_by_allows_mixed_case_product_alias():
    """GROUP BY의 Product Alias 매칭도 Table Alias와 마찬가지로 대소문자를 구분하지 않는다."""
    sql = (
        _GOOD_SQL.replace("AS p\n", "AS P\n")
        .replace("p.ProductID", "P.ProductID")
        .replace("p.Name", "P.Name")
        .replace("p.SafetyStockLevel", "P.SafetyStockLevel")
    )
    assert validate(sql, _CONTEXT)
