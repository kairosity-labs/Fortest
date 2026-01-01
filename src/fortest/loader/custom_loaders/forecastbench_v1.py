"""
ForecastBench v1 Loaders

Provides flexible data loaders for the ForecastBench_v1 resolved dataset with:
- Source-wise loading
- Extensive (all sources) loading
- Horizon grouping (short/near/medium/long/very-long/extended)
- Stratified sampling with reproducibility
"""

import os
import json
import random
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from fortest.loader.loader import ProblemLoader, base_process_problem


class HorizonGroup(Enum):
    """Horizon group definitions with (min_days, max_days, name)."""
    SHORT_TERM = (0, 7, "short_term")
    NEAR_TERM = (7, 30, "near_term")
    MEDIUM_TERM = (30, 90, "medium_term")
    LONG_TERM = (90, 180, "long_term")
    VERY_LONG_TERM = (180, 365, "very_long_term")
    EXTENDED = (365, float('inf'), "extended")
    
    @property
    def min_days(self) -> int:
        return self.value[0]
    
    @property
    def max_days(self) -> float:
        return self.value[1]
    
    @property
    def label(self) -> str:
        return self.value[2]
    
    @classmethod
    def from_days(cls, days: int) -> 'HorizonGroup':
        """Get horizon group for a given number of days."""
        for group in cls:
            if group.min_days <= days < group.max_days:
                return group
        return cls.EXTENDED


# Sources categorization
DATA_SOURCES = {'acled', 'dbnomics', 'fred', 'wikipedia', 'yfinance'}
MARKET_SOURCES = {'manifold', 'metaculus', 'polymarket', 'infer'}
ALL_SOURCES = DATA_SOURCES | MARKET_SOURCES


def _get_data_dir() -> Path:
    """Get path to ForecastBench_v1 data directory."""
    return Path(__file__).parent.parent.parent / "problems" / "ForecastBench_v1"


def _load_raw_data() -> Tuple[List[Dict], List[Dict]]:
    """Load X and y data from JSON files."""
    data_dir = _get_data_dir()
    
    with open(data_dir / "X_single_resolved.json") as f:
        X_data = json.load(f)['questions']
    with open(data_dir / "y_single_resolved.json") as f:
        y_data = json.load(f)['resolutions']
    
    return X_data, y_data


def _compute_horizon(question: Dict, resolution: Dict) -> Optional[int]:
    """Compute horizon in days from start to resolution date."""
    # Use start_date if available (templatized questions), else forecast_due_date
    start = question.get('start_date') or question.get('forecast_due_date')
    end = question.get('end_date') or resolution.get('resolution_date')
    
    if not start or not end or start == 'N/A' or end == 'N/A':
        return None
    
    try:
        start_dt = datetime.strptime(start.split('T')[0], '%Y-%m-%d')
        end_dt = datetime.strptime(end.split('T')[0], '%Y-%m-%d')
        return (end_dt - start_dt).days
    except ValueError:
        return None


def _build_problem(question: Dict, resolution: Dict, horizon_days: Optional[int]) -> Dict[str, Any]:
    """Build a problem dict matching the expected interface."""
    qid = question.get('id')
    source = question.get('source', 'unknown')
    question_set = question.get('question_set', '')
    
    horizon_group = HorizonGroup.from_days(horizon_days) if horizon_days else None
    
    problem = {
        "problem_id": f"fbv1_{source}_{qid}",
        "question": question.get('question'),
        "time_start": question.get('start_date') or question.get('forecast_due_date'),
        "time_end": question.get('end_date') or resolution.get('resolution_date'),
        "resolved_flag": True,
        "resolution_status": resolution.get('resolved_to'),
        "metadata": {
            "source": source,
            "horizon": horizon_group.label if horizon_group else None,
            "horizon_days": horizon_days,
            "original_id": qid,
            "question_set": question_set,
            "background": question.get('background'),
            "resolution_criteria": question.get('resolution_criteria'),
            "url": question.get('url'),
            "freeze_datetime_value": question.get('freeze_datetime_value'),
        }
    }
    
    # Add time_testing from freeze_datetime
    time_testing = question.get('freeze_datetime')
    return base_process_problem(problem, time_testing=time_testing)


def _load_and_prepare_all() -> List[Dict[str, Any]]:
    """Load all data and prepare problem dicts with horizons."""
    X_data, y_data = _load_raw_data()
    
    # Build lookup for resolutions
    y_lookup = {}
    for y in y_data:
        key = (y.get('question_set'), y.get('id'))
        y_lookup[key] = y
    
    problems = []
    for q in X_data:
        key = (q.get('question_set'), q.get('id'))
        y = y_lookup.get(key, {})
        
        horizon = _compute_horizon(q, y)
        if horizon is None or horizon <= 0:
            continue  # Skip questions without valid horizon
        
        problem = _build_problem(q, y, horizon)
        problems.append(problem)
    
    return problems


