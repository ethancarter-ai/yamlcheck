# yamlcheck

Validate YAML files for type, structure, and schema constraints from the command line.

## About

YAML is easy to write and hard to validate. `yamlcheck` lets teams codify expected YAML shapes in tiny schema files and enforce them across configs, workflows, translations, and infra definitions without adopting a heavy JSON-Schema stack.

## Features

- Reusable per-file schemas (`type`, `required`, `allowed`, `maxDepth`).
- CLI flags for single-file, recursive directory, and stdin modes.
- Machine-readable JSON/TSV output plus colored terminal status.
- Fails on malformed YAML and schema violations with precise line numbers.

## Installation

```bash
pip install yamlcheck
```

## Usage

```bash
yamlcheck --schema schema.yaml config.yaml
yamlcheck --schema schema.yaml --recursive ./configs
cat config.yaml | yamlcheck --schema schema.yaml --stdin
yamlcheck --schema schema.yaml --format json config.yaml
```

## Schema format

Minimal example, `schema.yaml`:

```yaml
type: dict
required:
  - name
  - version
properties:
  name:
    type: str
  version:
    type: str
  enabled:
    type: bool
    required: false
  tags:
    type: list
    items:
      type: str
    required: false
```

Rules:
- Top-level `type` must be `dict`, `list`, `str`, `int`, `float`, `bool`, or `null`.
- `properties` is validated only when `type: dict`.
- `items` is validated only when `type: list`.
- `required: false` makes a property optional. Unlisted keys are forbidden by default.

- Repository: https://github.com/ethancarter-ai/yamlcheck

## Project structure

```
yamlcheck/
  yamlcheck.py
  README.md
  pyproject.toml
  tests/test_yamlcheck.py
```

## Tags / keywords

yaml, validation, schema, cli, config, pyyaml, quality-gate
