"""Calibrated hybrid physics-aware and Isolation Forest detector."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from cps_sentinel.config import DetectionConfig
from cps_sentinel.detection.diagnosis import diagnose_rows
from cps_sentinel.detection.features import FEATURE_FLOORS, FEATURES, prepare_features


@dataclass(frozen=True)
class FeatureCalibration:
    center: float
    threshold: float


class HybridDetector:
    """Detect persistent anomalies after fitting exclusively on clean baseline data."""

    def __init__(self, config: DetectionConfig, random_seed: int) -> None:
        self.config = config
        self.random_seed = random_seed
        self.calibrations: dict[str, FeatureCalibration] = {}
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=config.isolation_estimators,
            contamination="auto",
            random_state=random_seed,
            n_jobs=1,
        )
        self._normal_ml_scores = np.array([], dtype=float)
        self._fitted = False

    def fit(self, normal_frame: pd.DataFrame) -> HybridDetector:
        """Calibrate robust thresholds and ML score distribution on normal data only."""
        normal = prepare_features(normal_frame)
        for feature in FEATURES:
            values = normal[feature].to_numpy(dtype=float)
            center = float(np.median(values))
            deviations = np.abs(values - center)
            mad = float(np.median(deviations))
            robust_limit = self.config.robust_z_threshold * 1.4826 * mad
            quantile_limit = float(np.quantile(deviations, self.config.calibration_quantile))
            threshold = max(FEATURE_FLOORS[feature], robust_limit, quantile_limit)
            self.calibrations[feature] = FeatureCalibration(center, threshold)

        matrix = normal.loc[:, FEATURES].to_numpy(dtype=float)
        scaled = self.scaler.fit_transform(matrix)
        self.model.fit(scaled)
        self._normal_ml_scores = np.sort(-self.model.decision_function(scaled))
        self._fitted = True
        return self

    def detect(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Score, temporally correlate, and diagnose a twin-enriched observation frame."""
        if not self._fitted:
            raise RuntimeError("HybridDetector.fit must be called before detect")
        detected = prepare_features(frame)
        breach_columns: list[str] = []
        ratio_columns: list[str] = []
        for feature, calibration in self.calibrations.items():
            deviation = (detected[feature] - calibration.center).abs()
            ratio_column = f"{feature}_threshold_ratio"
            breach_column = f"{feature}_breach"
            detected[ratio_column] = deviation / calibration.threshold
            detected[breach_column] = detected[ratio_column] > 1.0
            ratio_columns.append(ratio_column)
            breach_columns.append(breach_column)

        detected["physics_vote_count"] = detected[breach_columns].sum(axis=1).astype(int)
        detected["physics_score"] = detected[ratio_columns].max(axis=1)
        detected["physics_detected"] = (
            detected["physics_vote_count"] >= self.config.physics_min_votes
        )
        detected["physics_evidence"] = detected.apply(
            lambda row: "|".join(feature for feature in FEATURES if bool(row[f"{feature}_breach"])),
            axis=1,
        )

        matrix = detected.loc[:, FEATURES].to_numpy(dtype=float)
        ml_scores = -self.model.decision_function(self.scaler.transform(matrix))
        detected["ml_anomaly_score"] = ml_scores
        detected["ml_anomaly_percentile"] = [self._score_percentile(score) for score in ml_scores]
        detected["ml_detected"] = (
            detected["ml_anomaly_percentile"] >= self.config.ml_score_percentile
        )
        detected["raw_detected"] = detected["physics_detected"] | detected["ml_detected"]

        persistence_count = (
            detected["raw_detected"]
            .astype(int)
            .rolling(self.config.persistence_window, min_periods=1)
            .sum()
        )
        detected["persistence_vote_count"] = persistence_count.astype(int)
        detected["detected"] = persistence_count >= self.config.persistence_votes

        physics_confidence = np.clip(detected["physics_score"] / 3.0, 0, 1)
        ml_confidence = np.clip((detected["ml_anomaly_percentile"] - 0.90) / 0.10, 0, 1)
        raw_confidence = np.maximum(physics_confidence, ml_confidence)
        rolling_confidence = (
            pd.Series(raw_confidence, index=detected.index)
            .rolling(self.config.persistence_window, min_periods=1)
            .max()
        )
        detected["confidence"] = np.where(detected["detected"], rolling_confidence, 0.0)
        detected["severity"] = detected["confidence"].map(_severity)
        return diagnose_rows(detected)

    def _score_percentile(self, score: float) -> float:
        rank = np.searchsorted(self._normal_ml_scores, score, side="right")
        return float(rank / len(self._normal_ml_scores))


def _severity(confidence: float) -> str:
    if confidence >= 0.90:
        return "critical"
    if confidence >= 0.70:
        return "high"
    if confidence >= 0.45:
        return "medium"
    if confidence > 0:
        return "low"
    return "none"
