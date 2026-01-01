"""
Search functions for pastcasting analysis.

Simplified to use only:
- Perplexity Search API (with max_results and search_before_date)
- AskNews API (with timestamp-based date filtering)
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from fortest.environment.search_core.base import SearchCore

# Load environment variables
load_dotenv()


def _extract_links(results: List[Dict], url_key: str = "url") -> List[str]:
    """Extract URLs from a list of result dictionaries."""
    links = []
    for r in results:
        url = r.get(url_key) or r.get("link") or r.get("href") or r.get("article_url")
        if url:
            links.append(url)
    return links


def _standardize_result(
    results_before: List[Dict],
    results_after: List[Dict],
    requested_k: int,
    url_key: str = "url",
    date_parse_failures: int = 0,
    no_date_count: int = 0
) -> Dict[str, Any]:
    """Create standardized result format for analysis."""
    links_before = _extract_links(results_before, url_key)
    links_after = _extract_links(results_after, url_key)
    return {
        "results_before_filter": results_before,
        "results_after_filter": results_after,
        "requested_k": requested_k,
        "returned_before_filter": len(results_before),
        "returned_after_filter": len(results_after),
        "links_before_filter": links_before,
        "links_after_filter": links_after,
        "date_parse_failures": date_parse_failures,
        "no_date_count": no_date_count,
    }


def _error_result(error_msg: str, requested_k: int) -> Dict[str, Any]:
    """Create standardized error result format."""
    return {
        "error": error_msg,
        "requested_k": requested_k,
        "returned_before_filter": 0,
        "returned_after_filter": 0,
        "links_before_filter": [],
        "links_after_filter": [],
        "results_before_filter": [],
        "results_after_filter": [],
        "date_parse_failures": 0,
        "no_date_count": 0,
    }


# =============================================================================
# PERPLEXITY SEARCH API
# =============================================================================
@SearchCore.register("perplexity_search")
async def perplexity_search(query: str, testing_time: str, k: int = 10) -> Dict[str, Any]:
    """
    Perplexity Search API with max_results (k) and search_before_date filter.
    
    Docs: https://docs.perplexity.ai/guides/search-date-time-filters
    
    Args:
        query: Search query
        testing_time: ISO format date string (results before this date)
        k: Number of results to request
        
    Returns:
        Standardized result dict
    """
    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        return _error_result("PPLX_API_KEY not set", k)

    try:
        dt = datetime.fromisoformat(testing_time.replace("Z", "+00:00"))
        before_date = dt.strftime("%m/%d/%Y")  # MM/DD/YYYY format per docs
    except ValueError:
        return _error_result(f"Invalid testing_time format: {testing_time}", k)

    try:
        # Perplexity Search API endpoint
        url = "https://api.perplexity.ai/search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "max_results": k,
            "search_before_date": before_date,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Extract results from response
        results = data.get("results", []) if isinstance(data, dict) else []
        
        # Perplexity has built-in date filtering, so before == after
        return _standardize_result(results, results, k)
    except requests.RequestException as e:
        return _error_result(f"Perplexity API error: {str(e)}", k)


# =============================================================================
# ASKNEWS API (using official AsyncAskNewsSDK with historical search)
# =============================================================================
@SearchCore.register("asknews_search")
async def asknews_search(query: str, testing_time: str, k: int = 10) -> Dict[str, Any]:
    """
    AskNews API search using the official AsyncAskNewsSDK.
    
    Key improvements:
    - Uses AsyncAskNewsSDK with async context manager
    - Sets historical=True for archive access
    - Uses both start_timestamp and end_timestamp (60-day window)
    - Implements exponential backoff retry for rate limits
    
    Docs: https://docs.asknews.app/en/reference#get-/v1/news/search
    
    Args:
        query: Search query
        testing_time: ISO format date string (results before this date)
        k: Number of results to request (max 10 on free plan)
        
    Returns:
        Standardized result dict
    """
    try:
        from asknews_sdk import AsyncAskNewsSDK
    except ImportError:
        return _error_result("asknews SDK not installed. Run: uv add asknews", k)
    
    client_id = os.getenv("ASKNEWS_CLIENT_ID")
    client_secret = os.getenv("ASKNEWS_SECRET")
    
    if not client_id or not client_secret:
        return _error_result("ASKNEWS_CLIENT_ID and ASKNEWS_SECRET not set", k)

    try:
        dt = datetime.fromisoformat(testing_time.replace("Z", "+00:00"))
        end_timestamp = int(dt.timestamp())
        # 60-day lookback window for historical search
        start_timestamp = end_timestamp - (60 * 24 * 3600)
    except ValueError:
        return _error_result(f"Invalid testing_time format: {testing_time}", k)

    # Retry with exponential backoff for rate limits
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            async with AsyncAskNewsSDK(
                client_id=client_id,
                client_secret=client_secret,
                scopes={"news"},
            ) as sdk:
                # Search for historical news with proper parameters
                response = await sdk.news.search_news(
                    query=query,
                    n_articles=min(k, 10),  # Free plan caps at 10
                    historical=True,  # CRITICAL: enables archive access
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    strategy="default",
                    return_type="dicts",
                )
                
                # Extract articles from response
                articles = response.as_dicts if hasattr(response, 'as_dicts') else []
                if not articles and hasattr(response, 'articles'):
                    articles = response.articles or []
                
                # Transform to standard format
                results = []
                for article in articles:
                    if isinstance(article, dict):
                        pub_date = article.get("pub_date", "")
                        results.append({
                            "title": str(article.get("title", "") or article.get("eng_title", "")),
                            "url": str(article.get("article_url", "") or ""),
                            "snippet": article.get("summary", "") or article.get("eng_summary", ""),
                            "date": str(pub_date) if pub_date else "",
                            "source": article.get("source_id", "") or str(article.get("source", "")),
                        })
                    else:
                        # Handle object attributes (SearchResponseDictItem)
                        pub_date = getattr(article, "pub_date", "")
                        results.append({
                            "title": str(getattr(article, "title", "") or getattr(article, "eng_title", "")),
                            "url": str(getattr(article, "article_url", "") or ""),
                            "snippet": str(getattr(article, "summary", "") or getattr(article, "eng_summary", "") or ""),
                            "date": str(pub_date) if pub_date else "",
                            "source": getattr(article, "source_id", "") or str(getattr(article, "source", "")),
                        })
                
                # AskNews has built-in date filtering
                return _standardize_result(results, results, k, url_key="url")
                
        except Exception as e:
            error_str = str(e)
            # Check for rate limit error
            if "429" in error_str or "Rate Limit" in error_str:
                if attempt < max_retries - 1:
                    # Exponential backoff: 2, 4, 8 seconds
                    wait_time = 2 ** (attempt + 1)
                    import asyncio
                    await asyncio.sleep(wait_time)
                    continue
            # Non-rate-limit error or final retry
            return _error_result(f"AskNews API error: {error_str}", k)
    
    return _error_result(f"AskNews API error: Rate limit exceeded after {max_retries} retries", k)
