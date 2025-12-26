# Fortest Environment API Documentation

This document provides a detailed reference for the functions and interfaces exposed by the Fortest environment. It is designed for developers adding new search capabilities, custom dataset loaders, or building agents.

## 1. Search Functions Interface & Registry

The search system is managed by `SearchCore` (`src/fortest/environment/search_core/base.py`). It allows for dynamic registration and execution of search functions that are aware of "testing time" (to prevent data leakage).

### Registry

The registry automatically loads any module in the `src/fortest/environment/search_core` package. To add a new search function, simply create a new file in that directory (or add to an existing one) and decorate your function.

### Interface

To create a new search function, use the `@SearchCore.register("function_name")` decorator.

**Function Signature**:
```python
@SearchCore.register("my_search_function")
async def my_search_function(query: str, testing_time: str) -> Any:
    """
    Args:
        query: The search query string.
        testing_time: ISO-8601 formatted string representing the "current" time for the agent.
                      Data returned MUST be available before this time.
    Returns:
        Any data structure (string, dict, list) containing search results.
    """
    # Implementation here
```

### Execution

Agents do not call `SearchCore` directly. Instead, they access search via `EnvironmentManager.search`.

```python
result = await manager.search("my_search_function", problem_id, "search query")
```
The `EnvironmentManager` automatically injects the correct `testing_time` for the given `problem_id`.

## 2. Problem Interface

Problems are loaded via `ProblemLoader` (`src/fortest/loader/loader.py`). The system uses a standardized dictionary schema for all problems, regardless of their source format.

### Schema

Each problem object passed to an agent contains the following fields:

```python
{
    "problem_id": str,          # Unique identifier (e.g., "fb_2024_12345")
    "question": str,            # The text of the question
    "time_start": str,          # ISO timestamp when the question opened
    "time_end": str,            # ISO timestamp when the question closed/resolved
    "time_now": str,            # ISO timestamp of the current real-world execution time
    "time_testing": str,        # ISO timestamp simulating when the agent is "acting"
    "metadata": {               # Additional context
        "source": str,          # E.g., "ForecastBench"
        "dataset": str,         # E.g., "2024-07-21-llm"
        "original_id": str,     # ID in the original dataset
        "choices": list,        # Optional list of choices for MC questions
        "background": str,      # Background info/context
        "resolution_criteria": str, # Detailed criteria for resolution
        "url": str              # URL to original market/question
    }
}
```

*Note: Fields like `resolution_status` and `resolved_flag` are removed before passing the problem to the agent.*

### Registry

Custom loaders can be registered to parse external datasets into this schema.

```python
from fortest.loader.loader import ProblemLoader

@ProblemLoader.register("my_custom_loader")
def load_my_dataset(raw_problems, **kwargs) -> Dict[str, Dict]:
    # Parse and return dictionary of problems {problem_id: problem_dict}
```

### Capability Discovery

Agents can inspect the environment to see what tools are available:

```python
# List available search functions
search_funcs = manager.get_available_search_functions()
# -> ['mock_google', 'mock_perplexity', 'ddg_text_search', ...]

# List available loader strategies
loaders = manager.get_available_loader_strategies()
# -> ['default', 'forecastbench', 'json_loader']

# List available metrics
metrics = manager.get_available_metrics()
# -> ['brier_score', 'accuracy']
```

## 3. Submission Interface

Agents submit predictions via the `EnvironmentManager`.

### Method

```python
manager.submit_prediction(problem_id: str, prediction: float)
```

**Parameters**:
- `problem_id`: The ID of the problem being answered.
- `prediction`: A float value between `0.0` and `1.0` representing the probability of the outcome occurring (or the value for the question).

### Behavior

1. **Validation**: Checks if `problem_id` exists and `prediction` is within bounds.
2. **Logging**: logs the submission timestamp and value.
3. **Storage**: Stores the submission in `manager.submissions` list for that problem.
4. **Evaluation**: When `report()` is called, the manager selects a final prediction based on the configured strategy (default is "recent", using the last submission).

### Example Usage

```python
# Initialize environment
manager = EnvironmentManager(loader_strategy="forecastbench", dataset_name="2024-07-21-llm", limit=1)
problems = manager.get_problems()
pid = list(problems.keys())[0]

# Agent Logic
await manager.search("mock_google", pid, "Recent news about X")
prediction = 0.75 

# Submit
manager.submit_prediction(pid, prediction)

# Generate Report (optional: filter metrics)
metrics = manager.report(metrics=["brier_score"])
print(metrics)
```
