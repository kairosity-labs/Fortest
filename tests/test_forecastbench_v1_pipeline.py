"""
Pipeline and Metrics Tests for ForecastBench v1

Round 3: Pipeline Level Testing
- Simulated agents (random, always-yes, always-no, calibrated)
- End-to-end pipeline testing
- Grouped metrics (by source x horizon)
- Metric validation
"""

import pytest
import random
from collections import defaultdict
from typing import Dict, List, Callable, Any

from fortest.loader.loader import ProblemLoader
from fortest.loader.custom_loaders.forecastbench_v1 import (
    get_horizon_summary,
    get_sources_list,
    get_horizons_list,
    ALL_SOURCES,
)
from fortest.metrics.metrics import brier_score, accuracy


# ============================================================================
# SIMULATED AGENTS
# ============================================================================

class SimulatedAgent:
    """Base class for simulated agents."""
    
    def __init__(self, name: str):
        self.name = name
    
    def predict(self, problem: Dict) -> float:
        """Return probability prediction for a problem."""
        raise NotImplementedError


class RandomAgent(SimulatedAgent):
    """Agent that predicts random probabilities."""
    
    def __init__(self, seed: int = 42):
        super().__init__("random_agent")
        self.rng = random.Random(seed)
    
    def predict(self, problem: Dict) -> float:
        return self.rng.random()


class AlwaysYesAgent(SimulatedAgent):
    """Agent that always predicts 1.0 (yes)."""
    
    def __init__(self):
        super().__init__("always_yes_agent")
    
    def predict(self, problem: Dict) -> float:
        return 1.0


class AlwaysNoAgent(SimulatedAgent):
    """Agent that always predicts 0.0 (no)."""
    
    def __init__(self):
        super().__init__("always_no_agent")
    
    def predict(self, problem: Dict) -> float:
        return 0.0


class BaseRateAgent(SimulatedAgent):
    """Agent that predicts based on training set base rate."""
    
    def __init__(self, base_rate: float = 0.34):  # ~34% yes in dataset
        super().__init__("base_rate_agent")
        self.base_rate = base_rate
    
    def predict(self, problem: Dict) -> float:
        return self.base_rate


class CalibratedRandomAgent(SimulatedAgent):
    """Agent that predicts random but calibrated around base rate."""
    
    def __init__(self, base_rate: float = 0.34, spread: float = 0.2, seed: int = 42):
        super().__init__("calibrated_random_agent")
        self.base_rate = base_rate
        self.spread = spread
        self.rng = random.Random(seed)
    
    def predict(self, problem: Dict) -> float:
        prediction = self.base_rate + self.rng.uniform(-self.spread, self.spread)
        return max(0.0, min(1.0, prediction))


# ============================================================================
# PIPELINE RUNNER
# ============================================================================

