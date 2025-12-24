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

## Benchmarking System Architecture

The project is a benchmarking package for event forecasting.

### Components

- **Problems DB**: A JSON database (`src/fortest/problems/problems.json`) stores problems with metadata and resolution status.
- **ProblemLoader**: Dynamically registers loading strategies from `src/fortest/loader/custom_loaders/`. It processes problems and injects `time_testing`.
- **SearchCore**: Manages search/data functions. Modules in `src/fortest/environment/search_core/` are automatically registered.
- **EnvironmentManager**: The main interface for agents. It handles problem anonymization, search requests (respecting `time_testing`), and submission management.
- **Metrics**: Standard evaluation metrics (Brier score, Accuracy) located in `src/fortest/metrics/`.

### Development Guidelines

#### Adding a Custom Problem Loader
Create a new file in `src/fortest/loader/custom_loaders/` and use the `@ProblemLoader.register` decorator:

```python
from fortest.loader.loader import ProblemLoader, base_process_problem

@ProblemLoader.register("my_custom_loader")
def my_loader(problems, **kwargs):
    # filtered_probs = ...
    return {p["problem_id"]: base_process_problem(p) for p in filtered_probs}
```

#### Adding a Search Function
Create a new file in `src/fortest/environment/search_core/` and use the `@SearchCore.register` decorator:

```python
from fortest.environment.search_core.base import SearchCore

@SearchCore.register("my_search")
async def my_search(query, testing_time):
    # implementation restricted to data before testing_time
    return results
```

### Running Benchmarks (Example)

```python
from fortest.environment.manager import EnvironmentManager
import asyncio

async def run():
    env = EnvironmentManager(loader_strategy="load_all", eval_strategy="recent")
    problems = env.get_problems()
    
    for pid, prob in problems.items():
        # Search for info
        results = await env.search("mock_google", pid, prob["question"])
        # Agent predicts...
        env.submit_prediction(pid, 0.6)
    
    env.report()

asyncio.run(run())
```

### Running Tests

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
uv run pytest tests/
```


