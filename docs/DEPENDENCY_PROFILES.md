# Dependency Profiles

## Base profile (core Cortex)

Use this when you only need hook gating, invariants, challenges, graveyard, and foundation analysis.

```bash
pip install -e .
```

Runtime dependencies: none beyond Python stdlib (`sqlite3`, `tomllib`, `subprocess`).

## Repo-map profile (Aider graft alpha)

Use this when you want AST-aware repo-map generation (`ast_pagerank`) with fallback support.

```bash
pip install -e '.[repomap]'
```

Optional packages installed:
- `grep-ast`
- `numpy`
- `networkx`
- `tree-sitter`
- `tree-sitter-language-pack`

Current runtime note:
- Cortex v1 uses `networkx` + `numpy` (when present) to improve PageRank quality. Missing either falls back to built-in deterministic math.
- `grep-ast` and `tree-sitter*` are installed for planned repomap graft phases; they are not yet required by the current runtime path.

## Dev profile

```bash
pip install -e '.[dev]'
```

Installs test/lint tooling (`pytest`, `ruff`).

## Full local testing profile

```bash
pip install -e '.[dev,repomap]'
```

## Verification

```bash
pytest -q
ruff check cortex tests
cortex check --root /path/to/project
```
