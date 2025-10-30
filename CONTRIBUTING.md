# Contributing

## How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/new-tool`)
3. **Make** your changes
4. **Add** tests for new functionality
5. **Run** tests (`pytest python/tests/`)
6. **Commit** your changes (`git commit -m 'Add new tool'`)
7. **Push** to the branch (`git push origin feature/new-tool`)
8. **Open** a Pull Request

## Code Style

- Follow PEP 8 for Python code
- Add docstrings to functions and classes
- Include type hints where helpful
- Keep functions focused and small

## Testing

- Add tests for new functionality in `python/tests/`
- Run tests with `pytest python/tests/`
- Aim for good test coverage

## Adding New Tools

- Place Python tools in the `python/` directory
- Add comprehensive docstrings and help text
- Support both CLI and programmatic usage
- Include usage examples in docstrings
