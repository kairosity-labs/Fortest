
import asyncio
import pytest
from fortest.environment.manager import EnvironmentManager
from fortest.loader.loader import ProblemLoader
from fortest.scripts.setup_datasets import ensure_forecastbench_data

# Ensure data is present before running tests
ensure_forecastbench_data()

@pytest.mark.asyncio
async def test_forecastbench_end_to_end():
    """
    End-to-end test for ForecastBench integration.
    Simulates three agents:
    1. Perfect Agent (Brier Score -> 0)
    2. Worst Agent (Brier Score -> high)
    3. Uncertain Agent (50% prob)
    """
    
    LIMIT = 5
    
    # 1. Initialize Manager with new strategy
    print("\n[INFO] Initializing Environment with forecastbench loader...")
    manager = EnvironmentManager(loader_strategy="forecastbench", dataset_name="2024-07-21-llm", limit=LIMIT)
    
    problems = manager.get_problems()
    print(f"[INFO] Loaded {len(problems)} problems.")
    
    assert len(problems) > 0, "No problems loaded!"
    if LIMIT:
        assert len(problems) <= LIMIT
        
    print("[INFO] Showing what info agent gets for first problem:")
    first_pid = list(problems.keys())[0]
    first_pid = list(problems.keys())[0]
    print(problems[first_pid])
    
    # --- Capability Discovery ---
    print("\n--- Capability Discovery ---")
    search_funcs = manager.get_available_search_functions()
    loader_strategies = manager.get_available_loader_strategies()
    avail_metrics = manager.get_available_metrics()
    
    print(f"Available Search: {search_funcs}")
    print(f"Available Loaders: {loader_strategies}")
    print(f"Available Metrics: {avail_metrics}")
    
    assert "mock_google" in search_funcs
    assert "forecastbench" in loader_strategies
    assert "brier_score" in avail_metrics

    # Simulating Agent Actions
    
    # --- SCENARIO 1: Perfect Agent ---
    print("\n--- SCENARIO 1: Perfect Agent ---")
    # Reset submissions for this test logic (hacky for test purpose, usually persistent)
    manager.submissions = {pid: [] for pid in manager.problems}
    
    for pid in problems:
        # Agent "searches"
        await manager.search("mock_google", pid, "What is the answer?") # Using mock_google which is likely available 
        # Actually, let's just create a log entry as if search happened since we might not have search keys configured.
        manager.log(f"Agent searching info for {pid}...")
        
        # Agent "knows" the answer (cheating by looking at manager's secret resolved data)
        actual = manager.problems[pid].get("resolution_status")
        
        if actual is None:
            print(f"[WARN] Problem {pid} has no resolution, skipping submission.")
            continue
            
        prediction = float(actual) # 1.0 or 0.0
        manager.submit_prediction(pid, prediction)
        
    metrics = manager.report()
    print(f"[RESULT] Perfect Agent Brier Score: {metrics['brier_score']}")
    # Assert Brier Score is very low (allow some float error)
    if metrics['count'] > 0:
        assert metrics['brier_score'] < 0.01

    # --- SCENARIO 2: Worst Agent ---
    print("\n--- SCENARIO 2: Worst Agent ---")
    manager.submissions = {pid: [] for pid in manager.problems} # Reset
    
    for pid in problems:
        actual = manager.problems[pid].get("resolution_status")
        if actual is None: continue
            
        # Predict opposite
        prediction = 1.0 - float(actual)
        manager.submit_prediction(pid, prediction)
        
    metrics = manager.report()
    print(f"[RESULT] Worst Agent Brier Score: {metrics['brier_score']}")
    if metrics['count'] > 0:
        assert metrics['brier_score'] > 0.9 # (1-0)^2 = 1

    # --- SCENARIO 3: Uncertain Agent ---
    print("\n--- SCENARIO 3: Uncertain Agent ---")
    manager.submissions = {pid: [] for pid in manager.problems} # Reset
    
    for pid in problems:
        actual = manager.problems[pid].get("resolution_status")
        if actual is None: continue
            
        prediction = 0.5
        manager.submit_prediction(pid, prediction)
        
    metrics = manager.report()
    print(f"[RESULT] Uncertain Agent Brier Score: {metrics['brier_score']}")
    if metrics['count'] > 0:
        # (0.5 - 0)^2 = 0.25, (0.5 - 1)^2 = 0.25
        assert 0.24 < metrics['brier_score'] < 0.26
        
    # --- Metric Selection Test ---
    print("\n--- Metric Selection Test ---")
    # Using Uncertain Agent predictions (already in state)
    # Select only Brier Score
    selected_metrics = manager.report(metrics=["brier_score"])
    print(f"[RESULT] Selected Metrics: {selected_metrics.keys()}")
    
    assert "brier_score" in selected_metrics
    assert "accuracy" not in selected_metrics
    assert selected_metrics["brier_score"] == metrics["brier_score"]

if __name__ == "__main__":
    # Allow running as script
    asyncio.run(test_forecastbench_end_to_end())
