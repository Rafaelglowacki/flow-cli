import json
import sys
from typing import Any


def emit(
    data: Any,
    *,
    as_json: bool,
    table_columns: list[str] | None = None,
) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if isinstance(data, list) and table_columns:
        col_widths: dict[str, int] = {col: len(col) for col in table_columns}
        str_rows: list[dict[str, str]] = []
        for item in data:
            row = {}
            for col in table_columns:
                val = str(item.get(col, ""))
                row[col] = val
                if len(val) > col_widths[col]:
                    col_widths[col] = len(val)
            str_rows.append(row)

        header = "  ".join(col.ljust(col_widths[col]) for col in table_columns)
        separator = "  ".join("-" * col_widths[col] for col in table_columns)
        print(header)
        print(separator)
        for row in str_rows:
            line = "  ".join(row[col].ljust(col_widths[col]) for col in table_columns)
            print(line)
        return

    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
        return

    if isinstance(data, list):
        for item in data:
            print(str(item))
        return

    print(str(data))


def fail(message: str, *, as_json: bool, code: int = 1) -> None:
    if as_json:
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"Erro: {message}", file=sys.stderr)
    sys.exit(code)
