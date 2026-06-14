from __future__ import annotations

import json
from typing import Any, Iterable, List, Mapping, Sequence


def render_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_table(rows: Iterable[Mapping[str, Any]], *, columns: Sequence[str]) -> str:
    materialized = list(rows)
    widths: List[int] = []
    for column in columns:
        width = len(column)
        for row in materialized:
            width = max(width, len(_cell(row.get(column))))
        widths.append(width)

    header = "  ".join(column.ljust(widths[index]) for index, column in enumerate(columns))
    divider = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(_cell(row.get(column)).ljust(widths[index]) for index, column in enumerate(columns))
        for row in materialized
    ]
    return "\n".join([header, divider, *body]).rstrip()


def pick_rows(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    for key in ("data", "items", "materials", "logs", "cookies", "users"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return data


def render_response(data: Any, *, output: str = "json", columns: Sequence[str] = ()) -> str:
    if output == "table":
        rows = pick_rows(data)
        if isinstance(rows, list):
            selected = list(columns) or _infer_columns(rows)
            return render_table(rows, columns=selected)
    return render_json(data)


def _infer_columns(rows: Sequence[Mapping[str, Any]]) -> Sequence[str]:
    if not rows:
        return []
    return list(rows[0].keys())[:6]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
