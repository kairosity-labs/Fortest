"""
ForecastBench Templatized Dataset Resolver

This module provides interfaces for dynamically generating and resolving 
templatized forecasting questions with custom date ranges.

TODO: Implement actual data fetching and resolution logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
from pathlib import Path


@dataclass
class TemplatedQuestion:
    """A templatized question with placeholders for dates."""
    id: str
    source: str
    question_template: str
    resolution_criteria: str
    background: str
    url: str
    source_intro: str
    
    def render(self, forecast_due_date: str, resolution_date: str) -> str:
        """Render the question with actual dates."""
        return self.question_template.replace(
            '{forecast_due_date}', forecast_due_date
        ).replace(
            '{resolution_date}', resolution_date
        )


@dataclass 
class ResolvedQuestion:
    """A resolved question with dates and resolution."""
    id: str
    source: str
    question: str
    forecast_due_date: str
    resolution_date: str
    resolved_to: Optional[float] = None  # 0.0 or 1.0
    resolution_value: Optional[Any] = None  # actual data value


class BaseResolver(ABC):
    """Abstract base class for question resolvers."""
    
    @abstractmethod
    def fetch_value(self, question_id: str, date: str) -> Any:
        """Fetch the value for a question at a specific date."""
        pass
    
    @abstractmethod
    def resolve(
        self, 
        template: TemplatedQuestion,
        forecast_due_date: str, 
        resolution_date: str
    ) -> ResolvedQuestion:
        """Resolve a templatized question for given dates."""
        pass


class DummyResolver(BaseResolver):
    """Dummy resolver for testing - always returns None."""
    
    def fetch_value(self, question_id: str, date: str) -> Any:
        """TODO: Implement actual data fetching."""
        return None
    
    def resolve(
        self, 
        template: TemplatedQuestion,
        forecast_due_date: str, 
        resolution_date: str
    ) -> ResolvedQuestion:
        """Create resolved question without actual resolution."""
        return ResolvedQuestion(
            id=template.id,
            source=template.source,
            question=template.render(forecast_due_date, resolution_date),
            forecast_due_date=forecast_due_date,
            resolution_date=resolution_date,
            resolved_to=None,
            resolution_value=None,
        )


class TemplateLoader:
    """Load and manage templatized questions."""
    
    def __init__(self, templates_path: str = None):
        if templates_path is None:
            templates_path = Path(__file__).parent / 'templates.json'
        self.templates_path = Path(templates_path)
        self._templates: List[TemplatedQuestion] = []
        self._load()
    
    def _load(self):
        """Load templates from JSON file."""
        with open(self.templates_path) as f:
            data = json.load(f)
        
        for t in data.get('templates', []):
            self._templates.append(TemplatedQuestion(
                id=t['id'],
                source=t['source'],
                question_template=t['question_template'],
                resolution_criteria=t.get('resolution_criteria', ''),
                background=t.get('background', ''),
                url=t.get('url', ''),
                source_intro=t.get('source_intro', ''),
            ))
    
    @property
    def templates(self) -> List[TemplatedQuestion]:
        """Get all templates."""
        return self._templates
    
    def get_by_source(self, source: str) -> List[TemplatedQuestion]:
        """Get templates by source."""
        return [t for t in self._templates if t.source == source]
    
    def get_by_id(self, question_id: str) -> Optional[TemplatedQuestion]:
        """Get template by ID."""
        for t in self._templates:
            if t.id == question_id:
                return t
        return None
    
    @property
    def sources(self) -> List[str]:
        """Get unique sources."""
        return list(set(t.source for t in self._templates))


def generate_dataset(
    loader: TemplateLoader,
    resolver: BaseResolver,
    forecast_due_date: str,
    resolution_date: str,
    sources: List[str] = None,
) -> List[ResolvedQuestion]:
    """
    Generate a dataset of resolved questions for given dates.
    
    Args:
        loader: TemplateLoader with templates
        resolver: Resolver to use for resolution
        forecast_due_date: Start date (YYYY-MM-DD)
        resolution_date: End date (YYYY-MM-DD)
        sources: Optional list of sources to include
    
    Returns:
        List of ResolvedQuestion objects
    """
    results = []
    
    for template in loader.templates:
        if sources and template.source not in sources:
            continue
        
        resolved = resolver.resolve(template, forecast_due_date, resolution_date)
        results.append(resolved)
    
    return results
