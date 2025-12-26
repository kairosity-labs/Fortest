# Fortest API Reference

Welcome to the detailed API documentation for **Fortest**, a flexible benchmarking framework for forecasting agents. This document covers the core components, interfaces, and usage patterns.

## 1. Environment Manager (`fortest.environment.manager`)

The `EnvironmentManager` is the central coordinator. It handles problem loading, agent interaction (search, submission), and evaluation.

### Class: `EnvironmentManager`

```python
class EnvironmentManager(loader_strategy: str = "load_all", eval_strategy: str = "recent", **loader_kwargs)
```

**Initialization Parameters:**
- `loader_strategy` *(str)*: The name of the registered loader function to use (e.g., `"forecastbench"`, `"json_loader"`). Defaults to `"load_all"`.
- `eval_strategy` *(str)*: Strategy for selecting the final prediction from multiple submissions. Options:
    - `"recent"`: Uses the last submission (default).
    - `"best"`: Selects the submission closest to the ground truth (oracle-like, useful for upper-bound analysis).
- `**loader_kwargs`: Additional keyword arguments passed directly to the loader function (e.g., `dataset_name`, `limit`).

---

### Core Methods

#### `get_problems()`
```python
def get_problems(self) -> Dict[str, Dict[str, Any]]
```
Returns the loaded problems. **Crucially, this method strips resolution information** (`resolved_flag`, `resolution_status`) to prevent data leakage to the agent.

- **Returns**: A dictionary mapping `problem_id` to problem data objects.

#### `search()`
```python
async def search(self, function_name: str, problem_id: str, query: str) -> Any
```
Executes a search query using a registered search function.

- **Parameters**:
    - `function_name` *(str)*: The name of the search tool (e.g., `"mock_google"`).
    - `problem_id` *(str)*: ID of the problem the agent is working on. Used to inject the correct `time_testing`.
    - `query` *(str)*: The search query string.
- **Returns**: Search results (format depends on the search function, typically `str` or `List[Dict]`).
- **Raises**: `ValueError` if `problem_id` or `function_name` is invalid.

#### `submit_prediction()`
```python
def submit_prediction(self, problem_id: str, prediction: float)
```
Records an agent's prediction for a specific problem.

- **Parameters**:
    - `problem_id` *(str)*: The ID of the problem.
    - `prediction` *(float)*: A probability value between `0.0` and `1.0`. `1.0` means the event will definitely happen (or YES).
- **Raises**: `ValueError` for invalid ID or out-of-bounds prediction.

#### `report()`
```python
def report(self, metrics: List[str] = None) -> Dict[str, float]
```
Generates the final performance report.

- **Parameters**:
    - `metrics` *(List[str], optional)*: List of specific metrics to compute (e.g., `["brier_score"]`). If `None`, computes all available metrics.
- **Returns**: A dictionary containing computed metrics and metadata:
    - `count`: Number of resolved problems evaluated.
    - `brier_score`: Mean squared error of predictions.
    - `accuracy`: Classification accuracy (threshold 0.5).

---

### Capability Discovery Methods

- `get_available_search_functions() -> List[str]`: List all registered search tools.
- `get_available_loader_strategies() -> List[str]`: List all registered dataset loaders.
- `get_available_metrics() -> List[str]`: List all supported metrics.

---

## 2. Problem Loader (`fortest.loader.loader`)

The `ProblemLoader` is responsible for ingesting raw data and converting it into the standardized Fortest schema.

### Class: `ProblemLoader`

**Usage**: Typically instantiated internally by `EnvironmentManager`.

#### `load()`
```python
def load(self, strategy: str, **kwargs) -> Dict[str, Any]
```
Loads problems using the specified strategy.

- **Parameters**:
    - `strategy` *(str)*: Name of the registered loader.
    - `**kwargs`: Arguments passed to the loader.
- **Returns**: Dictionary of full problem objects (including resolutions).

### Registration Decorator

To add a new data source, define a function and decorate it:

```python
from fortest.loader.loader import ProblemLoader

@ProblemLoader.register("my_source_name")
def load_my_source(raw_data, **kwargs):
    # Process raw_data or load files
    # Return Dict[problem_id, problem_object]
    pass
```

### Problem Schema

Every loaded problem has this structure:

| Field | Type | Description |
| :--- | :--- | :--- |
| `problem_id` | `str` | Unique identifier. |
| `question` | `str` | The forecast question. |
| `time_start` | `str` | ISO 8601 timestamp (open date). |
| `time_end` | `str` | ISO 8601 timestamp (close date). |
| `time_now` | `str` | Current system time at load. |
| `time_testing` | `str` | Simulated "current" time for the agent. |
| `resolved_flag` | `bool` | Whether the question has a ground truth. |
| `resolution_status` | `float/None` | Ground truth (0.0 or 1.0). Removed for agents. |
| `metadata` | `dict` | Extra info (source, original ID, URL, etc). |

---

## 3. Search Core (`fortest.environment.search_core.base`)

Manages search tools and enforces temporal validity.

### Application

Agents request search via `EnvironmentManager.search()`, which delegates to `SearchCore.execute()`.

### Registration Decorator

Add new search tools by decorating an `async` function:

```python
from fortest.environment.search_core.base import SearchCore

@SearchCore.register("tool_name")
async def my_search_tool(query: str, testing_time: str) -> Any:
    # Perform search, ensuring results exist BEFORE testing_time
    return results
```

- **Parameters**:
    - `query`: The user's search string.
    - `testing_time`: The implicit cut-off time for information.

---

## 4. Metrics (`fortest.metrics.metrics`)

Standard scoring functions available for evaluation.

#### `brier_score()`
```python
def brier_score(predictions: List[float], outcomes: List[int]) -> float
```
Computes the mean squared error between probability predictions and binary outcomes.
$$ BS = \frac{1}{N} \sum_{i=1}^{N} (f_i - o_i)^2 $$
- Range: `0.0` (Perfect) to `1.0` (Worst).

#### `accuracy()`
```python
def accuracy(predictions: List[float], outcomes: List[int], threshold: float = 0.5) -> float
```
Computes classification accuracy. Prediction >= `threshold` is treated as `1` (Yes).
