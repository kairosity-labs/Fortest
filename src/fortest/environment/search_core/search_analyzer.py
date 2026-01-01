"""
Search Volume Analyzer for Pastcasting Search Evaluation.

This module provides tools to analyze the volume and quality of web search
results across different k values and search functions.

Metrics computed:
- Volume before/after filtering
- IoU (pairwise Intersection over Union of links)
- Unique link ratio per search function
- K-fulfillment rate (actual/requested results)
"""

import os
import json
import asyncio
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from itertools import combinations

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from fortest.environment.search_core.base import SearchCore


class SearchVolumeAnalyzer:
    """Analyzes search volume and quality metrics across k values."""
    
    # K values from 10 to 1000, doubling each time
    K_VALUES = [10, 20, 40, 80, 160, 320, 640, 1000]
    
    def __init__(self, queries_path: Optional[str] = None):
        """
        Initialize the analyzer.
        
        Args:
            queries_path: Path to JSON file with test queries
        """
        self.search_core = SearchCore()
        
        if queries_path is None:
            # Default path relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            queries_path = os.path.join(base_dir, "search_test_queries.json")
        
        self.queries_path = queries_path
        self.queries = self._load_queries()
        self.results: Dict[str, Dict[int, Dict[str, Any]]] = {}  # {query_id: {k: {func: result}}}
    
    def _load_queries(self) -> List[Dict[str, Any]]:
        """Load test queries from JSON file."""
        if os.path.exists(self.queries_path):
            with open(self.queries_path, "r") as f:
                data = json.load(f)
                return data.get("queries", [])
        return []
    
    @staticmethod
    def compute_iou(links_a: List[str], links_b: List[str]) -> float:
        """
        Compute Intersection over Union of two link sets.
        
        Args:
            links_a: First set of links
            links_b: Second set of links
            
        Returns:
            IoU score (0.0 to 1.0)
        """
        set_a = set(links_a)
        set_b = set(links_b)
        
        if not set_a and not set_b:
            return 1.0  # Both empty = perfect match
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def compute_unique_ratio(links: List[str], all_links: Set[str]) -> float:
        """
        Compute ratio of unique links from this function to all unique links.
        
        Args:
            links: Links from one search function
            all_links: Union of all links from all search functions
            
        Returns:
            Ratio (0.0 to 1.0)
        """
        if not all_links:
            return 0.0
        
        unique_to_func = set(links)
        return len(unique_to_func) / len(all_links)
    
    @staticmethod
    def compute_k_fulfillment(requested_k: int, returned_k: int) -> float:
        """
        Compute k-fulfillment rate (were k results actually returned?).
        
        Args:
            requested_k: Requested number of results
            returned_k: Actually returned number of results
            
        Returns:
            Fulfillment rate (0.0 to 1.0+)
        """
        if requested_k == 0:
            return 1.0 if returned_k == 0 else 0.0
        return returned_k / requested_k
    
    async def run_single_query(
        self,
        query: Dict[str, Any],
        search_functions: Optional[List[str]] = None,
        k_values: Optional[List[int]] = None,
        delay_seconds: float = 1.0
    ) -> Dict[int, Dict[str, Any]]:
        """
        Run analysis for a single query across all k values and functions.
        
        Args:
            query: Query dict with 'query' and 'testing_time' keys
            search_functions: List of function names (None = all)
            k_values: List of k values to test (None = default)
            delay_seconds: Delay between API calls
            
        Returns:
            Dict of {k: {function_name: result}}
        """
        if search_functions is None:
            search_functions = self.search_core.list_available_functions()
        
        if k_values is None:
            k_values = self.K_VALUES
        
        query_text = query["query"]
        testing_time = query["testing_time"]
        query_id = query.get("id", "unknown")
        
        results_by_k: Dict[int, Dict[str, Any]] = {}
        
        for k in k_values:
            results_by_k[k] = {}
            
            for func_name in search_functions:
                try:
                    print(f"  [{query_id}] Running {func_name} with k={k}...")
                    result = await self.search_core.execute(
                        func_name, 
                        query_text, 
                        testing_time,
                        k=k
                    )
                    results_by_k[k][func_name] = result
                    
                    # Check for errors in result
                    if result.get("error"):
                        print(f"    ⚠️  ERROR: {result['error']}")
                    else:
                        print(f"    ✓ Got {result.get('returned_before_filter', 0)} results")
                        
                except Exception as e:
                    error_msg = str(e)
                    results_by_k[k][func_name] = {"error": error_msg}
                    print(f"    ❌ EXCEPTION: {error_msg}")
                
                # Rate limiting
                await asyncio.sleep(delay_seconds)
        
        return results_by_k
    
    async def run_analysis(
        self,
        search_functions: Optional[List[str]] = None,
        k_values: Optional[List[int]] = None,
        query_limit: Optional[int] = None,
        delay_seconds: float = 1.0
    ) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """
        Run full analysis across all queries.
        
        Args:
            search_functions: List of function names (None = all)
            k_values: List of k values to test (None = default)
            query_limit: Maximum number of queries to run (None = all)
            delay_seconds: Delay between API calls
            
        Returns:
            Dict of {query_id: {k: {function_name: result}}}
        """
        queries = self.queries[:query_limit] if query_limit else self.queries
        
        for query in queries:
            query_id = query.get("id", "unknown")
            print(f"\nProcessing query: {query_id} - {query['query']}")
            
            self.results[query_id] = await self.run_single_query(
                query,
                search_functions=search_functions,
                k_values=k_values,
                delay_seconds=delay_seconds
            )
        
        return self.results
    
    def compute_metrics(self) -> Dict[str, Any]:
        """
        Compute all metrics from collected results.
        
        Returns:
            Dict containing:
            - volume_before: {query_id: {k: {func: count}}}
            - volume_after: {query_id: {k: {func: count}}}
            - iou_matrix: {query_id: {k: {(func_a, func_b): iou}}}
            - unique_ratios: {query_id: {k: {func: ratio}}}
            - k_fulfillment: {query_id: {k: {func: rate}}}
            - date_parse_failures: {query_id: {k: {func: count}}}
            - no_date_count: {query_id: {k: {func: count}}}
        """
        metrics = {
            "volume_before": defaultdict(lambda: defaultdict(dict)),
            "volume_after": defaultdict(lambda: defaultdict(dict)),
            "iou_matrix": defaultdict(lambda: defaultdict(dict)),
            "unique_ratios": defaultdict(lambda: defaultdict(dict)),
            "k_fulfillment": defaultdict(lambda: defaultdict(dict)),
            "date_parse_failures": defaultdict(lambda: defaultdict(dict)),
            "no_date_count": defaultdict(lambda: defaultdict(dict)),
        }
        
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                # Collect all links at this k for this query
                all_links_at_k: Set[str] = set()
                func_links: Dict[str, List[str]] = {}
                
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    
                    # Volume metrics
                    vol_before = result.get("returned_before_filter", 0)
                    vol_after = result.get("returned_after_filter", 0)
                    metrics["volume_before"][query_id][k][func_name] = vol_before
                    metrics["volume_after"][query_id][k][func_name] = vol_after
                    
                    # K-fulfillment
                    requested = result.get("requested_k", k)
                    metrics["k_fulfillment"][query_id][k][func_name] = self.compute_k_fulfillment(
                        requested, vol_before
                    )
                    
                    # Date parse tracking
                    date_failures = result.get("date_parse_failures", 0)
                    no_dates = result.get("no_date_count", 0)
                    metrics["date_parse_failures"][query_id][k][func_name] = date_failures
                    metrics["no_date_count"][query_id][k][func_name] = no_dates
                    
                    # Collect links for IoU
                    links = result.get("links_after_filter", [])
                    func_links[func_name] = links
                    all_links_at_k.update(links)
                
                # IoU pairwise
                func_names = list(func_links.keys())
                for func_a, func_b in combinations(func_names, 2):
                    iou = self.compute_iou(func_links[func_a], func_links[func_b])
                    metrics["iou_matrix"][query_id][k][(func_a, func_b)] = iou
                
                # Unique ratios
                for func_name, links in func_links.items():
                    ratio = self.compute_unique_ratio(links, all_links_at_k)
                    metrics["unique_ratios"][query_id][k][func_name] = ratio
        
        return dict(metrics)
    
    def to_dataframe(self) -> Optional["pd.DataFrame"]:
        """Convert results to a pandas DataFrame for easier analysis."""
        if not PANDAS_AVAILABLE:
            print("Warning: pandas not available, cannot create DataFrame")
            return None
        
        rows = []
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    
                    rows.append({
                        "query_id": query_id,
                        "k": k,
                        "function": func_name,
                        "volume_before": result.get("returned_before_filter", 0),
                        "volume_after": result.get("returned_after_filter", 0),
                        "requested_k": result.get("requested_k", k),
                        "k_fulfillment": self.compute_k_fulfillment(
                            result.get("requested_k", k),
                            result.get("returned_before_filter", 0)
                        ),
                    })
        
        return pd.DataFrame(rows)
    
    def save_results(self, output_path: str):
        """Save results to JSON file."""
        # Convert tuple keys to strings for JSON serialization
        def convert_keys(obj):
            if isinstance(obj, dict):
                return {
                    (str(k) if isinstance(k, tuple) else k): convert_keys(v)
                    for k, v in obj.items()
                }
            return obj
        
        with open(output_path, "w") as f:
            json.dump(convert_keys(self.results), f, indent=2)
        print(f"Results saved to {output_path}")


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Search Volume Analyzer")
    parser.add_argument("--queries", type=str, help="Path to queries JSON file")
    parser.add_argument("--output", type=str, default="./search_results.json",
                        help="Output path for results")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run with single query and k=10 only")
    parser.add_argument("--k-values", type=str, default=None,
                        help="Comma-separated k values (e.g., '10,40,160,640')")
    parser.add_argument("--functions", type=str, default=None,
                        help="Comma-separated function names")
    parser.add_argument("--exclude-mocks", action="store_true", default=True,
                        help="Exclude mock functions from analysis (default: True)")
    parser.add_argument("--include-mocks", action="store_true",
                        help="Include mock functions in analysis")
    parser.add_argument("--include-sonar", action="store_true",
                        help="Include perplexity_sonar (expensive, excluded by default)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between API calls in seconds")
    
    args = parser.parse_args()
    
    analyzer = SearchVolumeAnalyzer(queries_path=args.queries)
    
    k_values = None
    if args.k_values:
        k_values = [int(k.strip()) for k in args.k_values.split(",")]
    
    functions = None
    if args.functions:
        functions = [f.strip() for f in args.functions.split(",")]
    else:
        # Get all available functions
        functions = analyzer.search_core.list_available_functions()
        
        excluded = []
        
        # Exclude mocks by default (unless --include-mocks is specified)
        if args.exclude_mocks and not args.include_mocks:
            excluded.extend([f for f in functions if f.startswith("mock_")])
        
        # Exclude perplexity_sonar by default (expensive, no k support)
        if not args.include_sonar:
            if "perplexity_sonar" in functions:
                excluded.append("perplexity_sonar")
        
        functions = [f for f in functions if f not in excluded]
        if excluded:
            print(f"Excluding: {excluded}")
        print(f"Using functions: {functions}")
    
    if args.dry_run:
        print("Running in dry-run mode (single query, k=10 only)")
        k_values = [10]
        query_limit = 1
    else:
        query_limit = None
    
    await analyzer.run_analysis(
        search_functions=functions,
        k_values=k_values,
        query_limit=query_limit,
        delay_seconds=args.delay
    )
    
    print("\n=== Computing Metrics ===")
    metrics = analyzer.compute_metrics()
    
    print(f"\nVolume Before (sample): {dict(list(metrics['volume_before'].items())[:1])}")
    print(f"K-Fulfillment (sample): {dict(list(metrics['k_fulfillment'].items())[:1])}")
    
    analyzer.save_results(args.output)


if __name__ == "__main__":
    asyncio.run(main())

