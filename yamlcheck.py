from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _flatten_errors(errors: list[dict]) -> list[str]:
    return [f"{e['file']}:{e['line']}:{e['column']} {e['message']}" for e in errors]


def _validate_node(node: Any, schema: dict[str, Any], path: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    expected = schema.get("type")
    if expected == "null":
        if node is not None:
            errors.append({"path": path, "message": f"expected null at {path}"})
        return errors

    if expected == "str" and not isinstance(node, str):
        errors.append({"path": path, "message": f"expected str at {path}"})
        return errors
    if expected == "int" and (not isinstance(node, int) or isinstance(node, bool)):
        errors.append({"path": path, "message": f"expected int at {path}"})
        return errors
    if expected == "float" and (not isinstance(node, (int, float)) or isinstance(node, bool)):
        errors.append({"path": path, "message": f"expected float at {path}"})
        return errors
    if expected == "bool" and not isinstance(node, bool):
        errors.append({"path": path, "message": f"expected bool at {path}"})
        return errors
    if expected == "list" and not isinstance(node, list):
        errors.append({"path": path, "message": f"expected list at {path}"})
        return errors
    if expected == "dict" and not isinstance(node, dict):
        errors.append({"path": path, "message": f"expected dict at {path}"})
        return errors

    if expected == "dict" and isinstance(node, dict):
        for key, prop_schema in schema.get("properties", {}).items():
            required = prop_schema.get("required", True)
            if key not in node:
                if required:
                    errors.append({"path": path, "message": f"missing required key '{key}'"})
                continue
            child_path = f"{path}.{key}" if path else key
            errors.extend(_validate_node(node[key], prop_schema, child_path))
        if schema.get("properties"):
            for key in node.keys():
                if key not in schema.get("properties", {}):
                    errors.append(
                        {"path": path, "message": f"forbidden key '{key}' at {path}"}
                    )

    if expected == "list" and isinstance(node, list):
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(node):
                errors.extend(
                    _validate_node(
                        item, item_schema, f"{path}[{idx}]"
                    )
                )

    return errors


def _attach_positions(content: str, errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positioned = []
    lines = content.splitlines()
    for err in errors:
        line = 1
        col = 1
        key = err.get("path", "")
        if key:
            needle = key.split(".")[0].split("[")[0]
            for i, ln in enumerate(lines, start=1):
                idx = ln.find(needle)
                if idx != -1:
                    line = i
                    col = idx + 1
                    break
        positioned.append(
            {
                "file": err.get("file", "?"),
                "line": line,
                "column": col,
                "message": err["message"],
            }
        )
    return positioned


def validate_file(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        line = mark.line + 1 if mark else 1
        col = mark.column + 1 if mark else 1
        return [
            {
                "file": str(path),
                "line": line,
                "column": col,
                "message": f"malformed YAML: {exc.__class__.__name__}: {exc}",
            }
        ]
    raw_errors = _validate_node(data, schema, "$")
    if not raw_errors:
        return []
    return _attach_positions(content, raw_errors)


def run(paths: list[Path], schema: dict[str, Any], fmt: str) -> tuple[int, str]:
    all_errors: list[dict[str, Any]] = []
    for target in paths:
        if target.is_dir():
            for child in sorted(target.rglob("*")):
                if child.is_file() and child.suffix in {".yaml", ".yml"}:
                    all_errors.extend(validate_file(child, schema))
        elif target.exists():
            all_errors.extend(validate_file(target, schema))
        else:
            all_errors.append(
                {"file": str(target), "line": 1, "column": 1, "message": "file not found"}
            )

    if fmt == "json":
        payload = json.dumps({"ok": not all_errors, "errors": all_errors}, indent=2)
        return 0 if not all_errors else 1, payload + "\n"

    if fmt == "tsv":
        lines = ["file\tline\tcolumn\tmessage"]
        lines.extend(
            f"{e['file']}\t{e['line']}\t{e['column']}\t{e['message']}" for e in all_errors
        )
        return 0 if not all_errors else 1, "\n".join(lines) + "\n"

    if all_errors:
        print(f"FAIL {len(all_errors)} validation error(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  {err['file']}:{err['line']}:{err['column']} {err['message']}", file=sys.stderr)
        return 1, ""
    print("OK")
    return 0, ""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="yamlcheck",
        description="Validate YAML files against a small schema.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="YAML files or directories")
    parser.add_argument("--schema", required=True, type=Path, help="Schema YAML file")
    parser.add_argument("--recursive", action="store_true", help="Recurse into directories")
    parser.add_argument("--stdin", action="store_true", help="Read YAML from stdin")
    parser.add_argument(
        "--format",
        choices=["human", "json", "tsv"],
        default="human",
        help="Output format",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        schema = yaml.safe_load(args.schema.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return 1

    targets = args.paths
    if args.stdin:
        import io

        data = yaml.safe_load(sys.stdin.read()) or {}
        all_errors = _validate_node(data, schema, "$")
        if all_errors:
            positioned = _attach_positions("", all_errors)
            for err in positioned:
                print(
                    f"{err['file']}:{err['line']}:{err['column']} {err['message']}",
                    file=sys.stderr,
                )
            return 1
        print("OK")
        return 0

    rc, _ = run(targets, schema, args.format)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
