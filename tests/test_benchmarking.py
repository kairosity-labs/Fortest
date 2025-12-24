import pytest
import asyncio
from fortest.loader.loader import ProblemLoader
from fortest.environment.manager import EnvironmentManager
from fortest.metrics.metrics import brier_score, accuracy

def test_loader_registration():
    loader = ProblemLoader()
    available = loader.list_available_loaders()
    assert "load_all" in available
    assert "load_random" in available
    assert "load_by_source" in available

def test_loader_load_all():
    loader = ProblemLoader()
    problems = loader.load("load_all")
    assert len(problems) >= 2
    assert "P001" in problems
    assert "time_testing" in problems["P001"]
    assert "time_now" in problems["P001"]

def test_environment_anonymization():
    env = EnvironmentManager(loader_strategy="load_all")
    problems = env.get_problems()
    for p in problems.values():
        assert "resolved_flag" not in p
        assert "resolution_status" not in p

@pytest.mark.asyncio
async def test_search_injection():
    env = EnvironmentManager(loader_strategy="load_all")
    results = await env.search("mock_google", "P001", "SpaceX Mars")
    assert "SpaceX Mars" in results[0]["title"]
    # Verify testing_time was injected (from P001 which is 2024-01-01T00:00:00Z)
    assert results[0]["snippet"].strip().endswith("2024-01-01T00:00:00Z")

def test_submission_and_metrics_recent():
    env = EnvironmentManager(loader_strategy="load_all", eval_strategy="recent")
    # P002 is resolved with status 0
    env.submit_prediction("P002", 0.8) # Wrong prediction
    env.submit_prediction("P002", 0.2) # Corrected prediction (more recent)
    
    metrics = env.compute_metrics()
    # Only P002 has outcome and submission
    # Brier score: (0.2 - 0)^2 = 0.04
    assert metrics["brier_score"] == pytest.approx(0.04)
    assert metrics["accuracy"] == 1.0 # 0.2 < 0.5 threshold

def test_submission_and_metrics_best():
    env = EnvironmentManager(loader_strategy="load_all", eval_strategy="best")
    # P002 status 0
    env.submit_prediction("P002", 0.1) # Best
    env.submit_prediction("P002", 0.9) # Worse
    
    metrics = env.compute_metrics()
    # Brier score: (0.1 - 0)^2 = 0.01
    assert metrics["brier_score"] == pytest.approx(0.01)

def test_metrics_calculation():
    preds = [0.8, 0.2, 0.5]
    outcomes = [1, 0, 1]
    # Brier: ((0.8-1)^2 + (0.2-0)^2 + (0.5-1)^2) / 3 = (0.04 + 0.04 + 0.25) / 3 = 0.33 / 3 = 0.11
    assert brier_score(preds, outcomes) == pytest.approx(0.11)
    # Accuracy: (1 + 1 + 1) / 3 = 1.0 (threshold 0.5, 0.5 is predicted as 1)
    assert accuracy(preds, outcomes) == 1.0
