"""Ground-truth evaluation kept separate from detector inputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DetectionEvaluation:
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    event_detected: bool
    detection_delay_steps: int | None


def evaluate_detection(frame: pd.DataFrame) -> DetectionEvaluation:
    """Evaluate detections against labels without feeding labels into detection."""
    truth = frame["scenario_active"].astype(bool).to_numpy()
    prediction = frame["detected"].astype(bool).to_numpy()
    true_positives = int(np.sum(truth & prediction))
    false_positives = int(np.sum(~truth & prediction))
    false_negatives = int(np.sum(truth & ~prediction))
    true_negatives = int(np.sum(~truth & ~prediction))
    precision = _safe_divide(true_positives, true_positives + false_positives)
    recall = _safe_divide(true_positives, true_positives + false_negatives)
    f1 = _safe_divide(2 * precision * recall, precision + recall)
    false_positive_rate = _safe_divide(false_positives, false_positives + true_negatives)

    truth_indices = np.flatnonzero(truth)
    matching_detections = np.flatnonzero(truth & prediction)
    event_detected = len(matching_detections) > 0
    delay = (
        int(matching_detections[0] - truth_indices[0])
        if event_detected and len(truth_indices) > 0
        else None
    )
    return DetectionEvaluation(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        event_detected=event_detected,
        detection_delay_steps=delay,
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0
