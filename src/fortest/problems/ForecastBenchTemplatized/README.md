# ForecastBench Templatized

Dynamic templatized forecasting questions that can be resolved with custom date ranges.

## Overview

This module contains 1,951 unique question templates from data sources that support dynamic date ranges:

| Source | Templates |
|--------|-----------|
| acled | 927 |
| yfinance | 457 |
| wikipedia | 348 |
| fred | 166 |
| dbnomics | 53 |

## Files

- `templates.json` - All templatized questions with `{forecast_due_date}` and `{resolution_date}` placeholders
- `resolver.py` - Interfaces for resolving templates with custom dates

## Usage

```python
from fortest.problems.ForecastBenchTemplatized.resolver import (
    TemplateLoader, 
    DummyResolver,
    generate_dataset
)

# Load templates
loader = TemplateLoader()
print(f"Loaded {len(loader.templates)} templates")
print(f"Sources: {loader.sources}")

# Get templates by source
fred_templates = loader.get_by_source('fred')

# Generate dataset with custom dates
resolver = DummyResolver()  # TODO: Implement actual resolvers
dataset = generate_dataset(
    loader=loader,
    resolver=resolver,
    forecast_due_date="2025-01-01",
    resolution_date="2025-07-01",
    sources=["fred", "yfinance"]
)
```

## Template Format

Each template has placeholders:
```
"Will X have increased by {resolution_date} compared to {forecast_due_date}?"
```

These get replaced with actual dates when generating questions.

## TODO

- [ ] Implement FRED API resolver
- [ ] Implement yfinance resolver  
- [ ] Implement Wikipedia resolver
- [ ] Implement ACLED resolver
- [ ] Implement DBnomics resolver
