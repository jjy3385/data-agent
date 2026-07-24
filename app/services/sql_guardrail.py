"""MCP 호출 전 Backend 최소 SQL 검증 (Week 1, Approved Plan의 12개 규칙 + FEAT-0004
고정 Demo Scope 최소 의미 검증).

정규식·토큰 기반 검사이며 SQL Parser는 사용하지 않는다. mcp_server/readonly_query_executor.py의
SELECT-only·단일 Statement·금지 키워드 재검증은 독립된 추가 방어 계층으로 그대로 유지되며,
이 모듈이 그것을 대체하지 않는다(두 계층은 서로 다른 신뢰 경계에서 의도적으로 중복 검증한다).

QueryPlan에서 안전재고 부족 Filter를 강제하더라도(plan_validator) LLM이 SQL 생성 단계에서
그 조건을 SQL 문자열에 반영하지 않을 수 있다(Codex 발견 3). 이를 막기 위해 기존 12개 구조
규칙에 더해 두 Table 모두 사용, ProductID Join, SUM(Quantity) 집계, 안전재고 부족 HAVING
조건, 4개 출력 Alias 전체 존재를 확인한다. 이 추가 검증도 Week 1 수준의 고정 Demo Scope
전용 검사이며, 전체 SQL AST Guardrail과 구조적 Plan-SQL Match(FEAT-0006)로 확장하지 않는다.

Table Alias는 단순 존재 여부(set)가 아니라 alias -> table 매핑으로 관리한다(Codex 재검토
발견). 같은 Table을 다른 Alias로 두 번 끌어와 "겉보기엔 올바른 Product-ProductInventory
Join"을 흉내 내면서 실제로는 관계없는 제3의 Table Alias를 얹어 비제약 Cross Join을 만드는
우회를 막기 위해 같은 Table의 중복 참조 자체를 Fail Closed로 거부한다.

Codex 3차 재검토 발견 D·E를 반영해 두 가지를 더 강화한다:
* (발견 D) ON·HAVING Clause는 부분 문자열 포함 여부가 아니라 Clause 전체(다음 Clause
  경계 키워드 직전까지)가 승인된 단일 Predicate와 정확히 일치하는지 비교한다. `OR 1 = 1`
  같은 추가 조건을 Predicate 뒤에 붙이면 정확 일치 비교에서 그대로 거부된다.
* (발견 E) SELECT 목록은 정확히 4개의 승인된 출력 표현식(`<Product alias>.ProductID`,
  `<Product alias>.Name`, `SUM(<ProductInventory alias>.Quantity)`,
  `<Product alias>.SafetyStockLevel`)으로만 구성돼야 하며, 각 출력 Alias가 그 승인된
  물리 표현식에 정확히 연결됐는지 확인한다. Alias는 존재 여부가 아니라 표현식과의 결합으로
  검증하므로 `pi.Quantity AS Name`처럼 승인된 Column을 잘못된 Alias에 연결하는 SQL은
  거부된다. 필수 Alias 4개는 각각 정확히 한 번만 나타나야 한다.

Codex 4차 재검토 발견 F를 반영해 GROUP BY Clause의 의미도 검증한다:
* GROUP BY는 정확히 한 번만 나타나야 하며(중복 Clause·부분 문자열 우회 방지), Clause
  본문은 `GROUP BY` 바로 뒤부터 `HAVING` 직전까지만 추출한다. Grain을 `<Product
  alias>.ProductID`/`<Product alias>.Name`/`<Product alias>.SafetyStockLevel` 정확히
  3개로 고정해, `pi.Quantity` 같은 추가 그룹 키가 ProductID 단위 집계를 더 잘게 쪼개
  Golden Query와 다른 결과를 만드는 것을 막는다. 세 표현식의 순서는 의미에 영향이 없으므로
  허용하지만, 함수·연산식·숫자·ProductInventory Alias의 Column·중복·누락은 모두 거부한다.
"""

from __future__ import annotations

import re

from app.services.context_builder import MetadataContext

# agent_service.MAXIMUM_RETURNED_ROWS와 동일한 값을 유지한다(순환 Import 회피를 위한 미러링).
_MAXIMUM_RETURNED_ROWS = 100

