# Fortest

A project initialized with `uv` for easy and reproducible environment management.

## Environment Setup and Management

We use [uv](https://github.com/astral-sh/uv) to manage this project's Python environment and dependencies.

### 1. Installation

To set up the environment for the first time:

```bash
uv sync
```

This command will:
- Create a virtual environment in `.venv/`.
- Install all dependencies specified in `pyproject.toml`.
- Synchronize your environment with the `uv.lock` file to ensure reproducibility.

### 2. Managing Dependencies

All dependencies are tracked in `pyproject.toml`.

#### Adding New Packages
To add a new package (e.g., `requests`):

```bash
uv add requests
```

This updates both `pyproject.toml` and `uv.lock`.

#### For Development Packages
To add a package only for development:

```bash
uv add --dev pytest
```

### 3. Reproducibility

For a reproducible setup, **always commit both `pyproject.toml` and `uv.lock`**.

When you pull changes that include dependency updates:

```bash
uv sync
```

This ensures your local `.venv` matches the exact versions specified in the lockfile.

### 4. Running Code

To run a script within the environment:

```bash
uv run <your_script.py>
```

