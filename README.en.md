# python-uv

[English](#english) | [中文](./README.md)

## English

### Project Setup

```sh
uv sync
```

### Run Application

```sh
uv run main.py
```

### Adding Dependencies

```sh
# Add production dependency
uv add package-name

# Add development dependency
uv add --dev package-name
```

### Python Version Management

```sh
# Show current Python version
uv python list

# Install specific Python version
uv python install 3.13

# Pin Python version for project
uv python pin 3.13
```

### Virtual Environment Management

```sh
# uv automatically creates and manages virtual environments
# Show virtual environment info
uv venv --show

# Activate virtual environment (optional, uv run handles this automatically)
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### Common Commands

```sh
# List installed packages
uv pip list

# Update all dependencies to latest versions
uv lock --upgrade

# Export dependencies as requirements.txt
uv export --format requirements-txt --output-file requirements.txt

# Run Python module
uv run python -m python-uv

# Run script
uv run python script.py
```

### Project Structure

```
python-uv/
├── src/
│   └── python-uv/
│       └── __init__.py
├── hello.py
├── pyproject.toml
├── uv.lock
└── README.md
```

### Development Guidelines

1. **Dependency Management**: Use `uv add` to add dependencies, avoid manually editing `pyproject.toml`
2. **Version Locking**: The `uv.lock` file should be committed to version control
3. **Python Version**: Recommend specifying supported Python version range in `pyproject.toml`
4. **Virtual Environment**: uv automatically manages virtual environments, manual intervention usually not needed