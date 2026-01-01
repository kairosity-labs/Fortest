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

### 5. Initial Data Setup

To download and set up the necessary datasets (e.g. ForecastBench):

```bash
uv run src/fortest/scripts/setup_datasets.py
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

### Pipeline Usage & Examples

For a complete runnable example, see `examples/pipeline_demo.py`.

#### 1. Running the Demo
```bash
uv run examples/pipeline_demo.py
```
This script demonstrates:
- Loading questions with different strategies (Extensive, Source-specific)
- Generating random datasets using seeds
- Running a simulated agent pipeline
- Generating evaluation reports

#### 2. Generating Random Question Sets
You can generate reproducible random datasets by changing the `seed` and `max_quest` parameters.

```python
from fortest.environment.manager import EnvironmentManager

# Generate a random set of 100 questions from all sources
env = EnvironmentManager(
    loader_strategy="forecastbench_v1_extensive",
    max_quest=100,
    seed=42  # Change seed to get a different set
)

problems = env.get_problems()
print(f"Loaded {len(problems)} questions")
```

#### 3. Using Different Loaders
Supported strategies for `ForecastBench_v1`:

| Strategy | Description |
|----------|-------------|
| `forecastbench_v1_extensive` | **Recommended**. Balanced sampling across all 9 sources. |
| `forecastbench_v1_source` | Load from a specific source (e.g., `fred`, `manifold`). |
| `forecastbench_v1` | Base loader with `sources` and `horizons` filters. |

**Example: Specific Source & Horizon**
```python
env = EnvironmentManager(
    loader_strategy="forecastbench_v1_source",
    source="fred",
    horizons=["long_term", "very_long_term"],
    max_quest=50,
    seed=123
)
```

#### 4. Evaluating Predictions
The pipeline automatically handles metric calculation.

```python
# Submit predictions
for pid in env.problems:
    env.submit_prediction(pid, 0.75)

# Generate report with Brier Score and Accuracy
metrics = env.report(metrics=["brier_score", "accuracy"])
# Output:
# Problems processed: 50
# brier_score: 0.1875
# accuracy: 0.6200
```

### Running Tests

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
uv run pytest tests/
```


