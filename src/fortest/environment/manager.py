import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from fortest.loader.loader import ProblemLoader
from fortest.environment.search_core.base import SearchCore
from fortest.metrics.metrics import brier_score, accuracy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EnvironmentManager:
    def __init__(self, loader_strategy: str = "load_all", eval_strategy: str = "recent", **loader_kwargs):
        self.loader = ProblemLoader()
        self.search_core = SearchCore()
        self.eval_strategy = eval_strategy # "recent" or "best"
        
        # Load problems
        self.problems = self.loader.load(loader_strategy, **loader_kwargs)
        
        # submissions[problem_id] = [ {prediction, timestamp} ]
        self.submissions: Dict[str, List[Dict]] = {pid: [] for pid in self.problems}
        self.logs: List[str] = []

    def log(self, message: str):
        self.logs.append(f"{datetime.now().isoformat()} - {message}")
        logging.info(message)

    def get_problems(self) -> Dict[str, Any]:
        """Returns problems without resolution info."""
        anonymized = {}
        for pid, p in self.problems.items():
            copy = p.copy()
            copy.pop("resolved_flag", None)
            copy.pop("resolution_status", None)
            anonymized[pid] = copy
        return anonymized

    def get_available_search_functions(self) -> List[str]:
        """Returns available search/data functions."""
        return self.search_core.list_available_functions()

    async def search(self, function_name: str, problem_id: str, query: str) -> Any:
        """Runs a search function with testing_time injection."""
        if problem_id not in self.problems:
            raise ValueError(f"Problem ID {problem_id} not found.")
        
        testing_time = self.problems[problem_id]["time_testing"]
        self.log(f"Searching {function_name} for {problem_id} (Testing Time: {testing_time}): {query}")
        
        return await self.search_core.execute(function_name, query, testing_time)

    def submit_prediction(self, problem_id: str, prediction: float):
        """Adds a prediction for a problem."""
        if problem_id not in self.problems:
            raise ValueError(f"Problem ID {problem_id} not found.")
        
        if not (0.0 <= prediction <= 1.0):
            raise ValueError("Prediction must be between 0.0 and 1.0.")

        submission = {
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.submissions[problem_id]:
            self.log(f"WARNING: Multiple submissions detected for {problem_id}")
            
        self.submissions[problem_id].append(submission)
        self.log(f"Submission received for {problem_id}: {prediction}")

    def _get_final_prediction(self, problem_id: str, actual_outcome: int) -> Optional[float]:
        """Selects prediction based on evaluation strategy."""
        subs = self.submissions[problem_id]
        if not subs:
            return None
        
        if self.eval_strategy == "recent":
            return subs[-1]["prediction"]
        elif self.eval_strategy == "best":
            # Best is defined as the one closest to actual outcome
            return min(subs, key=lambda x: (x["prediction"] - actual_outcome)**2)["prediction"]
        
        return subs[-1]["prediction"]

    def compute_metrics(self) -> Dict[str, float]:
        """Computes metrics for all resolved problems that have submissions."""
        predictions = []
        outcomes = []
        
        for pid, p in self.problems.items():
            if not p.get("resolved_flag"):
                continue
                
            actual = p.get("resolution_status")
            if actual is None:
                continue
            
            pred = self._get_final_prediction(pid, actual)
            if pred is not None:
                predictions.append(pred)
                outcomes.append(actual)

        if not predictions:
            return {"brier_score": 0.0, "accuracy": 0.0, "count": 0}

        return {
            "brier_score": brier_score(predictions, outcomes),
            "accuracy": accuracy(predictions, outcomes),
            "count": len(predictions)
        }

    def report(self):
        """Final report of the benchmarking run."""
        metrics = self.compute_metrics()
        self.log("--- FINAL BENCHMARK REPORT ---")
        self.log(f"Problems processed: {len(self.problems)}")
        self.log(f"Submissions received: {sum(len(s) for s in self.submissions.values())}")
        self.log(f"Metrics (on {metrics['count']} resolved problems):")
        self.log(f"  Brier Score: {metrics['brier_score']:.4f}")
        self.log(f"  Accuracy: {metrics['accuracy']:.4f}")
        return metrics
