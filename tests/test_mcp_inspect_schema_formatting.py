import pytest

from mcp_server.tools.inspect_schema import _format_data_type


@pytest.mark.parametrize(
    "type_name,max_length,precision,scale,expected",
    [
        ("nvarchar", 100, 0, 0, "nvarchar(50)"),
        ("nvarchar", -1, 0, 0, "nvarchar(max)"),
        ("nchar", 20, 0, 0, "nchar(10)"),
        ("varchar", 50, 0, 0, "varchar(50)"),
        ("varchar", -1, 0, 0, "varchar(max)"),
        ("char", 10, 0, 0, "char(10)"),
        ("varbinary", -1, 0, 0, "varbinary(max)"),
        ("decimal", 0, 18, 4, "decimal(18,4)"),
        ("numeric", 0, 9, 2, "numeric(9,2)"),
        ("datetime2", 0, 0, 7, "datetime2(7)"),
        ("time", 0, 0, 3, "time(3)"),
        ("datetimeoffset", 0, 0, 7, "datetimeoffset(7)"),
        ("int", 4, 0, 0, "int"),
        ("bigint", 8, 0, 0, "bigint"),
        ("bit", 1, 0, 0, "bit"),
        ("uniqueidentifier", 16, 0, 0, "uniqueidentifier"),
        ("date", 3, 0, 0, "date"),
    ],
)
def test_format_data_type(type_name, max_length, precision, scale, expected):
    assert _format_data_type(type_name, max_length, precision, scale) == expected