_FORBIDDEN_KEYWORDS = (
    "WITH",
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "EXEC",
    "EXECUTE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "INTO",
    "UNION",
    "EXCEPT",
    "INTERSECT",
)
_FORBIDDEN_PATTERN = re.compile(r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE)

_RESERVED_WORDS = {
    "SELECT",
    "FROM",
    "JOIN",
    "INNER",
    "LEFT",
    "ON",
    "WHERE",
    "GROUP",
    "BY",
    "HAVING",
    "ORDER",
    "ASC",
    "DESC",
    "TOP",
    "AS",
    "AND",
    "OR",
    "NOT",
    "IN",
    "IS",
    "NULL",
    "SUM",
    "COUNT",
    "AVG",
    "MIN",
    "MAX",
}

_ALLOWED_TABLES = {"PRODUCT", "PRODUCTINVENTORY"}
_ALLOWED_SCHEMA_TOKEN = "PRODUCTION"
_ALLOWED_SOURCE_COLUMNS = {"PRODUCTID", "NAME", "SAFETYSTOCKLEVEL", "QUANTITY"}
_ALLOWED_OUTPUT_ALIASES = {"ProductID", "Name", "CurrentInventory", "SafetyStockLevel"}

_IDENT = r"\[?[A-Za-z_][A-Za-z0-9_]*\]?"

_TOP_PATTERN = re.compile(r"^\s*SELECT\s+TOP\s*\(?\s*(\d+)\s*\)?", re.IGNORECASE)
_TABLE_REF_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+(?:\[?Production\]?\.)?\[?([A-Za-z_][A-Za-z0-9_]*)\]?"
    r"(?:\s+AS\s+(\[?[A-Za-z_][A-Za-z0-9_]*\]?))?",
    re.IGNORECASE,
)
_AS_PATTERN = re.compile(r"\bAS\s+(\[?[A-Za-z_][A-Za-z0-9_]*\]?)", re.IGNORECASE)
_IDENTIFIER_PATTERN = re.compile(r"\[?([A-Za-z_][A-Za-z0-9_]*)\]?")
_ORDER_BY_EXISTS_PATTERN = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)
_ORDER_BY_FIRST_KEY_PATTERN = re.compile(
    r"ORDER\s+BY\s+(?:\[?[A-Za-z_][A-Za-z0-9_]*\]?\.)?\[?ProductID\]?\s+ASC\b", re.IGNORECASE
)

# FEAT-0004 고정 Demo Scope 최소 의미 검증에서 쓰는 Clause 경계·항목 패턴(발견 D·E).
# WHERE는 경계 키워드에서 의도적으로 제외한다 — ON/HAVING 뒤에 WHERE를 끼워 넣는 시도는
# 그 뒤 Clause 추출 범위 안으로 그대로 흡수돼 정확 일치 비교에서 자동으로 거부된다.
_CLAUSE_BOUNDARY_PATTERN = re.compile(r"\b(?:INNER|LEFT|JOIN|GROUP|HAVING|ORDER)\b", re.IGNORECASE)
_ON_KEYWORD_PATTERN = re.compile(r"\bON\b", re.IGNORECASE)
_GROUP_BY_KEYWORD_PATTERN = re.compile(r"\bGROUP\s+BY\b", re.IGNORECASE)
_HAVING_KEYWORD_PATTERN = re.compile(r"\bHAVING\b", re.IGNORECASE)
_FROM_KEYWORD_PATTERN = re.compile(r"\bFROM\b", re.IGNORECASE)
_SELECT_ITEM_PATTERN = re.compile(rf"^(?P<expr>.+?)\bAS\b\s*(?P<alias>{_IDENT})\s*$", re.IGNORECASE | re.DOTALL)
# 정규화(대괄호·공백 제거, 대문자 변환)를 거친 뒤의 단순 "ALIAS.COLUMN" 형태만 승인한다.
# 함수 호출·연산식·숫자 리터럴 등은 이 형태와 일치하지 않아 자동으로 거부된다.
_NORMALIZED_ALIAS_COLUMN_PATTERN = re.compile(r"^([A-Z_][A-Z0-9_]*)\.([A-Z_][A-Z0-9_]*)$")
_REQUIRED_GROUP_BY_COLUMNS = {"PRODUCTID", "NAME", "SAFETYSTOCKLEVEL"}


