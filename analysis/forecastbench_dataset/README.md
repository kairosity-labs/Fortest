# ForecastBench Dataset Analysis

Analysis of the ForecastBench forecasting benchmark dataset.

## Directories

### `raw_data/`
- Original dataset statistics from `data/forecastbench/datasets/`
- 15,684 total questions across 19 question sets
- 9 sources: manifold, metaculus, polymarket, acled, fred, wikipedia, yfinance, dbnomics, infer

### `cleaned_data/`
- Resolved questions for ML training
- 8,575 resolved questions (4,650 single + 3,925 composed)
- X/y format with full metadata preserved
- Plots for class distribution, temporal analysis, horizon analysis

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Questions | 15,684 |
| Resolved Questions | 8,575 |
| Single Resolved | 4,650 |
| Composed Resolved | 3,925 |
| Date Range | 2024-07-21 to 2025-12-23 |
