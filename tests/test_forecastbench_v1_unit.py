"""
Exhaustive Unit Tests for ForecastBench v1 Pipeline

Round 1: Unit Level Testing
- Loader components
- Data structures
- Metrics functions
"""

import pytest
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import Counter

# Module imports
from fortest.loader.loader import ProblemLoader, base_process_problem
from fortest.loader.custom_loaders.forecastbench_v1 import (
    HorizonGroup,
    DATA_SOURCES,
    MARKET_SOURCES,
    ALL_SOURCES,
    _get_data_dir,
    _load_raw_data,
    _compute_horizon,
    _build_problem,
    _load_and_prepare_all,
    _stratified_sample,
    get_horizon_summary,
    get_sources_list,
    get_horizons_list,
)
from fortest.metrics.metrics import brier_score, accuracy


# ============================================================================
# ROUND 1: UNIT LEVEL TESTS
# ============================================================================

class TestHorizonGroup:
    """Tests for HorizonGroup enum."""
    
    def test_horizon_group_values(self):
        """Test that all horizon groups have correct structure."""
        for group in HorizonGroup:
            assert hasattr(group, 'min_days')
            assert hasattr(group, 'max_days')
            assert hasattr(group, 'label')
            assert isinstance(group.min_days, int)
            assert isinstance(group.label, str)
    
    def test_horizon_group_ranges_no_overlap(self):
        """Test that horizon ranges don't overlap."""
        groups = list(HorizonGroup)
        for i in range(len(groups) - 1):
            assert groups[i].max_days == groups[i + 1].min_days, \
                f"Gap or overlap between {groups[i].label} and {groups[i+1].label}"
    
    def test_horizon_group_from_days(self):
        """Test from_days classification."""
        test_cases = [
            (0, HorizonGroup.SHORT_TERM),
            (3, HorizonGroup.SHORT_TERM),
            (7, HorizonGroup.NEAR_TERM),
            (15, HorizonGroup.NEAR_TERM),
            (30, HorizonGroup.MEDIUM_TERM),
            (60, HorizonGroup.MEDIUM_TERM),
            (90, HorizonGroup.LONG_TERM),
            (120, HorizonGroup.LONG_TERM),
            (180, HorizonGroup.VERY_LONG_TERM),
            (300, HorizonGroup.VERY_LONG_TERM),
            (365, HorizonGroup.EXTENDED),
            (500, HorizonGroup.EXTENDED),
            (1000, HorizonGroup.EXTENDED),
        ]
        for days, expected in test_cases:
            result = HorizonGroup.from_days(days)
            assert result == expected, f"from_days({days}) should be {expected.label}, got {result.label}"
    
    def test_all_labels_unique(self):
        """Test that all horizon labels are unique."""
        labels = [h.label for h in HorizonGroup]
        assert len(labels) == len(set(labels)), "Horizon labels must be unique"


class TestSourceConstants:
    """Tests for source-related constants."""
    
    def test_sources_are_disjoint(self):
        """Data and market sources should not overlap."""
        overlap = DATA_SOURCES & MARKET_SOURCES
        assert len(overlap) == 0, f"Sources overlap: {overlap}"
    
    def test_all_sources_is_union(self):
        """ALL_SOURCES should be union of data and market sources."""
        assert ALL_SOURCES == DATA_SOURCES | MARKET_SOURCES
    
    def test_expected_sources_present(self):
        """Check expected sources are present."""
        expected_data = {'acled', 'dbnomics', 'fred', 'wikipedia', 'yfinance'}
        expected_market = {'manifold', 'metaculus', 'polymarket', 'infer'}
        assert expected_data == DATA_SOURCES
        assert expected_market == MARKET_SOURCES


class TestDataLoading:
    """Tests for data loading functions."""
    
    def test_get_data_dir_exists(self):
        """Data directory should exist."""
        data_dir = _get_data_dir()
        assert data_dir.exists(), f"Data directory not found: {data_dir}"
    
    def test_data_files_exist(self):
        """Required JSON files should exist."""
        data_dir = _get_data_dir()
        required_files = [
            'X_single_resolved.json',
            'y_single_resolved.json',
            'X_compose_resolved.json',
            'y_compose_resolved.json',
        ]
        for f in required_files:
            path = data_dir / f
            assert path.exists(), f"Missing file: {path}"
    
    def test_load_raw_data_returns_lists(self):
        """_load_raw_data should return two lists."""
        X_data, y_data = _load_raw_data()
        assert isinstance(X_data, list), "X_data should be a list"
        assert isinstance(y_data, list), "y_data should be a list"
    
    def test_raw_data_not_empty(self):
        """Raw data should not be empty."""
        X_data, y_data = _load_raw_data()
        assert len(X_data) > 0, "X_data should not be empty"
        assert len(y_data) > 0, "y_data should not be empty"
    
    def test_x_y_same_length(self):
        """X and y data should have same length."""
        X_data, y_data = _load_raw_data()
        assert len(X_data) == len(y_data), f"X ({len(X_data)}) != y ({len(y_data)})"


