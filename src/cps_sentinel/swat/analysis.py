"""Time-safe anomaly detection and event explanation for SWaT historian data."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from cps_sentinel.config import SwatConfig


@dataclass(frozen=True)
class SwatEvaluation:
    rows: int
    attack_rows: int
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    ground_truth_events: int
    detected_attack_events: int
    event_recall: float
    median_detection_delay_steps: float | None


@dataclass(frozen=True)
class SwatEvent:
    event_id: str
    start_index: int
    end_index: int
    start_timestamp: str
    end_timestamp: str
    duration_steps: int
    detected_points: int
    peak_anomaly_score: float
    top_affected_tags: tuple[str, ...]
    overlaps_labeled_attack: bool
    physical_context: str
    recommended_actions: tuple[str, ...]
    safety_note: str = (
        "Detection is decision support only. Confirm process conditions and obtain operator "
        "approval before isolating equipment or changing control logic."
    )


class SwatDetector:
    """Isolation-Forest baseline fitted only on chronologically earlier normal data."""

    def __init__(self, config: SwatConfig, random_seed: int) -> None:
        self.config = config
        self.random_seed = random_seed
        self.feature_columns: list[str] = []
        self.medians: pd.Series | None = None
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=config.isolation_estimators,
            contamination="auto",
            random_state=random_seed,
            n_jobs=-1,
        )
        self.threshold: float | None = None
        self.model_calibration_scores: np.ndarray | None = None
        self.statistical_threshold: float | None = None

    def fit(self, normal: pd.DataFrame) -> SwatDetector:
        """Fit levels and first-difference features with a held-out normal calibration tail."""
        self.feature_columns = _feature_columns(normal)
        clean = normal.loc[~normal["is_attack"], self.feature_columns].copy()
        if len(clean) < 100:
            raise ValueError("SWaT normal training data must contain at least 100 clean rows")
        split = int(len(clean) * self.config.training_fraction)
        split = min(max(split, 50), len(clean) - 20)
        train = clean.iloc[:split]
        calibration = clean.iloc[split:]
        self.medians = train.median().fillna(0.0)
        train_values = self._fill(train)
        self.scaler.fit(train_values)
        train_augmented = self._augment(train_values)
        if len(train_augmented) > self.config.max_training_rows:
            rng = np.random.default_rng(self.random_seed)
            selected = np.sort(
                rng.choice(
                    len(train_augmented),
                    size=self.config.max_training_rows,
                    replace=False,
                )
            )
            train_augmented = train_augmented[selected]
        self.model.fit(train_augmented)
        calibration_values = self._fill(calibration)
        calibration_augmented = self._augment(calibration_values)
        calibration_model_score = -self.model.decision_function(calibration_augmented)
        calibration_statistical_score = np.max(np.abs(calibration_augmented), axis=1)
        self.model_calibration_scores = np.sort(calibration_model_score)
        self.statistical_threshold = float(
            np.quantile(calibration_statistical_score, self.config.score_quantile)
        )
        self.threshold = 1.0
        return self

    def detect(self, attack: pd.DataFrame) -> pd.DataFrame:
        """Score a later labeled run without using its labels as model inputs."""
        if (
            self.threshold is None
            or self.statistical_threshold is None
            or self.model_calibration_scores is None
            or self.medians is None
            or not self.feature_columns
        ):
            raise RuntimeError("SwatDetector must be fitted before detect")
        missing = set(self.feature_columns).difference(attack.columns)
        if missing:
            raise ValueError(f"SWaT attack data is missing trained tags: {sorted(missing)}")
        values = self._fill(attack[self.feature_columns])
        scaled = self.scaler.transform(values)
        augmented = self._augment(values)
        model_score = -self.model.decision_function(augmented)
        statistical_score = np.max(np.abs(augmented), axis=1)
        model_percentile = np.searchsorted(
            self.model_calibration_scores, model_score, side="right"
        ) / len(self.model_calibration_scores)
        statistical_ratio = statistical_score / max(self.statistical_threshold, 1e-9)
        model_ratio = model_percentile / self.config.score_quantile
        score = np.maximum(statistical_ratio, model_ratio)
        raw = score > self.threshold
        votes = (
            pd.Series(raw, dtype=int)
            .rolling(self.config.persistence_window, min_periods=1)
            .sum()
            .to_numpy()
        )
        detected = votes >= self.config.persistence_votes
        result = attack[["timestamp", "is_attack", *self.feature_columns]].copy()
        result["anomaly_score"] = score
        result["anomaly_threshold"] = self.threshold
        result["statistical_deviation_score"] = statistical_score
        result["model_anomaly_percentile"] = model_percentile
        result["raw_anomaly"] = raw
        result["persistence_votes"] = votes.astype(int)
        result["detected"] = detected
        result["top_contributors"] = ""
        for index in np.flatnonzero(detected):
            contribution = np.abs(scaled[index])
            order = np.argsort(contribution)[::-1][: self.config.top_contributors]
            result.at[index, "top_contributors"] = ", ".join(
                self.feature_columns[position] for position in order
            )
        return result

    def _fill(self, frame: pd.DataFrame) -> np.ndarray:
        medians = frame.median().fillna(0.0) if self.medians is None else self.medians
        return frame.ffill().fillna(medians).to_numpy(dtype=float)

    def _augment(self, values: np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(values)
        differences = np.vstack([np.zeros((1, scaled.shape[1])), np.diff(scaled, axis=0)])
        return np.hstack([scaled, differences])


def evaluate_swat_detection(frame: pd.DataFrame) -> SwatEvaluation:
    """Evaluate point and event detection against labels withheld during scoring."""
    truth = frame["is_attack"].astype(bool).to_numpy()
    predicted = frame["detected"].astype(bool).to_numpy()
    true_positive = int(np.sum(truth & predicted))
    false_positive = int(np.sum(~truth & predicted))
    false_negative = int(np.sum(truth & ~predicted))
    true_negative = int(np.sum(~truth & ~predicted))
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    false_positive_rate = _safe_ratio(false_positive, false_positive + true_negative)

    truth_intervals = _boolean_intervals(truth)
    prediction_intervals = _boolean_intervals(predicted)
    delays: list[int] = []
    detected_events = 0
    for truth_start, truth_end in truth_intervals:
        overlapping = [
            (start, end)
            for start, end in prediction_intervals
            if start <= truth_end and end >= truth_start
        ]
        if overlapping:
            detected_events += 1
            first_detection = min(max(start, truth_start) for start, _ in overlapping)
            delays.append(first_detection - truth_start)
    return SwatEvaluation(
        rows=len(frame),
        attack_rows=int(truth.sum()),
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        ground_truth_events=len(truth_intervals),
        detected_attack_events=detected_events,
        event_recall=_safe_ratio(detected_events, len(truth_intervals)),
        median_detection_delay_steps=float(np.median(delays)) if delays else None,
    )


def aggregate_swat_events(frame: pd.DataFrame, config: SwatConfig) -> list[SwatEvent]:
    """Aggregate persistent row flags into explainable industrial-security events."""
    indices = np.flatnonzero(frame["detected"].astype(bool).to_numpy())
    if len(indices) == 0:
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for index in indices[1:]:
        if int(index) - groups[-1][-1] <= config.event_gap_steps + 1:
            groups[-1].append(int(index))
        else:
            groups.append([int(index)])

    events: list[SwatEvent] = []
    for number, group in enumerate(groups, start=1):
        start, end = group[0], group[-1]
        rows = frame.iloc[start : end + 1]
        contributors = _rank_contributors(rows["top_contributors"], config.top_contributors)
        events.append(
            SwatEvent(
                event_id=f"SWAT-{number:03d}",
                start_index=start,
                end_index=end,
                start_timestamp=str(frame.iloc[start]["timestamp"]),
                end_timestamp=str(frame.iloc[end]["timestamp"]),
                duration_steps=end - start + 1,
                detected_points=len(group),
                peak_anomaly_score=round(float(rows["anomaly_score"].max()), 6),
                top_affected_tags=contributors,
                overlaps_labeled_attack=bool(rows["is_attack"].any()),
                physical_context=_physical_context(contributors),
                recommended_actions=(
                    "Compare the affected tag history with the operator log and attack schedule.",
                    "Verify related sensors and actuator states through an independent "
                    "process view.",
                    "Preserve historian and network evidence before making a control change.",
                ),
            )
        )
    return events


def write_swat_events(events: list[SwatEvent], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([asdict(event) for event in events], indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def _feature_columns(frame: pd.DataFrame) -> list[str]:
    columns = [column for column in frame.columns if column not in {"timestamp", "is_attack"}]
    if len(columns) < 2:
        raise ValueError("SWaT data must provide at least two tag columns")
    return columns


def _boolean_intervals(values: np.ndarray) -> list[tuple[int, int]]:
    indices = np.flatnonzero(values)
    if len(indices) == 0:
        return []
    intervals: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for index in indices[1:]:
        current = int(index)
        if current != previous + 1:
            intervals.append((start, previous))
            start = current
        previous = current
    intervals.append((start, previous))
    return intervals


def _rank_contributors(values: pd.Series, limit: int) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        for tag in str(value).split(", "):
            if tag:
                counts[tag] = counts.get(tag, 0) + 1
    ranked = sorted(counts, key=lambda tag: (-counts[tag], tag))
    return tuple(ranked[:limit])


def _physical_context(tags: tuple[str, ...]) -> str:
    if not tags:
        return "Persistent multivariate deviation in the water-treatment historian."
    stages = sorted({tag[:1] for tag in tags if tag[:1].isdigit()})
    stage_text = f" across process stage(s) {', '.join(stages)}" if stages else ""
    return f"Persistent deviation{stage_text}; leading evidence: {', '.join(tags)}."


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0
