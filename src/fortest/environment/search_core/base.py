import os
import importlib
import pkgutil
from typing import Dict, List, Callable, Any

class SearchCore:
    _registry: Dict[str, Callable] = {}

    def __init__(self):
        self._load_registry()

    def _load_registry(self):
        """Automatically register search functions from the search_core directory."""
        import fortest.environment.search_core as search_core_pkg
        path = search_core_pkg.__path__
        for loader, name, ispkg in pkgutil.iter_modules(path):
            if name == "base": continue
            module = importlib.import_module(f"fortest.environment.search_core.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, "_is_search_func"):
                    self._registry[attr._search_name] = attr

    @classmethod
    def register(cls, name: str):
        """Decorator to register a search function."""
        def decorator(func):
            func._is_search_func = True
            func._search_name = name
            return func
        return decorator

    def list_available_functions(self) -> List[str]:
        """Returns a list of available search functions."""
        return list(self._registry.keys())

    async def execute(self, function_name: str, query: str, testing_time: str, **kwargs) -> Any:
        """Executes a search function with optional parameters like k."""
        if function_name not in self._registry:
            raise ValueError(f"Search function '{function_name}' not found. Available: {self.list_available_functions()}")
        return await self._registry[function_name](query, testing_time, **kwargs)