class TestComputeHorizon:
    """Tests for _compute_horizon function."""
    
    def test_compute_horizon_valid_dates(self):
        """Test with valid date strings."""
        question = {'start_date': '2024-01-01', 'forecast_due_date': '2024-01-01'}
        resolution = {'resolution_date': '2024-01-11'}
        result = _compute_horizon(question, resolution)
        assert result == 10
    
    def test_compute_horizon_with_datetime(self):
        """Test with ISO datetime format."""
        question = {'start_date': '2024-01-01T00:00:00+00:00'}
        resolution = {'resolution_date': '2024-02-01'}
        result = _compute_horizon(question, resolution)
        assert result == 31
    
    def test_compute_horizon_na_returns_none(self):
        """Test that N/A dates return None."""
        question = {'start_date': 'N/A'}
        resolution = {'resolution_date': '2024-01-11'}
        assert _compute_horizon(question, resolution) is None
    
    def test_compute_horizon_missing_dates(self):
        """Test with missing date fields."""
        assert _compute_horizon({}, {}) is None
        assert _compute_horizon({'start_date': '2024-01-01'}, {}) is None
    
    def test_compute_horizon_uses_forecast_due_fallback(self):
        """Test that forecast_due_date is used when start_date is missing."""
        question = {'forecast_due_date': '2024-01-01'}
        resolution = {'resolution_date': '2024-01-15'}
        result = _compute_horizon(question, resolution)
        assert result == 14


class TestBuildProblem:
    """Tests for _build_problem function."""
    
    def test_build_problem_required_fields(self):
        """Built problem should have required fields."""
        question = {
            'id': 'test_id',
            'source': 'fred',
            'question': 'Test question?',
            'question_set': 'test_set',
            'forecast_due_date': '2024-01-01',
            'freeze_datetime': '2024-01-01T00:00:00Z',
        }
        resolution = {'resolution_date': '2024-06-01'}
        
        problem = _build_problem(question, resolution, 150)
        
        assert 'problem_id' in problem
        assert 'question' in problem
        assert 'time_start' in problem
        assert 'time_end' in problem
        assert 'resolved_flag' in problem
        assert 'metadata' in problem
        assert 'time_testing' in problem
        assert 'time_now' in problem
    
    def test_build_problem_metadata_content(self):
        """Metadata should contain expected fields."""
        question = {
            'id': 'test_id',
            'source': 'manifold',
            'question': 'Test?',
            'background': 'Background info',
            'url': 'https://example.com',
        }
        resolution = {}
        
        problem = _build_problem(question, resolution, 90)
        
        assert problem['metadata']['source'] == 'manifold'
        assert problem['metadata']['horizon'] == 'long_term'  # 90 days is boundary, goes to long_term
        assert problem['metadata']['horizon_days'] == 90
        assert problem['metadata']['background'] == 'Background info'


class TestMetrics:
    """Tests for metric calculations."""
    
    def test_brier_score_perfect(self):
        """Perfect predictions should have Brier score 0."""
        predictions = [1.0, 0.0, 1.0, 0.0]
        outcomes = [1, 0, 1, 0]
        assert brier_score(predictions, outcomes) == 0.0
    
    def test_brier_score_worst(self):
        """Worst predictions should have Brier score 1."""
        predictions = [0.0, 1.0, 0.0, 1.0]
        outcomes = [1, 0, 1, 0]
        assert brier_score(predictions, outcomes) == 1.0
    
    def test_brier_score_random(self):
        """50% predictions should have Brier score 0.25."""
        predictions = [0.5, 0.5, 0.5, 0.5]
        outcomes = [1, 0, 1, 0]
        assert abs(brier_score(predictions, outcomes) - 0.25) < 0.001
    
    def test_brier_score_empty(self):
        """Empty inputs should return 0."""
        assert brier_score([], []) == 0.0
    
    def test_brier_score_length_mismatch(self):
        """Mismatched lengths should raise error."""
        with pytest.raises(ValueError):
            brier_score([0.5, 0.5], [1])
    
    def test_accuracy_perfect(self):
        """Perfect predictions should have accuracy 1.0."""
        predictions = [0.9, 0.1, 0.8, 0.2]
        outcomes = [1, 0, 1, 0]
        assert accuracy(predictions, outcomes) == 1.0
    
    def test_accuracy_worst(self):
        """Worst predictions should have accuracy 0.0."""
        predictions = [0.1, 0.9, 0.2, 0.8]
        outcomes = [1, 0, 1, 0]
        assert accuracy(predictions, outcomes) == 0.0
    
    def test_accuracy_threshold(self):
        """Custom threshold should work correctly."""
        predictions = [0.6, 0.6, 0.6, 0.6]
        outcomes = [1, 1, 1, 1]
        assert accuracy(predictions, outcomes, threshold=0.5) == 1.0
        assert accuracy(predictions, outcomes, threshold=0.7) == 0.0