class SqlRejectedError(RuntimeError):
    """SQL이 Week 1 최소 실행 제한 12개 규칙 중 하나라도 위반할 때 발생한다."""


def _strip_brackets(identifier: str) -> str:
    return identifier.strip("[]")


def _extract_clause_after(text: str, start_pattern: re.Pattern[str]) -> str | None:
    """start_pattern이 매치하는 지점 바로 뒤부터 다음 Clause 경계 키워드(GROUP/HAVING/ORDER 등)
    또는 문자열 끝까지의 원문을 추출한다. 시작 키워드를 찾지 못하면 None을 반환한다."""
    start_match = start_pattern.search(text)
    if not start_match:
        return None
    remainder = text[start_match.end() :]
    boundary_match = _CLAUSE_BOUNDARY_PATTERN.search(remainder)
    clause_text = remainder[: boundary_match.start()] if boundary_match else remainder
    return clause_text.strip()


def _extract_select_list(cleaned: str, top_match: re.Match[str]) -> str:
    """TOP (n) 바로 뒤부터 FROM 키워드 직전까지의 SELECT 목록 원문을 추출한다."""
    remainder = cleaned[top_match.end() :]
    from_match = _FROM_KEYWORD_PATTERN.search(remainder)
    select_list_text = remainder[: from_match.start()] if from_match else remainder
    return select_list_text.strip()


def _normalize_predicate(text: str) -> str:
    """대괄호와 모든 공백을 제거하고 대문자로 바꿔 Predicate·표현식을 정확 비교할 수 있는
    canonical 형태로 만든다. 부분 문자열 포함이 아니라 완전 일치 비교에만 사용한다."""
    text = text.replace("[", "").replace("]", "")
    text = re.sub(r"\s+", "", text)
    return text.upper()


def _split_top_level_commas(text: str) -> list[str]:
    """괄호(SUM(...) 등) 안의 콤마는 무시하고 최상위 콤마로만 SELECT 목록을 분리한다."""
    items: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return [item.strip() for item in items]


