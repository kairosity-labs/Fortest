"""
Fortest Pipeline Demo
=====================

This script demonstrates how to:
1. Load ForecastBench questions using different strategies
2. Generate new random question sets (via seed)
3. Run a simulated agent pipeline
4. Evaluate performance with grouped metrics
"""

import asyncio
import random
import sys
from collections import defaultdict
from datetime import datetime

# Add src to path for running from root
sys.path.append('src')

from fortest.environment.manager import EnvironmentManager
from fortest.loader.custom_loaders.forecastbench_v1 import (
    get_horizon_summary, 
    get_horizons_list,
    DATA_SOURCES,
    MARKET_SOURCES
)


async def run_pipeline(
    name: str, 
    loader_strategy: str, 
    max_quest: int = 50, 
    seed: int = 42,
    **loader_kwargs
):
    print(f"\n{'='*80}")
    print(f"RUNNING PIPELINE: {name}")
    print(f"Strategy: {loader_strategy}")
    print(f"Config: max_quest={max_quest}, seed={seed}, kwargs={loader_kwargs}")
    print(f"{'='*80}")
    
    # 1. Initialize Environment with specific loader
    # This automatically loads the questions based on strategy
    env = EnvironmentManager(
        loader_strategy=loader_strategy,
        max_quest=max_quest,
        seed=seed,
        **loader_kwargs
    )
    
    problems = env.get_problems()
    print(f"\nLoaded {len(problems)} questions")
    
    # Analyze distribution
    summary = get_horizon_summary(env.problems)
    horizons = get_horizons_list()
    
    print("\nDataset Distribution:")
    print(f"{'Source':<12} | " + " | ".join(f"{h[:8]:<8}" for h in horizons))
    print("-" * 80)
    for src in sorted(summary.keys()):
        row = [str(summary[src].get(h, 0)) for h in horizons]
        print(f"{src:<12} | " + " | ".join(f"{v:<8}" for v in row))
    
    # 2. Run Simulated Agent
    # In a real scenario, this would use env.search() and an LLM
    print("\nRunning simulated agent (Random + Base Rate bias)...")
    
    predictions = {}
    
    for pid, prob in problems.items():
        # Simulate thinking...
        
        # Simple agent: predicts around 0.34 (base rate) with noise
        # Data sources (usually hard/specific) -> higher uncertainty
        src = prob['metadata']['source']
        if src in DATA_SOURCES:
            noise = 0.4  # More random
        else:
            noise = 0.2  # More structured markets
            
        base = 0.35
        pred = base + random.uniform(-noise, noise)
        pred = max(0.01, min(0.99, pred))
        
        # Submit prediction
        env.submit_prediction(pid, pred)
        predictions[pid] = pred
        
    print(f"Submissions complete. Total: {len(predictions)}")
    
    # 3. Generate Report
    print("\nGenerating Evaluation Report...")
    metrics = env.report(metrics=["brier_score", "accuracy"])
    
    return metrics


async def main():
    print("""
    ░█▀▀░█▀█░█▀▄░▀█▀░█▀▀░█▀▀░▀█▀
    ░█▀▀░█░█░█▀▄░░█░░█▀▀░▀▀█░░█░
    ░▀░░░▀▀▀░▀░▀░░▀░░▀▀▀░▀▀▀░░▀░
    Pipeline Demo & Usage Guide
    """)
    
    # Example 1: Extensive Loading (All sources balanced)
    await run_pipeline(
        name="Extensive Benchmark (All Sources)",
        loader_strategy="forecastbench_v1_extensive",
        max_quest=100,
        seed=42  # Change seed to generate new random set
    )
    
    # Example 2: Source Specific Loading (e.g., FRED only)
    await run_pipeline(
        name="Source Specific (FRED Economic Data)",
        loader_strategy="forecastbench_v1_source",
        source="fred",
        max_quest=30,
        seed=123,
        horizons=["long_term", "very_long_term"]  # Filter horizons
    )
    
    # Example 3: Filtered Loading (Market questions, short/near term)
    await run_pipeline(
        name="Short-term Market Forecasts",
        loader_strategy="forecastbench_v1",
        sources=list(MARKET_SOURCES),
        horizons=["short_term", "near_term"],
        max_quest=40,
        seed=999
    )
    
    print("\nDone! See README.md for more details.")


if __name__ == "__main__":
    asyncio.run(main())
