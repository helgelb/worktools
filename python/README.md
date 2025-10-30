# Python Work Tools

Collection of Python productivity tools for daily work tasks.

## Available Tools

### Hours Allocation Tool

- **File:** `allocate_hours.py`
- **Purpose:** Allocates per-day working hours across percentage categories
- **Documentation:** [../docs/python/allocate_hours.md](../docs/python/allocate_hours.md)

**Quick Example:**

```bash
python allocate_hours.py --hours 0 2 7.5 7.5 7.5 --percent 0.6 0.4 --sum
```

## Installation

**Note:** All commands should be run from this `python/` directory.

The project uses `pyproject.toml` which works with multiple dependency managers:

```bash
# UV (fast, modern)
pip install uv && uv pip install -e ".[dev]"

# Poetry (popular)
pip install poetry && poetry install

# PDM (Python-native)
pip install pdm && pdm install

# Traditional pip
pip install -e ".[dev]"
```

## Usage

Each tool can be run directly:

```bash
python tool_name.py [options]
```

Or imported programmatically:

```python
from tool_name import function_name
```

## Development

```bash
# Run all tests
python -m pytest tests/ -v

# Format and lint code
ruff format .
ruff check .
```

## Adding New Tools

When adding a new tool:

1. Place the Python file in this directory
2. Add comprehensive docstrings and help text
3. Create corresponding tests in `tests/`
4. Update this README with the new tool
