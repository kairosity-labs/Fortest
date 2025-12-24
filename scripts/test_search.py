import asyncio
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fortest.environment.search_core.base import SearchCore
# Ensure real_search is imported so functions register
import fortest.environment.search_core.real_search
import fortest.environment.search_core.mock_search

async def test_all_apis(query: str, testing_time: str):
    load_dotenv()
    core = SearchCore()
    
    available = core.list_available_functions()
    print(f"Available search functions: {available}")
    
    for func in available:
        if func.startswith("mock_"): 
            print(f"\n--- Testing MOCK function: {func} ---")
        else:
            print(f"\n--- Testing REAL function: {func} ---")
            
        try:
            results = await core.execute(func, query, testing_time)
            # Print a summary of results
            if isinstance(results, dict) and "error" in results:
                print(f"Result: ERROR - {results['error']}")
            elif isinstance(results, list) and results and "error" in results[0]:
                print(f"Result: ERROR - {results[0]['error']}")
            else:
                count = len(results) if isinstance(results, list) else 1
                print(f"Result: SUCCESS - Found {count} results")
                # Print the first result as JSON to see the structure
                if isinstance(results, list) and results:
                    print(f"Structure of first result:\n{json.dumps(results[0], indent=2)}")
                elif isinstance(results, dict):
                    # For dict responses (like SearchApi or Perplexity)
                    print(f"Structure of response:\n{json.dumps(results, indent=2)[:1000]}...")
        except Exception as e:
            print(f"Result: FAILED with exception: {str(e)}")

if __name__ == "__main__":
    q = "OpenAI"
    t = "2025-01-01T00:00:00Z"
    
    print(f"Starting search test for query: '{q}' before {t}")
    asyncio.run(test_all_apis(q, t))
    print("\nNote: Real API tests will fail until valid keys are added to .env")
