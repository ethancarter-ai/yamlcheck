import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from yamlcheck import validate_file, _validate_node, run  # noqa: E402


def test_valid_dict():
    schema = {
        "type": "dict",
        "required": ["name"],
        "properties": {
            "name": {"type": "str"},
            "version": {"type": "str", "required": False},
        },
    }
    assert _validate_node({"name": "demo", "version": "1.0"}, schema, "$") == []


def test_missing_required():
    schema = {
        "type": "dict",
        "required": ["name"],
        "properties": {"name": {"type": "str"}},
    }
    errs = _validate_node({}, schema, "$")
    assert any("missing required key 'name'" in e["message"] for e in errs)


def test_forbidden_key():
    schema = {
        "type": "dict",
        "required": ["name"],
        "properties": {"name": {"type": "str"}},
    }
    errs = _validate_node({"name": "x", "secret": 1}, schema, "$")
    assert any("forbidden key 'secret'" in e["message"] for e in errs)


def test_list_items_validated():
    schema = {"type": "list", "items": {"type": "str"}}
    assert _validate_node(["a", "b"], schema, "$") == []


def test_list_item_invalid():
    schema = {"type": "list", "items": {"type": "str"}}
    errs = _validate_node(["a", 1], schema, "$")
    assert any("expected str at $[1]" in e["message"] for e in errs)


def test_boolean_rejected_as_int():
    schema = {"type": "int"}
    errs = _validate_node(True, schema, "$")
    assert any("expected int at $" in e["message"] for e in errs)


def test_valid_yaml_file():
    schema = {
        "type": "dict",
        "required": ["name"],
        "properties": {"name": {"type": "str"}},
    }
    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as f:
        f.write("name: ok\n")
        p = Path(f.name)
    try:
        errs = validate_file(p, schema)
        assert errs == []
    finally:
        p.unlink()


def test_malformed_yaml_file():
    schema = {"type": "dict"}
    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as f:
        f.write("key: [bad\n")
        p = Path(f.name)
    try:
        errs = validate_file(p, schema)
        assert any("malformed YAML" in e["message"] for e in errs)
    finally:
        p.unlink()


def test_cli_ok():
    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as cfg:
        cfg.write("name: demo\n")
        c = Path(cfg.name)
    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as sch:
        yaml.dump(
            {
                "type": "dict",
                "required": ["name"],
                "properties": {"name": {"type": "str"}},
            },
            sch,
        )
        s = Path(sch.name)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "yamlcheck", "--schema", str(s), str(c)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert "OK" in result.stdout + result.stderr
    finally:
        c.unlink()
        s.unlink()


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
