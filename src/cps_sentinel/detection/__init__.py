"""Hybrid physics-aware and statistical anomaly detection."""

from cps_sentinel.detection.detector import HybridDetector
from cps_sentinel.detection.evaluation import DetectionEvaluation, evaluate_detection
from cps_sentinel.detection.events import EventRecord, aggregate_events, write_events

__all__ = [
    "DetectionEvaluation",
    "EventRecord",
    "HybridDetector",
    "aggregate_events",
    "evaluate_detection",
    "write_events",
]