def _stratified_sample(
    problems: List[Dict],
    max_quest: int,
    seed: int,
    sources: Optional[List[str]] = None,
    horizons: Optional[List[str]] = None,
) -> Dict[str, Dict]:
    """
    Stratified sampling across sources and horizons.
    
    For data sources: uniform sampling across horizons
    For market sources: stratified sampling from horizon groups
    
    Redistributes unused quota from limited sources to larger ones.
    """
    random.seed(seed)
    
    # Group by source and horizon
    by_source_horizon = defaultdict(lambda: defaultdict(list))
    by_source_all = defaultdict(list)
    
    for p in problems:
        src = p['metadata']['source']
        h = p['metadata']['horizon']
        
        # Filter by sources if specified
        if sources and src not in sources:
            continue
        # Filter by horizons if specified
        if horizons and h not in horizons:
            continue
            
        by_source_horizon[src][h].append(p)
        by_source_all[src].append(p)
    
    if not by_source_horizon:
        return {}
    
    # Calculate initial questions per source
    active_sources = list(by_source_horizon.keys())
    per_source = max(1, max_quest // len(active_sources))
    
    selected = {}
    
    # First pass: sample up to per_source from each source
    source_counts = {}
    for src in active_sources:
        all_src = by_source_all[src][:]
        random.shuffle(all_src)
        
        if src in MARKET_SOURCES:
            # Market sources: try stratified sampling from horizon groups
            src_problems = by_source_horizon[src]
            horizon_groups = list(src_problems.keys())
            if horizon_groups:
                per_horizon = max(1, per_source // len(horizon_groups))
                src_selected = []
                for h in horizon_groups:
                    h_list = src_problems[h][:]
                    random.shuffle(h_list)
                    src_selected.extend(h_list[:per_horizon])
                
                # Fill remainder
                remaining_ids = {p['problem_id'] for p in src_selected}
                for p in all_src:
                    if len(src_selected) >= per_source:
                        break
                    if p['problem_id'] not in remaining_ids:
                        src_selected.append(p)
                
                for p in src_selected[:per_source]:
                    selected[p['problem_id']] = p
                source_counts[src] = min(len(src_selected), per_source)
            else:
                source_counts[src] = 0
        else:
            # Data sources: uniform sampling
            for p in all_src[:per_source]:
                selected[p['problem_id']] = p
            source_counts[src] = min(len(all_src), per_source)
    
    # Second pass: redistribute unused quota to sources with more data
    total_selected = len(selected)
    remaining_quota = max_quest - total_selected
    
    if remaining_quota > 0:
        # Sort sources by available remaining questions (descending)
        sources_with_capacity = []
        for src in active_sources:
            already_taken = source_counts.get(src, 0)
            available = len(by_source_all[src]) - already_taken
            if available > 0:
                sources_with_capacity.append((src, available))
        
        sources_with_capacity.sort(key=lambda x: -x[1])
        
        for src, available in sources_with_capacity:
            if remaining_quota <= 0:
                break
            
            # Get questions not yet selected from this source
            selected_ids = set(selected.keys())
            additional = []
            for p in by_source_all[src]:
                if p['problem_id'] not in selected_ids:
                    additional.append(p)
            
            random.shuffle(additional)
            to_add = min(len(additional), remaining_quota)
            for p in additional[:to_add]:
                selected[p['problem_id']] = p
                remaining_quota -= 1
    
    # Final trim if somehow exceeded
    if len(selected) > max_quest:
        all_selected = list(selected.values())
        random.shuffle(all_selected)
        selected = {p['problem_id']: p for p in all_selected[:max_quest]}
    
    return selected


@ProblemLoader.register("forecastbench_v1")
def load_forecastbench_v1(
    raw_problems: List[Dict],
    max_quest: int = 200,
    seed: int = 42,
    sources: Optional[List[str]] = None,
    horizons: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Load ForecastBench v1 resolved questions with flexible filtering.
    
    Args:
        raw_problems: Ignored (loads from ForecastBench_v1 files)
        max_quest: Maximum questions to return (default 200)
        seed: Random seed for reproducibility
        sources: List of sources to include (None = all)
        horizons: List of horizon groups to include (None = all)
    
    Returns:
        Dict mapping problem_id to problem dict
    """
    problems = _load_and_prepare_all()
    return _stratified_sample(problems, max_quest, seed, sources, horizons)


@ProblemLoader.register("forecastbench_v1_source")
def load_by_source(
    raw_problems: List[Dict],
    source: str,
    max_quest: int = 200,
    seed: int = 42,
    horizons: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Load ForecastBench v1 questions from a single source.
    
    Args:
        raw_problems: Ignored
        source: Source name (e.g., 'fred', 'manifold')
        max_quest: Maximum questions to return
        seed: Random seed
        horizons: List of horizon groups to include
    
    Returns:
        Dict mapping problem_id to problem dict
    """
    if source not in ALL_SOURCES:
        raise ValueError(f"Unknown source: {source}. Available: {ALL_SOURCES}")
    
    problems = _load_and_prepare_all()
    return _stratified_sample(problems, max_quest, seed, sources=[source], horizons=horizons)


@ProblemLoader.register("forecastbench_v1_extensive")
def load_extensive(
    raw_problems: List[Dict],
    max_quest: int = 200,
    seed: int = 42,
    **kwargs
) -> Dict[str, Any]:
    """
    Load ForecastBench v1 questions with equal distribution across all sources.
    
    Args:
        raw_problems: Ignored
        max_quest: Maximum questions to return
        seed: Random seed
    
    Returns:
        Dict mapping problem_id to problem dict
    """
    problems = _load_and_prepare_all()
    return _stratified_sample(problems, max_quest, seed, sources=list(ALL_SOURCES))


def get_horizon_summary(problems: Dict[str, Dict]) -> Dict[str, Dict[str, int]]:
    """
    Get summary of loaded problems by source and horizon.
    
    Returns:
        Dict[source -> Dict[horizon -> count]]
    """
    summary = defaultdict(lambda: defaultdict(int))
    for p in problems.values():
        src = p['metadata']['source']
        h = p['metadata']['horizon']
        summary[src][h] += 1
    return dict(summary)


def get_sources_list() -> List[str]:
    """Get list of all available sources."""
    return sorted(list(ALL_SOURCES))


def get_horizons_list() -> List[str]:
    """Get list of all horizon group names."""
    return [h.label for h in HorizonGroup]
