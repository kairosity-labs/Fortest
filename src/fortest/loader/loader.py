import os
import json
import importlib
import pkgutil
from datetime import datetime
from typing import Dict, List, Callable, Any

class ProblemLoader:
    _registry: Dict[str, Callable] = {}

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "problems", "problems.json")
        self.db_path = db_path
        self._load_registry()

    def _load_registry(self):
        """Automatically register loaders from the custom_loaders directory."""
        import fortest.loader.custom_loaders as custom_loaders
        path = custom_loaders.__path__
        for loader, name, ispkg in pkgutil.iter_modules(path):
            module = importlib.import_module(f"fortest.loader.custom_loaders.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, "_is_loader"):
                    self._registry[attr._loader_name] = attr

    @classmethod
    def register(cls, name: str):
        """Decorator to register a custom loader function."""
        def decorator(func):
            func._is_loader = True
            func._loader_name = name
            return func
        return decorator

    def list_available_loaders(self) -> List[str]:
        """Returns a list of implemented custom loading functions."""
        return list(self._registry.keys())

    def load(self, strategy: str, **kwargs) -> Dict[str, Any]:
        """Loads problems using the specified strategy."""
        if strategy not in self._registry:
            raise ValueError(f"Loader strategy '{strategy}' not found. Available: {self.list_available_loaders()}")
        
        # Load raw data
        with open(self.db_path, "r") as f:
            raw_problems = json.load(f)
            
        return self._registry[strategy](raw_problems, **kwargs)

def base_process_problem(problem: Dict, time_testing: str = None, time_now: str = None) -> Dict:
    """Helper to add time_testing and time_now to a problem."""
    processed = problem.copy()
    now_dt = datetime.now()
    processed["time_now"] = time_now or now_dt.isoformat()
    processed["time_testing"] = time_testing or processed["time_start"] # Default to start if not provided
    return processed
