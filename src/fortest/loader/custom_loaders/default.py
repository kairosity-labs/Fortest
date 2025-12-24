from fortest.loader.loader import ProblemLoader, base_process_problem
from datetime import datetime
import random

@ProblemLoader.register("load_all")
def load_all(problems, time_testing=None, time_now=None):
    """Loads all problems from the database."""
    return {p["problem_id"]: base_process_problem(p, time_testing, time_now) for p in problems}

@ProblemLoader.register("load_random")
def load_random(problems, count=1, time_testing=None, time_now=None):
    """Loads a random subset of problems."""
    selected = random.sample(problems, min(len(problems), count))
    return {p["problem_id"]: base_process_problem(p, time_testing, time_now) for p in selected}

@ProblemLoader.register("load_by_source")
def load_by_source(problems, source, time_testing=None, time_now=None):
    """Loads problems from a specific source."""
    filtered = [p for p in problems if p.get("metadata", {}).get("source") == source]
    return {p["problem_id"]: base_process_problem(p, time_testing, time_now) for p in filtered}
