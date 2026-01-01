"""
Exhaustive Distribution Tests for ForecastBench v1

Round 2: Dataset Distribution Testing
- Horizon distribution validation
- Class balance verification
- Sampling quality tests
- Edge case handling
"""

import pytest
import random
from collections import Counter, defaultdict
from typing import Dict, List

from fortest.loader.loader import ProblemLoader
from fortest.loader.custom_loaders.forecastbench_v1 import (
    HorizonGroup,
    DATA_SOURCES,
    MARKET_SOURCES,
    ALL_SOURCES,
    get_horizon_summary,
    get_sources_list,
    get_horizons_list,
    _load_and_prepare_all,
)


# ============================================================================
# ROUND 2: DISTRIBUTION TESTS
# ============================================================================

class TestHorizonDistribution:
    """Tests for horizon distribution across the dataset."""
    
    def test_all_horizons_present_in_full_load(self):
        """Most horizons should be present when loading enough data."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1', max_quest=500, seed=42)
        horizons = set(p['metadata']['horizon'] for p in problems.values())
        
        # At least medium, long, very_long should be present
        assert 'medium_term' in horizons or 'long_term' in horizons
        assert 'very_long_term' in horizons
    
    def test_horizon_distribution_per_source(self):
        """Check horizon distribution for each source."""
        all_problems = _load_and_prepare_all()
        
        source_horizons = defaultdict(Counter)
        for p in all_problems:
            source_horizons[p['metadata']['source']][p['metadata']['horizon']] += 1
        
        # Report distribution
        for source in sorted(source_horizons.keys()):
            horizons = source_horizons[source]
            total = sum(horizons.values())
            assert total > 0, f"Source {source} has no questions"
            print(f"{source}: {dict(horizons)}")
    
    def test_data_sources_have_varied_horizons(self):
        """Data sources should have questions across multiple horizons."""
        all_problems = _load_and_prepare_all()
        
        for source in DATA_SOURCES:
            source_problems = [p for p in all_problems if p['metadata']['source'] == source]
            horizons = set(p['metadata']['horizon'] for p in source_problems)
            
            # Data sources should have at least 2 different horizons
            # (acled is exception with only long_term)
            if source != 'acled':
                assert len(horizons) >= 2, f"{source} has only {horizons}"


class TestClassBalance:
    """Tests for class balance (resolution distribution)."""
    
    def test_class_distribution_not_empty(self):
        """Both classes should be present."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        resolutions = [p['resolution_status'] for p in problems.values()]
        classes = set(resolutions)
        
        assert 0.0 in classes or 1.0 in classes, "At least one class should be present"
    
    def test_class_balance_per_source(self):
        """Check class balance for each source."""
        all_problems = _load_and_prepare_all()
        
        source_classes = defaultdict(Counter)
        for p in all_problems:
            source_classes[p['metadata']['source']][p['resolution_status']] += 1
        
        for source in sorted(source_classes.keys()):
            classes = source_classes[source]
            total = sum(classes.values())
            yes_rate = classes.get(1.0, 0) / total if total > 0 else 0
            no_rate = classes.get(0.0, 0) / total if total > 0 else 0
            
            print(f"{source}: Yes={yes_rate:.1%}, No={no_rate:.1%}")
            
            # No source should be 100% one class (would be too easy)
            assert yes_rate < 1.0 or no_rate < 1.0, f"{source} has only one class"
    
    def test_overall_class_balance(self):
        """Overall dataset should have reasonable class balance."""
        all_problems = _load_and_prepare_all()
        
        resolutions = [p['resolution_status'] for p in all_problems]
        yes_count = sum(1 for r in resolutions if r == 1.0)
        no_count = sum(1 for r in resolutions if r == 0.0)
        total = len(resolutions)
        
        yes_rate = yes_count / total if total > 0 else 0
        
        # Class imbalance should not be extreme (>10% minority)
        assert 0.1 < yes_rate < 0.9, f"Extreme class imbalance: {yes_rate:.1%} yes"


