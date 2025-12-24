import os
import requests
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fortest.environment.search_core.base import SearchCore
from ddgs import DDGS

# Load environment variables
load_dotenv()

@SearchCore.register("perplexity_search")
async def perplexity_search(query: str, testing_time: str) -> Dict[str, Any]:
    """
    Perplexity Search API with search_before_date filter.
    testing_time should be ISO format, we convert to %m/%d/%Y.
    """
    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        return {"error": "PPLX_API_KEY not set"}

    try:
        dt = datetime.fromisoformat(testing_time.replace("Z", "+00:00"))
        before_date = dt.strftime("%m/%d/%Y")
    except ValueError:
        before_date = testing_time # Fallback

    url = "https://api.perplexity.ai/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "max_results": 10,
        "search_before_date": before_date,
    }
    
    # Using requests here as per user snippet. In a production async environment, 
    # we might prefer httpx or similar, but keeping to user's reference.
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()

@SearchCore.register("parallel_search")
async def parallel_search(query: str, testing_time: str) -> List[Dict[str, Any]]:
    """
    Parallel AI search with post-filtering for "before" testing_time.
    """
    from parallel import Parallel # Local import to handle potential missing dependency if not used
    
    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key:
        return [{"error": "PARALLEL_API_KEY not set"}]

    client = Parallel(api_key=api_key)
    
    # Requesting results (Parallel doesn't have native "before" filter)
    resp = client.beta.search(objective=query, max_results=20)
    
    try:
        cutoff = datetime.fromisoformat(testing_time.replace("Z", "+00:00")).date()
    except ValueError:
        return [{"error": f"Invalid testing_time format: {testing_time}"}]

    filtered = []
    for r in resp.results:
        pub_date_str = getattr(r, "publish_date", None)
        if pub_date_str:
            try:
                pub_date = date.fromisoformat(pub_date_str[:10])
                if pub_date < cutoff:
                    filtered.append({
                        "title": getattr(r, "title", "No Title"),
                        "url": getattr(r, "url", ""),
                        "snippet": getattr(r, "snippet", ""),
                        "publish_date": pub_date_str
                    })
            except Exception:
                continue
                
    return filtered

@SearchCore.register("google_news_searchapi")
async def google_news_searchapi(query: str, testing_time: str) -> Dict[str, Any]:
    """
    Google News search via SearchApi.io with custom date range.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"error": "SERPAPI_KEY not set"}

    try:
        dt = datetime.fromisoformat(testing_time.replace("Z", "+00:00"))
        before_date = dt.strftime("%m/%d/%Y")
    except ValueError:
        before_date = "01/01/2025" 

    params = {
        "engine": "google_news",
        "q": query,
        "api_key": api_key,
        "time_period_max": before_date,
    }
    
    r = requests.get("https://www.searchapi.io/api/v1/search", params=params, timeout=60)
    r.raise_for_status()
    return r.json()

@SearchCore.register("ddg_news_search")
async def ddg_news_search(query: str, testing_time: str) -> List[Dict[str, Any]]:
    """
    DuckDuckGo news search with local post-filtering.
    """
    try:
        cutoff = datetime.fromisoformat(testing_time.replace("Z", "+00:00")).date()
    except ValueError:
        return [{"error": f"Invalid testing_time format: {testing_time}"}]

    out = []
    with DDGS() as ddgs:
        # Using timelimit="y" to get semi-recent/old results if needed
        for item in ddgs.news(query, timelimit="y", max_results=50):
            d = item.get("date") or item.get("datetime") or item.get("published")
            if not d:
                continue
            try:
                pub = date.fromisoformat(d[:10])
                if pub < cutoff:
                    out.append(item)
            except Exception:
                continue

    return out

@SearchCore.register("google_search_searchapi")
async def google_search_searchapi(query: str, testing_time: str) -> Dict[str, Any]:
    """
    General Google Web search via SearchApi.io with custom date range.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"error": "SERPAPI_KEY not set"}

    try:
        dt = datetime.fromisoformat(testing_time.replace("Z", "+00:00"))
        before_date = dt.strftime("%m/%d/%Y")
    except ValueError:
        before_date = None

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }
    if before_date:
        params["time_period_max"] = before_date
    
    r = requests.get("https://www.searchapi.io/api/v1/search", params=params, timeout=60)
    r.raise_for_status()
    return r.json()

@SearchCore.register("ddg_text_search")
async def ddg_text_search(query: str, testing_time: str) -> List[Dict[str, Any]]:
    """
    DuckDuckGo general web search. 
    Note: Absolute date filtering is not natively supported in DDG text search.
    """
    try:
        cutoff = datetime.fromisoformat(testing_time.replace("Z", "+00:00")).date()
    except ValueError:
        return [{"error": f"Invalid testing_time format: {testing_time}"}]

    out = []
    with DDGS() as ddgs:
        # Using timelimit="y" to attempt to get older results
        for item in ddgs.text(query, timelimit="y", max_results=20):
            d = item.get("date")
            if d:
                try:
                    pub = date.fromisoformat(d[:10])
                    if pub < cutoff:
                        out.append(item)
                except Exception:
                    out.append(item)
            else:
                item["date_warning"] = "No date available for filtering"
                out.append(item)

    return out
