"""
Tests for Search Volume Analyzer.

Tests the metrics calculations and core functionality of the
pastcasting search volume analysis system.
"""

import pytest
from fortest.environment.search_core.search_analyzer import SearchVolumeAnalyzer


class TestIoUCalculation:
    """Test Intersection over Union calculations."""
    
    def test_iou_identical_sets(self):
        """IoU of identical sets should be 1.0."""
        links_a = ["url1", "url2", "url3"]
        links_b = ["url1", "url2", "url3"]
        assert SearchVolumeAnalyzer.compute_iou(links_a, links_b) == 1.0
    
    def test_iou_disjoint_sets(self):
        """IoU of completely different sets should be 0.0."""
        links_a = ["url1", "url2", "url3"]
        links_b = ["url4", "url5", "url6"]
        assert SearchVolumeAnalyzer.compute_iou(links_a, links_b) == 0.0
    
    def test_iou_partial_overlap(self):
        """IoU with partial overlap."""
        links_a = ["url1", "url2", "url3"]
        links_b = ["url2", "url3", "url4"]
        # Intersection: {url2, url3} = 2
        # Union: {url1, url2, url3, url4} = 4
        # IoU = 2/4 = 0.5
        assert SearchVolumeAnalyzer.compute_iou(links_a, links_b) == 0.5
    
    def test_iou_one_empty(self):
        """IoU with one empty set should be 0.0."""
        links_a = ["url1", "url2"]
        links_b = []
        assert SearchVolumeAnalyzer.compute_iou(links_a, links_b) == 0.0
    
    def test_iou_both_empty(self):
        """IoU of two empty sets should be 1.0."""
        assert SearchVolumeAnalyzer.compute_iou([], []) == 1.0
    
    def test_iou_handles_duplicates(self):
        """IoU should handle duplicates correctly (uses sets)."""
        links_a = ["url1", "url1", "url2"]
        links_b = ["url2", "url2", "url3"]
        # Sets: {url1, url2} and {url2, url3}
        # Intersection: {url2} = 1
        # Union: {url1, url2, url3} = 3
        # IoU = 1/3
        assert SearchVolumeAnalyzer.compute_iou(links_a, links_b) == pytest.approx(1/3)


class TestUniqueRatioCalculation:
    """Test unique link ratio calculations."""
    
    def test_unique_ratio_full_contribution(self):
        """When all links are from one function, ratio = 1.0."""
        links = ["url1", "url2", "url3"]
        all_links = {"url1", "url2", "url3"}
        assert SearchVolumeAnalyzer.compute_unique_ratio(links, all_links) == 1.0
    
    def test_unique_ratio_partial_contribution(self):
        """Partial contribution should give proportional ratio."""
        links = ["url1", "url2"]
        all_links = {"url1", "url2", "url3", "url4"}
        # 2 of 4 = 0.5
        assert SearchVolumeAnalyzer.compute_unique_ratio(links, all_links) == 0.5
    
    def test_unique_ratio_no_contribution(self):
        """Empty links should give 0.0 ratio."""
        links = []
        all_links = {"url1", "url2"}
        assert SearchVolumeAnalyzer.compute_unique_ratio(links, all_links) == 0.0
    
    def test_unique_ratio_empty_all_links(self):
        """Empty all_links should give 0.0 ratio."""
        links = ["url1"]
        all_links = set()
        assert SearchVolumeAnalyzer.compute_unique_ratio(links, all_links) == 0.0