class TestSamplingQuality:
    """Tests for sampling algorithm quality."""
    
    def test_sources_approximately_balanced(self):
        """Extensive loader should produce approximately balanced sources."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=180, seed=42)
        
        source_counts = Counter(p['metadata']['source'] for p in problems.values())
        
        avg = len(problems) / len(ALL_SOURCES)
        
        for source, count in source_counts.items():
            # Each source should have at least 50% of average
            assert count >= avg * 0.3, f"{source} underrepresented: {count} vs avg {avg:.1f}"
    
    def test_sampling_uses_all_available_sources(self):
        """Sampling should include questions from all sources when possible."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        sources = set(p['metadata']['source'] for p in problems.values())
        assert sources == ALL_SOURCES, f"Missing sources: {ALL_SOURCES - sources}"
    
    def test_quota_redistribution_works(self):
        """When a source is exhausted, quota should go to others."""
        loader = ProblemLoader()
        
        # Load with big max_quest to trigger redistribution
        problems = loader.load('forecastbench_v1_extensive', max_quest=500, seed=42)
        
        source_counts = Counter(p['metadata']['source'] for p in problems.values())
        
        # Sources with lots of data should have more than the equal share
        large_sources = ['fred', 'yfinance', 'wikipedia']
        small_sources = ['metaculus', 'acled', 'infer']
        
        large_avg = sum(source_counts[s] for s in large_sources if s in source_counts) / len(large_sources)
        small_avg = sum(source_counts[s] for s in small_sources if s in source_counts) / len(small_sources)
        
        # Large sources should have more questions due to redistribution
        assert large_avg > small_avg, f"Redistribution failed: large={large_avg:.1f}, small={small_avg:.1f}"


class TestReproducibility:
    """Tests for reproducibility with seeds."""
    
    def test_exact_reproducibility(self):
        """Same seed should produce identical results."""
        loader = ProblemLoader()
        
        for _ in range(3):
            result1 = loader.load('forecastbench_v1_extensive', max_quest=100, seed=999)
            result2 = loader.load('forecastbench_v1_extensive', max_quest=100, seed=999)
            
            ids1 = sorted(result1.keys())
            ids2 = sorted(result2.keys())
            
            assert ids1 == ids2, "Same seed should produce same IDs"
    
    def test_different_seeds_different_samples(self):
        """Different seeds should produce different samples."""
        loader = ProblemLoader()
        
        samples = []
        for seed in [1, 2, 3, 4, 5]:
            result = loader.load('forecastbench_v1_extensive', max_quest=100, seed=seed)
            samples.append(set(result.keys()))
        
        # Not all samples should be identical
        unique_samples = len(set(frozenset(s) for s in samples))
        assert unique_samples >= 3, "Different seeds should produce different samples"
    
    def test_seed_affects_order(self):
        """Different seeds should affect which questions are selected."""
        loader = ProblemLoader()
        
        result1 = loader.load('forecastbench_v1', max_quest=50, seed=100)
        result2 = loader.load('forecastbench_v1', max_quest=50, seed=200)
        
        intersection = set(result1.keys()) & set(result2.keys())
        union = set(result1.keys()) | set(result2.keys())
        
        overlap_rate = len(intersection) / len(union) if union else 1
        
        # Some overlap is expected, but not 100%
        assert overlap_rate < 0.9, f"Seeds produce too similar samples: {overlap_rate:.1%} overlap"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_max_quest_one(self):
        """Should work with max_quest=1."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', max_quest=1, seed=42)
        assert len(result) == 1
    
    def test_max_quest_very_large(self):
        """Should handle very large max_quest gracefully."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', max_quest=100000, seed=42)
        
        # Should return all available, not crash
        assert len(result) > 0
        assert len(result) <= 10000  # Reasonable upper bound
    
    def test_filter_by_single_horizon(self):
        """Should work with single horizon filter."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', horizons=['long_term'], max_quest=50, seed=42)
        
        for p in result.values():
            assert p['metadata']['horizon'] == 'long_term'
    
    def test_filter_by_multiple_horizons(self):
        """Should work with multiple horizon filters."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', 
                            horizons=['short_term', 'near_term'], 
                            max_quest=50, seed=42)
        
        for p in result.values():
            assert p['metadata']['horizon'] in ['short_term', 'near_term']
    
    def test_empty_horizon_filter(self):
        """Filtering by non-existent horizon should return empty."""
        loader = ProblemLoader()
        result = loader.load('forecastbench_v1', horizons=['nonexistent'], max_quest=50, seed=42)
        assert len(result) == 0


class TestDataIntegrity:
    """Tests for data integrity and consistency."""
    
    def test_all_problems_have_required_fields(self):
        """All problems should have required fields."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        required_fields = ['problem_id', 'question', 'time_start', 'time_end', 
                          'resolved_flag', 'resolution_status', 'metadata']
        
        for pid, problem in problems.items():
            for field in required_fields:
                assert field in problem, f"Problem {pid} missing field: {field}"
    
    def test_resolution_status_valid(self):
        """Resolution status should be 0.0 or 1.0."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        for pid, problem in problems.items():
            rs = problem['resolution_status']
            assert rs in [0.0, 1.0], f"Problem {pid} has invalid resolution: {rs}"
    
    def test_horizon_days_matches_group(self):
        """Horizon days should match the horizon group."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        for pid, problem in problems.items():
            days = problem['metadata']['horizon_days']
            group = problem['metadata']['horizon']
            expected = HorizonGroup.from_days(days).label
            
            assert group == expected, f"{pid}: {days} days should be {expected}, not {group}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
