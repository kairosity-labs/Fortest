"""
Search Volume Visualization Module.

Generates plots for analyzing pastcasting search quality and volume:
1. Volume vs K (before/after filtering)
2. IoU Heatmaps (pairwise between search functions)
3. Unique Link Ratio
4. K-Fulfillment Rate
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional, Set, TYPE_CHECKING
from collections import defaultdict
from itertools import combinations

# Type alias for matplotlib Figure (when available)
if TYPE_CHECKING:
    from matplotlib.figure import Figure
else:
    Figure = Any  # type: ignore

try:
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None  # type: ignore
    cm = None  # type: ignore
    np = None  # type: ignore


class SearchPlots:
    """Generate visualization plots for search volume analysis."""
    
    def __init__(self, results: Dict[str, Dict[int, Dict[str, Any]]]):
        """
        Initialize with analyzer results.
        
        Args:
            results: Dict of {query_id: {k: {function_name: result}}}
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for visualization")
        
        self.results = results
        self.k_values: List[int] = []
        self.functions: Set[str] = set()
        self._extract_metadata()
    
    def _extract_metadata(self):
        """Extract k values and function names from results."""
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                if k not in self.k_values:
                    self.k_values.append(k)
                self.functions.update(func_results.keys())
        
        self.k_values.sort()
        self.functions = sorted(self.functions)
    
    def plot_volume_vs_k(
        self,
        output_path: Optional[str] = None,
        figsize: tuple = (14, 8)
    ) -> Figure:
        """
        Plot volume (before/after filtering) vs k for each search function.
        
        Creates two subplots: one for volume before, one for volume after.
        """
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Aggregate across queries
        vol_before_by_func: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        vol_after_by_func: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    vol_before_by_func[func_name][k].append(
                        result.get("returned_before_filter", 0)
                    )
                    vol_after_by_func[func_name][k].append(
                        result.get("returned_after_filter", 0)
                    )
        
        colors = cm.tab10(np.linspace(0, 1, len(self.functions)))
        
        # Plot volume before filtering
        ax = axes[0]
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = vol_before_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            ax.plot(self.k_values, means, marker='o', label=func_name, color=colors[i])
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Volume (mean across queries)")
        ax.set_title("Volume BEFORE Date Filtering")
        ax.set_xscale("log", base=2)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # Plot volume after filtering
        ax = axes[1]
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = vol_after_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            ax.plot(self.k_values, means, marker='o', label=func_name, color=colors[i])
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Volume (mean across queries)")
        ax.set_title("Volume AFTER Date Filtering")
        ax.set_xscale("log", base=2)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        return fig
    
    def plot_iou_heatmaps(
        self,
        output_path: Optional[str] = None,
        figsize: tuple = (16, 10)
    ) -> Figure:
        """
        Plot IoU heatmaps for pairwise search function comparisons at each k.
        """
        n_k = len(self.k_values)
        n_cols = min(4, n_k)
        n_rows = (n_k + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        if n_k == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        
        func_list = list(self.functions)
        n_funcs = len(func_list)
        
        for idx, k in enumerate(self.k_values):
            row, col = idx // n_cols, idx % n_cols
            ax = axes[row, col]
            
            # Compute IoU matrix for this k
            iou_matrix = np.zeros((n_funcs, n_funcs))
            np.fill_diagonal(iou_matrix, 1.0)
            
            for query_id, k_results in self.results.items():
                if k not in k_results:
                    continue
                
                func_results = k_results[k]
                func_links: Dict[str, List[str]] = {}
                
                for func_name, result in func_results.items():
                    if "error" not in result:
                        func_links[func_name] = result.get("links_after_filter", [])
                
                for i, func_a in enumerate(func_list):
                    for j, func_b in enumerate(func_list):
                        if i >= j:
                            continue
                        if func_a in func_links and func_b in func_links:
                            links_a = set(func_links[func_a])
                            links_b = set(func_links[func_b])
                            if links_a or links_b:
                                iou = len(links_a & links_b) / len(links_a | links_b)
                                iou_matrix[i, j] = iou
                                iou_matrix[j, i] = iou
            
            im = ax.imshow(iou_matrix, cmap='YlOrRd', vmin=0, vmax=1)
            ax.set_xticks(range(n_funcs))
            ax.set_yticks(range(n_funcs))
            ax.set_xticklabels([f[:10] for f in func_list], rotation=45, ha='right', fontsize=7)
            ax.set_yticklabels([f[:10] for f in func_list], fontsize=7)
            ax.set_title(f"k={k}", fontsize=10)
            
            # Add values
            for i in range(n_funcs):
                for j in range(n_funcs):
                    ax.text(j, i, f"{iou_matrix[i, j]:.2f}",
                           ha="center", va="center", fontsize=6)
        
        # Hide empty subplots
        for idx in range(n_k, n_rows * n_cols):
            row, col = idx // n_cols, idx % n_cols
            axes[row, col].axis('off')
        
        fig.suptitle("IoU Heatmaps (Pairwise Link Overlap)", fontsize=14)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        return fig
    
    def plot_unique_ratio(
        self,
        output_path: Optional[str] = None,
        figsize: tuple = (12, 6)
    ) -> Figure:
        """
        Plot unique link ratio for each function across k values.
        
        Ratio = |links from func| / |all unique links from all funcs|
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Compute unique ratios
        ratios_by_func: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                # Collect all links at this k
                all_links: Set[str] = set()
                func_links: Dict[str, Set[str]] = {}
                
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    links = set(result.get("links_after_filter", []))
                    func_links[func_name] = links
                    all_links.update(links)
                
                if not all_links:
                    continue
                
                for func_name, links in func_links.items():
                    ratio = len(links) / len(all_links)
                    ratios_by_func[func_name][k].append(ratio)
        
        colors = cm.tab10(np.linspace(0, 1, len(self.functions)))
        bar_width = 0.8 / len(self.functions)
        x = np.arange(len(self.k_values))
        
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = ratios_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            
            ax.bar(x + i * bar_width, means, bar_width, 
                   label=func_name, color=colors[i])
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Unique Link Ratio")
        ax.set_title("Ratio of Unique Links per Function to All Unique Links")
        ax.set_xticks(x + bar_width * (len(self.functions) - 1) / 2)
        ax.set_xticklabels([str(k) for k in self.k_values])
        ax.legend(fontsize=8, loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        return fig
    
    def plot_k_fulfillment(
        self,
        output_path: Optional[str] = None,
        figsize: tuple = (12, 6)
    ) -> Figure:
        """
        Plot k-fulfillment rate (actual/requested) across k values.
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        fulfillment_by_func: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    
                    requested = result.get("requested_k", k)
                    returned = result.get("returned_before_filter", 0)
                    rate = returned / requested if requested > 0 else 0
                    fulfillment_by_func[func_name][k].append(rate)
        
        colors = cm.tab10(np.linspace(0, 1, len(self.functions)))
        
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = fulfillment_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            ax.plot(self.k_values, means, marker='s', label=func_name, 
                   color=colors[i], linewidth=2)
        
        # Add reference line at 1.0 (100% fulfillment)
        ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='100% fulfillment')
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Fulfillment Rate (actual / requested)")
        ax.set_title("K-Fulfillment Rate: Were K Results Actually Returned?")
        ax.set_xscale("log", base=2)
        ax.set_ylim(0, 1.2)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        return fig
    
    def plot_date_issues(
        self,
        output_path: Optional[str] = None,
        figsize: tuple = (14, 8)
    ) -> Figure:
        """
        Plot date parsing failures and missing dates across k values.
        Shows how many results couldn't be date-filtered due to parsing errors or missing dates.
        """
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Aggregate date issues
        parse_failures_by_func: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        no_date_by_func: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        
        for query_id, k_results in self.results.items():
            for k, func_results in k_results.items():
                for func_name, result in func_results.items():
                    if "error" in result:
                        continue
                    parse_failures = result.get("date_parse_failures", 0)
                    no_date = result.get("no_date_count", 0)
                    parse_failures_by_func[func_name][k].append(parse_failures)
                    no_date_by_func[func_name][k].append(no_date)
        
        colors = cm.tab10(np.linspace(0, 1, len(self.functions)))
        
        # Plot date parse failures
        ax = axes[0]
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = parse_failures_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            ax.plot(self.k_values, means, marker='o', label=func_name, color=colors[i])
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Count (mean across queries)")
        ax.set_title("Date Parse Failures")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # Plot no date count
        ax = axes[1]
        for i, func_name in enumerate(self.functions):
            means = []
            for k in self.k_values:
                values = no_date_by_func[func_name].get(k, [0])
                means.append(np.mean(values) if values else 0)
            ax.plot(self.k_values, means, marker='o', label=func_name, color=colors[i])
        
        ax.set_xlabel("K (requested results)")
        ax.set_ylabel("Count (mean across queries)")
        ax.set_title("Results Without Date Information")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {output_path}")
        
        return fig
    
    def generate_all_plots(self, output_dir: str) -> List[str]:
        """
        Generate all plots and save to output directory.
        
        Returns:
            List of saved file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = []
        
        path = os.path.join(output_dir, "volume_vs_k.png")
        self.plot_volume_vs_k(output_path=path)
        saved_files.append(path)
        
        path = os.path.join(output_dir, "iou_heatmaps.png")
        self.plot_iou_heatmaps(output_path=path)
        saved_files.append(path)
        
        path = os.path.join(output_dir, "unique_ratio.png")
        self.plot_unique_ratio(output_path=path)
        saved_files.append(path)
        
        path = os.path.join(output_dir, "k_fulfillment.png")
        self.plot_k_fulfillment(output_path=path)
        saved_files.append(path)
        
        path = os.path.join(output_dir, "date_issues.png")
        self.plot_date_issues(output_path=path)
        saved_files.append(path)
        
        return saved_files


def main():
    """CLI entry point for generating plots from saved results."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate search volume plots")
    parser.add_argument("--results", type=str, required=True,
                        help="Path to results JSON file")
    parser.add_argument("--output-dir", type=str, default="./plots",
                        help="Output directory for plots")
    
    args = parser.parse_args()
    
    with open(args.results, "r") as f:
        results = json.load(f)
    
    # Convert string keys back to integers for k values
    converted = {}
    for query_id, k_results in results.items():
        converted[query_id] = {int(k): v for k, v in k_results.items()}
    
    plotter = SearchPlots(converted)
    saved = plotter.generate_all_plots(args.output_dir)
    print(f"\nGenerated {len(saved)} plots in {args.output_dir}")


if __name__ == "__main__":
    main()