class TestProblemLoader:
    """Tests for ProblemLoader class."""
    
    def test_loader_initialization(self):
        """Loader should initialize without error."""
        loader = ProblemLoader()
        assert loader is not None
    
    def test_list_available_loaders(self):
        """Should list registered loaders."""
        loader = ProblemLoader()
        available = loader.list_available_loaders()
        assert 'forecastbench_v1' in available
        assert 'forecastbench_v1_source' in available
        assert 'forecastbench_v1_extensive' in available
    
    def test_invalid_loader_raises(self):
        """Invalid loader strategy should raise error."""
        loader = ProblemLoader()
        with pytest.raises(ValueError):
            loader.load('nonexistent_loader')


class TestForecastBenchV1Loaders:
    """Tests for ForecastBench v1 loader functions."""
    
    def test_base_loader_returns_dict(self):
        """Base loader should return dict."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', max_quest=10, seed=42)
        assert isinstance(result, dict)
    
    def test_base_loader_respects_max_quest(self):
        """Loader should not exceed max_quest."""
        loader = ProblemLoader()
        for max_q in [10, 50, 100]:
            result = loader.load('forecastbench_v1', max_quest=max_q, seed=42)
            assert len(result) <= max_q, f"Got {len(result)} > {max_q}"
    
    def test_source_loader_filters_correctly(self):
        """Source loader should only return requested source."""
        loader = ProblemLoader()
        for source in ['fred', 'manifold', 'acled']:
            result = loader.load('forecastbench_v1_source', source=source, max_quest=20, seed=42)
            for p in result.values():
                assert p['metadata']['source'] == source, \
                    f"Expected {source}, got {p['metadata']['source']}"
    
    def test_source_loader_invalid_source(self):
        """Invalid source should raise error."""
        loader = ProblemLoader()
        with pytest.raises(ValueError):
            loader.load('forecastbench_v1_source', source='invalid_source')
    
    def test_extensive_loader_includes_multiple_sources(self):
        """Extensive loader should include questions from multiple sources."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1_extensive', max_quest=100, seed=42)
        sources = set(p['metadata']['source'] for p in result.values())
        assert len(sources) >= 5, f"Expected >= 5 sources, got {len(sources)}: {sources}"
    
    def test_reproducibility_with_same_seed(self):
        """Same seed should produce same results."""
        loader = ProblemLoader()
        result1 = loader.load('forecastbench_v1_extensive', max_quest=50, seed=123)
        result2 = loader.load('forecastbench_v1_extensive', max_quest=50, seed=123)
        assert set(result1.keys()) == set(result2.keys())
    
    def test_different_seeds_produce_different_results(self):
        """Different seeds should produce different results."""
        loader = ProblemLoader()
        result1 = loader.load('forecastbench_v1_extensive', max_quest=50, seed=123)
        result2 = loader.load('forecastbench_v1_extensive', max_quest=50, seed=456)
        # Should have some difference (not guaranteed to be completely different)
        assert result1.keys() != result2.keys() or len(result1) < 10


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_get_sources_list(self):
        """Should return list of all sources."""
        sources = get_sources_list()
        assert len(sources) == 9
        assert set(sources) == ALL_SOURCES
    
    def test_get_horizons_list(self):
        """Should return list of horizon labels."""
        horizons = get_horizons_list()
        assert len(horizons) == 6
        expected = ['short_term', 'near_term', 'medium_term', 'long_term', 'very_long_term', 'extended']
        assert horizons == expected
    
    def test_get_horizon_summary(self):
        """Summary should have correct structure."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=50, seed=42)
        summary = get_horizon_summary(problems)
        
        assert isinstance(summary, dict)
        for source, horizons in summary.items():
            assert source in ALL_SOURCES
            assert isinstance(horizons, dict)
            for h, count in horizons.items():
                assert h in get_horizons_list()
                assert isinstance(count, int)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
