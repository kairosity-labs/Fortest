# Search Function Analysis

Analysis of search functions (Perplexity, AskNews) for pastcasting use cases.

## Results Files
- `search_results.json` - DDG/Perplexity analysis (legacy)
- `search_results_asknews.json` - AskNews analysis (k=5,10)
- `search_results_asknews_full.json` - AskNews analysis (k=10-100)

## Plots

### AskNews (k=5,10)
See `asknews/` folder

### AskNews Full (k=10-100)
See `asknews_full/` folder:
- `k_fulfillment.png` - Shows 100% at k=10, declining to 10% at k=100 (Free plan cap)
- `volume_vs_k.png` - Flat line at 10 articles (max allowed)

## Key Findings
- AskNews Free plan caps at **10 articles max** per request
- K-fulfillment: 100% at k=10, drops proportionally for k>10
- Historical data available from **January 2024** onwards
- Requires `historical=True` flag for archive access