def validate(sql: str, context: MetadataContext) -> str:
    """오류·보안·경계 처리 절의 12개 규칙과 FEAT-0004 고정 Demo Scope 최소 의미 검증을
    순서대로 적용해 MCP 호출 전 거부한다.

    통과한 SQL 문자열을 그대로 반환한다. `context` Parameter는 향후 Metadata Context 기반
    Allowlist 확장을 위해 공개 경계에 유지하며, Week 1 고정 Allowlist는 모듈 상수로 둔다.
    """
    _ = context  # Week 1 Allowlist는 고정 상수이며 Metadata Context에서 파생하지 않는다.

    cleaned = sql.strip()
    if not cleaned:
        raise SqlRejectedError("sql must not be blank")

    # 규칙 1: 세미콜론/다중 Statement
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if ";" in cleaned:
        raise SqlRejectedError("sql must not contain multiple statements")

    # 규칙 2: 문자열 Literal 거부(Fail Closed, 마스킹 없음)
    if "'" in cleaned:
        raise SqlRejectedError("sql must not contain string literals")

    # 규칙 3: 주석 거부
    if "--" in cleaned or "/*" in cleaned:
        raise SqlRejectedError("sql must not contain comments")

    # 규칙 4: SELECT 정확히 1회
    select_count = len(re.findall(r"\bSELECT\b", cleaned, re.IGNORECASE))
    if select_count != 1:
        raise SqlRejectedError("sql must contain exactly one SELECT")

    # 규칙 5: SELECT로 시작 + 금지 키워드
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        raise SqlRejectedError("sql must start with SELECT")
    forbidden_match = _FORBIDDEN_PATTERN.search(cleaned)
    if forbidden_match:
        raise SqlRejectedError(f"sql must not contain forbidden keyword: {forbidden_match.group(1).upper()}")

    # 규칙 6: TOP 필수 + 상한
    top_match = _TOP_PATTERN.match(cleaned)
    if not top_match:
        raise SqlRejectedError("sql must specify SELECT TOP (n)")
    top_n = int(top_match.group(1))
    if not (1 <= top_n <= _MAXIMUM_RETURNED_ROWS):
        raise SqlRejectedError(f"TOP must be between 1 and {_MAXIMUM_RETURNED_ROWS}")

    # 규칙 7: '*' 전면 거부(규칙 2로 문자열 Literal이 이미 없으므로 마스킹 불필요)
    if "*" in cleaned:
        raise SqlRejectedError("sql must not contain '*'")

    # 규칙 8·9: 허용 Table + AS Table Alias 선언 수집. Alias -> Table 매핑으로 관리해 어떤
    # Alias가 실제로 어떤 물리 Table을 가리키는지 뒤의 의미 검증에서 확인할 수 있게 한다.
    # 같은 Alias의 중복 선언과 같은 Table의 중복 참조(다른 Alias로 같은 Table을 두 번
    # 끌어와 위장 Join·비제약 Cross Join을 만드는 우회)를 모두 Fail Closed로 거부한다.
    table_alias_to_table: dict[str, str] = {}
    table_ref_spans: list[tuple[int, int]] = []
    found_table = False
    for match in _TABLE_REF_PATTERN.finditer(cleaned):
        found_table = True
        table_ref_spans.append(match.span())
        table_name = match.group(1).upper()
        if table_name not in _ALLOWED_TABLES:
            raise SqlRejectedError(f"sql references disallowed table: {match.group(1)}")
        alias = match.group(2)
        if not alias:
            raise SqlRejectedError(f"table reference {match.group(1)} must declare an alias with AS")
        # Alias는 SQL Server 기본 동작대로 대소문자 구분 없이 매칭한다(Key는 대문자로 정규화).
        alias_key = _strip_brackets(alias).upper()
        if alias_key in table_alias_to_table:
            raise SqlRejectedError(f"sql declares the table alias {alias_key!r} more than once")
        if table_name in table_alias_to_table.values():
            raise SqlRejectedError(f"sql references table {match.group(1)} more than once")
        table_alias_to_table[alias_key] = table_name
    if not found_table:
        raise SqlRejectedError("sql must reference FROM/JOIN")

    # 규칙 10: 출력 Column Alias를 Table Alias보다 먼저 분류하고 승인 목록과 대조(이름만).
    # 정확히 어떤 물리 표현식에 연결됐는지는 이 규칙이 아니라 아래 FEAT-0004 의미 검증(발견 E)이
    # 확인한다 — 여기서는 Table Alias 선언이 아닌 모든 "AS X" 사용에서 X가 승인된 4개 출력
    # Alias 이름 중 하나인지만 확인해 다른 위치의 임의 Alias 사용을 막는다.
    def _within_table_ref(pos: int) -> bool:
        return any(start <= pos < end for start, end in table_ref_spans)

    output_aliases: set[str] = set()
    for match in _AS_PATTERN.finditer(cleaned):
        if _within_table_ref(match.start()):
            continue
        ident = _strip_brackets(match.group(1))
        output_aliases.add(ident)
        if ident not in _ALLOWED_OUTPUT_ALIASES:
            raise SqlRejectedError(f"sql uses an unapproved output alias: {ident}")

    # 규칙 11: 전체 식별자 Allowlist(Table Alias·출력 Alias는 이미 승인됨)
    allowed_identifiers = (
        _RESERVED_WORDS
        | _ALLOWED_TABLES
        | {_ALLOWED_SCHEMA_TOKEN}
        | {alias.upper() for alias in table_alias_to_table}
        | {alias.upper() for alias in output_aliases}
        | _ALLOWED_SOURCE_COLUMNS
    )
    for match in _IDENTIFIER_PATTERN.finditer(cleaned):
        ident = match.group(1)
        if ident.upper() not in allowed_identifiers:
            raise SqlRejectedError(f"sql references an unapproved identifier: {ident}")

    # 규칙 12: 결정적 ORDER BY ProductID ASC
    if not _ORDER_BY_EXISTS_PATTERN.search(cleaned):
        raise SqlRejectedError("sql must contain ORDER BY")
    if not _ORDER_BY_FIRST_KEY_PATTERN.search(cleaned):
        raise SqlRejectedError("the first ORDER BY key must be ProductID ASC")

    # FEAT-0004 고정 Demo Scope 최소 의미 검증: Product와 ProductInventory가 정확히
    # 한 번씩 사용되고(위에서 이미 확인), 그 두 Alias가 실제로 어떤 물리 Table을 가리키는지
    # 확인한다. 이 시점부터 product_alias·inventory_alias는 각각 유일하게 결정된다.
    referenced_table_names = set(table_alias_to_table.values())
    if _ALLOWED_TABLES - referenced_table_names:
        missing = sorted(_ALLOWED_TABLES - referenced_table_names)
        raise SqlRejectedError(f"sql must reference both required tables: {missing}")

    product_alias = next(alias for alias, table in table_alias_to_table.items() if table == "PRODUCT")
    inventory_alias = next(alias for alias, table in table_alias_to_table.items() if table == "PRODUCTINVENTORY")

    # (발견 D) ON Clause: 두 Table Alias가 Product/ProductInventory를 가리키는지는 이미
    # 확정했으므로, 여기서는 ON부터 다음 Clause 경계(GROUP 등) 직전까지의 원문 전체가 그 두
    # Alias의 ProductID 등가 비교 하나와 정확히 일치하는지만 비교한다(좌우 순서는 허용). 부분
    # 문자열 포함이 아니라 완전 일치이므로 `OR 1 = 1` 같은 추가 조건은 그대로 거부된다.
    raw_on_clause = _extract_clause_after(cleaned, _ON_KEYWORD_PATTERN)
    if raw_on_clause is None:
        raise SqlRejectedError("sql must join Production.Product and Production.ProductInventory on ProductID")
    normalized_on = _normalize_predicate(raw_on_clause)
    allowed_on_predicates = {
        f"{product_alias}.PRODUCTID={inventory_alias}.PRODUCTID",
        f"{inventory_alias}.PRODUCTID={product_alias}.PRODUCTID",
    }
    if normalized_on not in allowed_on_predicates:
        raise SqlRejectedError(
            "the JOIN predicate must be exactly <Product alias>.ProductID = <ProductInventory alias>.ProductID "
            "(either order), with no additional condition"
        )

    # (발견 F) GROUP BY Clause: 정확히 한 번만 나타나야 하며(중복 Clause·부분 문자열 우회
    # 방지), `GROUP BY` 바로 뒤부터 `HAVING` 직전까지의 원문만 Grain 검증 대상으로 삼는다.
    # 승인된 세 표현식(<Product alias>.ProductID/Name/SafetyStockLevel)만 정확히 한 번씩
    # 나타나야 한다 — `pi.Quantity` 같은 추가 그룹 키가 섞이면 ProductID 단위 집계가 더
    # 잘게 쪼개져 CurrentInventory·안전재고 미달 판정이 Golden Query와 달라질 수 있다.
    group_by_occurrences = len(_GROUP_BY_KEYWORD_PATTERN.findall(cleaned))
    if group_by_occurrences == 0:
        raise SqlRejectedError("sql must contain GROUP BY")
    if group_by_occurrences > 1:
        raise SqlRejectedError("sql must not contain more than one GROUP BY clause")

    raw_group_by_clause = _extract_clause_after(cleaned, _GROUP_BY_KEYWORD_PATTERN)
    group_by_items = _split_top_level_commas(raw_group_by_clause or "")
    if len(group_by_items) != len(_REQUIRED_GROUP_BY_COLUMNS):
        raise SqlRejectedError(
            f"sql GROUP BY clause must contain exactly {len(_REQUIRED_GROUP_BY_COLUMNS)} approved group keys: "
            f"<Product alias>.ProductID, <Product alias>.Name, <Product alias>.SafetyStockLevel"
        )

    seen_group_by_columns: set[str] = set()
    for item in group_by_items:
        normalized_item = _normalize_predicate(item)
        item_match = _NORMALIZED_ALIAS_COLUMN_PATTERN.match(normalized_item)
        if not item_match:
            raise SqlRejectedError(f"sql GROUP BY key is not a simple '<Product alias>.<Column>' reference: {item}")
        item_alias, item_column = item_match.group(1), item_match.group(2)
        if table_alias_to_table.get(item_alias) != "PRODUCT":
            raise SqlRejectedError(f"sql GROUP BY key must use the Production.Product alias: {item}")
        if item_column not in _REQUIRED_GROUP_BY_COLUMNS:
            raise SqlRejectedError(f"sql GROUP BY key references an unapproved column: {item}")
        if item_column in seen_group_by_columns:
            raise SqlRejectedError(f"sql GROUP BY key {item_column!r} appears more than once")
        seen_group_by_columns.add(item_column)

    missing_group_by_columns = _REQUIRED_GROUP_BY_COLUMNS - seen_group_by_columns
    if missing_group_by_columns:
        raise SqlRejectedError(f"sql GROUP BY clause is missing required keys: {sorted(missing_group_by_columns)}")

    # (발견 D) HAVING Clause: HAVING부터 다음 Clause 경계(ORDER 등) 직전까지의 원문 전체가
    # 승인된 단일 안전재고 부족 비교와 정확히 일치해야 한다. SELECT 목록의 CurrentInventory와
    # 항상 같은 ProductInventory Alias를 쓴다 — 이 Alias는 이 시점에 이미 유일하게 결정되므로
    # (중복 Table 참조가 이미 거부됨) 별도 교차 확인이 필요하지 않다.
    raw_having_clause = _extract_clause_after(cleaned, _HAVING_KEYWORD_PATTERN)
    if raw_having_clause is None:
        raise SqlRejectedError(
            "sql must filter with HAVING SUM(<ProductInventory alias>.Quantity) < "
            "<Product alias>.SafetyStockLevel (below safety stock)"
        )
    normalized_having = _normalize_predicate(raw_having_clause)
    allowed_having_predicate = f"SUM({inventory_alias}.QUANTITY)<{product_alias}.SAFETYSTOCKLEVEL"
    if normalized_having != allowed_having_predicate:
        raise SqlRejectedError(
            "the HAVING clause must be exactly SUM(<ProductInventory alias>.Quantity) < "
            "<Product alias>.SafetyStockLevel, with no additional condition"
        )

    # (발견 E) SELECT 목록: 정확히 4개의 승인된 출력 표현식만 허용한다. 각 항목을
    # "<expr> AS <alias>" 형태로 파싱해 alias가 승인된 4개 이름 중 하나이고 정확히 한 번만
    # 나타나는지, 그리고 expr이 그 alias에 대해 승인된 물리 표현식과 정확히 일치하는지 모두
    # 확인한다. Alias 이름만 맞고 다른 Column·Alias에 연결된 표현식(예: `pi.Quantity AS Name`)
    # 은 여기서 거부된다.
    expected_expr_by_alias = {
        "PRODUCTID": f"{product_alias}.PRODUCTID",
        "NAME": f"{product_alias}.NAME",
        "CURRENTINVENTORY": f"SUM({inventory_alias}.QUANTITY)",
        "SAFETYSTOCKLEVEL": f"{product_alias}.SAFETYSTOCKLEVEL",
    }

    select_list_text = _extract_select_list(cleaned, top_match)
    select_items = _split_top_level_commas(select_list_text)
    if len(select_items) != len(expected_expr_by_alias):
        raise SqlRejectedError(
            f"sql SELECT list must contain exactly {len(expected_expr_by_alias)} approved output expressions"
        )

    seen_output_aliases: set[str] = set()
    for item in select_items:
        item_match = _SELECT_ITEM_PATTERN.match(item)
        if not item_match:
            raise SqlRejectedError(f"sql SELECT list item is not a valid '<expression> AS <alias>' form: {item}")
        alias_key = _strip_brackets(item_match.group("alias")).upper()
        if alias_key not in expected_expr_by_alias:
            raise SqlRejectedError(f"sql uses an unapproved output alias: {item_match.group('alias')}")
        if alias_key in seen_output_aliases:
            raise SqlRejectedError(f"sql declares the output alias {alias_key!r} more than once")
        seen_output_aliases.add(alias_key)

        normalized_expr = _normalize_predicate(item_match.group("expr"))
        if normalized_expr != expected_expr_by_alias[alias_key]:
            raise SqlRejectedError(
                f"output alias {alias_key} must be bound to exactly {expected_expr_by_alias[alias_key]}"
            )

    missing_output_aliases = set(expected_expr_by_alias) - seen_output_aliases
    if missing_output_aliases:
        raise SqlRejectedError(f"sql is missing required output aliases: {sorted(missing_output_aliases)}")

    return cleaned
