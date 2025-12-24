from typing import List, Union

def brier_score(predictions: List[float], outcomes: List[int]) -> float:
    """Calculates the Brier score for a set of predictions and outcomes."""
    if len(predictions) != len(outcomes):
        raise ValueError("Predictions and outcomes must have the same length.")
    if not predictions:
        return 0.0
    
    squared_errors = [(p - o) ** 2 for p, o in zip(predictions, outcomes)]
    return sum(squared_errors) / len(predictions)

def accuracy(predictions: List[float], outcomes: List[int], threshold: float = 0.5) -> float:
    """Calculates accuracy based on a probability threshold."""
    if len(predictions) != len(outcomes):
        raise ValueError("Predictions and outcomes must have the same length.")
    if not predictions:
        return 0.0
    
    correct = 0
    for p, o in zip(predictions, outcomes):
        pred_label = 1 if p >= threshold else 0
        if pred_label == o:
            correct += 1
            
    return correct / len(predictions)
