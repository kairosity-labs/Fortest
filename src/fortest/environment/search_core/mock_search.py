from fortest.environment.search_core.base import SearchCore

@SearchCore.register("mock_google")
async def mock_google(query: str, testing_time: str):
    """A mock google search that respects testing_time."""
    return [
        {"title": f"Result for {query}", "snippet": f"This info was available before {testing_time}", "date": testing_time}
    ]

@SearchCore.register("mock_perplexity")
async def mock_perplexity(query: str, testing_time: str):
    """A mock perplexity search."""
    return {
        "answer": f"Simulated answer for '{query}' restricted to data before {testing_time}",
        "sources": ["source1", "source2"]
    }
