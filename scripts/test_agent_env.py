import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fortest.environment.manager import EnvironmentManager
# Ensure real_search and mock_search are registered
import fortest.environment.search_core.real_search
import fortest.environment.search_core.mock_search

async def test_agent_flow():
    load_dotenv()
    
    # Initialize EnvironmentManager with the default "load_all" strategy
    # This will load problems from P001 and P002
    env = EnvironmentManager(loader_strategy="load_all")
    
    # Get anonymized problems
    problems = env.get_problems()
    print(f"Loaded {len(problems)} anonymized problems.")
    
    # List available search functions
    search_funcs = env.get_available_search_functions()
    print(f"Available search functions in environment: {search_funcs}")
    
    # Select a problem (P001 has testing_time 2024-01-01T00:00:00Z)
    problem_id = "P001"
    query = "SpaceX Starship progress 2023"
    
    print(f"\n--- Simulating Agent Search for {problem_id} using 'perplexity_search' ---")
    try:
        # Perplexity
        pplx_results = await env.search("perplexity_search", problem_id, query)
        print("Perplexity Search successful.")
        # print(json.dumps(pplx_results, indent=2)[:500] + "...")
    except Exception as e:
        print(f"Perplexity Search failed: {e}")

    print(f"\n--- Simulating Agent Search for {problem_id} using 'google_search_searchapi' ---")
    try:
        # Google
        google_results = await env.search("google_search_searchapi", problem_id, query)
        print("Google Search successful.")
        # print(json.dumps(google_results, indent=2)[:500] + "...")
    except Exception as e:
        print(f"Google Search failed: {e}")

    # Submit a dummy prediction
    print(f"\n--- Submitting Prediction for {problem_id} ---")
    env.submit_prediction(problem_id, 0.75)
    
    # Compute metrics (only for resolved problems, P002 is resolved)
    print(f"\n--- Simulating Completion and Reporting ---")
    env.submit_prediction("P002", 0.1) # Correct-ish for P002
    report = env.report()
    print(f"Final Report: {report}")

if __name__ == "__main__":
    asyncio.run(test_agent_flow())