class TestKFulfillmentCalculation:
    """Test k-fulfillment rate calculations."""
    
    def test_k_fulfillment_exact(self):
        """Exact fulfillment should be 1.0."""
        assert SearchVolumeAnalyzer.compute_k_fulfillment(10, 10) == 1.0
    
    def test_k_fulfillment_under(self):
        """Under-fulfillment should be < 1.0."""
        assert SearchVolumeAnalyzer.compute_k_fulfillment(100, 50) == 0.5
    
    def test_k_fulfillment_over(self):
        """Over-fulfillment should be > 1.0."""
        assert SearchVolumeAnalyzer.compute_k_fulfillment(10, 15) == 1.5
    
    def test_k_fulfillment_zero_requested(self):
        """Zero requested with zero returned should be 1.0."""
        assert SearchVolumeAnalyzer.compute_k_fulfillment(0, 0) == 1.0
    
    def test_k_fulfillment_zero_requested_nonzero_returned(self):
        """Zero requested with nonzero returned should be 0.0."""
        assert SearchVolumeAnalyzer.compute_k_fulfillment(0, 5) == 0.0


class TestSearchVolumeAnalyzerInit:
    """Test SearchVolumeAnalyzer initialization."""
    
    def test_k_values_ascending(self):
        """K_VALUES should be in ascending order."""
        k_values = SearchVolumeAnalyzer.K_VALUES
        assert k_values == sorted(k_values)
    
    def test_k_values_doubling(self):
        """K_VALUES should roughly double each step (with 1000 as endpoint)."""
        k_values = SearchVolumeAnalyzer.K_VALUES
        # Check that each value (except last) is roughly 2x previous
        for i in range(len(k_values) - 2):  # Exclude 1000 check
            assert k_values[i+1] == 2 * k_values[i]
    
    def test_k_values_range(self):
        """K_VALUES should start at 10 and end at 1000."""
        assert SearchVolumeAnalyzer.K_VALUES[0] == 10
        assert SearchVolumeAnalyzer.K_VALUES[-1] == 1000


class TestStandardizedResultFormat:
    """Test the standardized result format from search functions."""
    
    def test_result_has_required_keys(self):
        """Verify all required keys are present in standardized results."""
        from fortest.environment.search_core.real_search import _standardize_result
        
        result = _standardize_result(
            results_before=[{"url": "http://a.com"}],
            results_after=[{"url": "http://a.com"}],
            requested_k=10
        )
        
        required_keys = [
            "results_before_filter",
            "results_after_filter",
            "requested_k",
            "returned_before_filter",
            "returned_after_filter",
            "links_before_filter",
            "links_after_filter",
        ]
        
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
    
    def test_result_counts_correct(self):
        """Verify counts are calculated correctly."""
        from fortest.environment.search_core.real_search import _standardize_result
        
        before = [{"url": f"http://{i}.com"} for i in range(5)]
        after = [{"url": f"http://{i}.com"} for i in range(3)]
        
        result = _standardize_result(
            results_before=before,
            results_after=after,
            requested_k=10
        )
        
        assert result["returned_before_filter"] == 5
        assert result["returned_after_filter"] == 3
        assert result["requested_k"] == 10
        assert len(result["links_before_filter"]) == 5
        assert len(result["links_after_filter"]) == 3


class TestLinkExtraction:
    """Test link extraction from various result formats."""
    
    def test_extract_url_key(self):
        """Extract from 'url' key."""
        from fortest.environment.search_core.real_search import _extract_links
        
        results = [{"url": "http://a.com"}, {"url": "http://b.com"}]
        links = _extract_links(results, "url")
        assert links == ["http://a.com", "http://b.com"]
    
    def test_extract_link_key(self):
        """Extract from 'link' key (fallback)."""
        from fortest.environment.search_core.real_search import _extract_links
        
        results = [{"link": "http://a.com"}, {"link": "http://b.com"}]
        links = _extract_links(results, "link")
        assert links == ["http://a.com", "http://b.com"]
    
    def test_extract_href_key(self):
        """Extract from 'href' key (fallback)."""
        from fortest.environment.search_core.real_search import _extract_links
        
        results = [{"href": "http://a.com"}]
        links = _extract_links(results, "href")
        assert links == ["http://a.com"]
    
    def test_extract_handles_missing(self):
        """Handle results without URL field."""
        from fortest.environment.search_core.real_search import _extract_links
        
        results = [{"title": "No URL"}, {"url": "http://a.com"}]
        links = _extract_links(results, "url")
        assert links == ["http://a.com"]