class ForecastPipeline:
    """Pipeline for running forecasting experiments."""
    
    def __init__(self, agent: SimulatedAgent):
        self.agent = agent
        self.results = []
    
    def run(self, problems: Dict[str, Dict]) -> Dict[str, Any]:
        """Run agent on all problems and collect results."""
        self.results = []
        
        predictions = []
        outcomes = []
        
        for pid, problem in problems.items():
            prediction = self.agent.predict(problem)
            outcome = problem['resolution_status']
            
            self.results.append({
                'problem_id': pid,
                'prediction': prediction,
                'outcome': outcome,
                'source': problem['metadata']['source'],
                'horizon': problem['metadata']['horizon'],
            })
            
            predictions.append(prediction)
            outcomes.append(int(outcome))
        
        return {
            'agent': self.agent.name,
            'total_problems': len(problems),
            'brier_score': brier_score(predictions, outcomes),
            'accuracy': accuracy(predictions, outcomes),
            'predictions': predictions,
            'outcomes': outcomes,
        }
    
    def get_grouped_metrics(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Get metrics grouped by source x horizon."""
        grouped = defaultdict(lambda: defaultdict(lambda: {'predictions': [], 'outcomes': []}))
        
        for r in self.results:
            grouped[r['source']][r['horizon']]['predictions'].append(r['prediction'])
            grouped[r['source']][r['horizon']]['outcomes'].append(int(r['outcome']))
        
        metrics = defaultdict(dict)
        
        for source, horizons in grouped.items():
            for horizon, data in horizons.items():
                if data['predictions']:
                    metrics[source][horizon] = {
                        'brier_score': brier_score(data['predictions'], data['outcomes']),
                        'accuracy': accuracy(data['predictions'], data['outcomes']),
                        'count': len(data['predictions']),
                    }
        
        return dict(metrics)


# ============================================================================
# ROUND 3: PIPELINE TESTS
# ============================================================================

class TestSimulatedAgents:
    """Tests for simulated agents."""
    
    def test_random_agent_returns_valid_probs(self):
        """Random agent should return probabilities in [0, 1]."""
        agent = RandomAgent(seed=42)
        problem = {'question': 'test'}
        
        for _ in range(100):
            pred = agent.predict(problem)
            assert 0.0 <= pred <= 1.0
    
    def test_always_yes_returns_one(self):
        """Always-yes agent should return 1.0."""
        agent = AlwaysYesAgent()
        assert agent.predict({}) == 1.0
    
    def test_always_no_returns_zero(self):
        """Always-no agent should return 0.0."""
        agent = AlwaysNoAgent()
        assert agent.predict({}) == 0.0
    
    def test_base_rate_agent_consistent(self):
        """Base rate agent should always return same value."""
        agent = BaseRateAgent(base_rate=0.5)
        for _ in range(10):
            assert agent.predict({}) == 0.5
    
    def test_calibrated_random_bounded(self):
        """Calibrated random agent should stay bounded."""
        agent = CalibratedRandomAgent(base_rate=0.5, spread=0.3, seed=42)
        for _ in range(100):
            pred = agent.predict({})
            assert 0.0 <= pred <= 1.0


class TestForecastPipeline:
    """Tests for the forecast pipeline."""
    
    def test_pipeline_runs_without_error(self):
        """Pipeline should run without errors."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=50, seed=42)
        
        agent = RandomAgent(seed=100)
        pipeline = ForecastPipeline(agent)
        result = pipeline.run(problems)
        
        assert result is not None
        assert 'brier_score' in result
        assert 'accuracy' in result
    
    def test_pipeline_returns_correct_count(self):
        """Pipeline should process all problems."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1', max_quest=30, seed=42)
        
        pipeline = ForecastPipeline(RandomAgent(seed=42))
        result = pipeline.run(problems)
        
        assert result['total_problems'] == len(problems)
    
    def test_always_yes_metrics(self):
        """Always-yes agent should have predictable metrics."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=100, seed=42)
        
        pipeline = ForecastPipeline(AlwaysYesAgent())
        result = pipeline.run(problems)
        
        # Count actual yes outcomes
        yes_count = sum(1 for p in problems.values() if p['resolution_status'] == 1.0)
        expected_accuracy = yes_count / len(problems)
        
        assert abs(result['accuracy'] - expected_accuracy) < 0.01
    
    def test_always_no_metrics(self):
        """Always-no agent should have predictable metrics."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=100, seed=42)
        
        pipeline = ForecastPipeline(AlwaysNoAgent())
        result = pipeline.run(problems)
        
        # Count actual no outcomes
        no_count = sum(1 for p in problems.values() if p['resolution_status'] == 0.0)
        expected_accuracy = no_count / len(problems)
        
        assert abs(result['accuracy'] - expected_accuracy) < 0.01


class TestGroupedMetrics:
    """Tests for grouped metrics (by source x horizon)."""
    
    def test_grouped_metrics_structure(self):
        """Grouped metrics should have correct structure."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=100, seed=42)
        
        pipeline = ForecastPipeline(RandomAgent(seed=42))
        pipeline.run(problems)
        grouped = pipeline.get_grouped_metrics()
        
        assert isinstance(grouped, dict)
        
        for source, horizons in grouped.items():
            assert source in ALL_SOURCES
            for horizon, metrics in horizons.items():
                assert horizon in get_horizons_list()
                assert 'brier_score' in metrics
                assert 'accuracy' in metrics
                assert 'count' in metrics
    
    def test_grouped_metrics_sum_to_total(self):
        """Sum of grouped counts should equal total problems."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=100, seed=42)
        
        pipeline = ForecastPipeline(RandomAgent(seed=42))
        pipeline.run(problems)
        grouped = pipeline.get_grouped_metrics()
        
        total_count = sum(
            m['count'] 
            for horizons in grouped.values() 
            for m in horizons.values()
        )
        
        assert total_count == len(problems)
    
    def test_grouped_metrics_per_source(self):
        """Test grouped metrics for each source."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        pipeline = ForecastPipeline(BaseRateAgent(base_rate=0.34))
        pipeline.run(problems)
        grouped = pipeline.get_grouped_metrics()
        
        print("\nGrouped Metrics by Source x Horizon:")
        print("-" * 80)
        
        horizons = get_horizons_list()
        header = f"{'Source':<12} | " + " | ".join(f"{h[:8]:<8}" for h in horizons)
        print(header)
        print("-" * 80)
        
        for source in sorted(grouped.keys()):
            row = f"{source:<12} | "
            for h in horizons:
                if h in grouped[source]:
                    bs = grouped[source][h]['brier_score']
                    row += f"{bs:.3f}    | "
                else:
                    row += "N/A      | "
            print(row)


class TestMetricValidation:
    """Tests for metric calculation validity."""
    
    def test_brier_score_range(self):
        """Brier score should be in [0, 1]."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1', max_quest=100, seed=42)
        
        for AgentClass in [RandomAgent, AlwaysYesAgent, AlwaysNoAgent, BaseRateAgent]:
            agent = AgentClass() if AgentClass in [AlwaysYesAgent, AlwaysNoAgent] else AgentClass(42) if AgentClass == RandomAgent else AgentClass()
            pipeline = ForecastPipeline(agent)
            result = pipeline.run(problems)
            
            assert 0.0 <= result['brier_score'] <= 1.0, f"{agent.name} has invalid Brier: {result['brier_score']}"
    
    def test_accuracy_range(self):
        """Accuracy should be in [0, 1]."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1', max_quest=100, seed=42)
        
        for AgentClass in [RandomAgent, AlwaysYesAgent, AlwaysNoAgent]:
            agent = AgentClass() if AgentClass in [AlwaysYesAgent, AlwaysNoAgent] else AgentClass(42)
            pipeline = ForecastPipeline(agent)
            result = pipeline.run(problems)
            
            assert 0.0 <= result['accuracy'] <= 1.0, f"{agent.name} has invalid accuracy: {result['accuracy']}"
    
    def test_random_beats_constant_on_brier(self):
        """Calibrated agent should often beat constant agents on Brier score."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=200, seed=42)
        
        # Calculate actual base rate
        yes_count = sum(1 for p in problems.values() if p['resolution_status'] == 1.0)
        base_rate = yes_count / len(problems)
        
        base_agent = BaseRateAgent(base_rate=base_rate)
        yes_agent = AlwaysYesAgent()
        no_agent = AlwaysNoAgent()
        
        base_result = ForecastPipeline(base_agent).run(problems)
        yes_result = ForecastPipeline(yes_agent).run(problems)
        no_result = ForecastPipeline(no_agent).run(problems)
        
        # Base rate agent should beat extreme agents on Brier
        assert base_result['brier_score'] < yes_result['brier_score'], "Base rate should beat always-yes"
        assert base_result['brier_score'] < no_result['brier_score'], "Base rate should beat always-no"


class TestEndToEndPipeline:
    """End-to-end integration tests."""
    
    def test_full_pipeline_multiple_agents(self):
        """Run full pipeline with multiple agents and compare."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1_extensive', max_quest=150, seed=42)
        
        agents = [
            RandomAgent(seed=42),
            AlwaysYesAgent(),
            AlwaysNoAgent(),
            BaseRateAgent(base_rate=0.34),
            CalibratedRandomAgent(base_rate=0.34, spread=0.2, seed=42),
        ]
        
        results = []
        for agent in agents:
            pipeline = ForecastPipeline(agent)
            result = pipeline.run(problems)
            results.append(result)
            print(f"{agent.name}: Brier={result['brier_score']:.4f}, Acc={result['accuracy']:.2%}")
        
        # All results should be valid
        for r in results:
            assert r['total_problems'] == len(problems)
            assert 0 <= r['brier_score'] <= 1
            assert 0 <= r['accuracy'] <= 1
    
    def test_reproducibility_across_runs(self):
        """Same agent with same seed should produce identical results across runs."""
        loader = ProblemLoader()
        problems = loader.load('forecastbench_v1', max_quest=50, seed=42)
        
        results = []
        for _ in range(3):
            agent = RandomAgent(seed=999)
            pipeline = ForecastPipeline(agent)
            result = pipeline.run(problems)
            results.append(result['brier_score'])
        
        assert all(r == results[0] for r in results), "Results should be identical"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
