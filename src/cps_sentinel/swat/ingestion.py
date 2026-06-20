"""Robust ingestion for authorized SWaT historian files."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

_TIMESTAMP_NAMES = {"timestamp", "time", "datetime", "date_time"}
_LABEL_NAMES = {
    "normal_attack",
    "normalattack",
    "attack",
    "label",
    "class",
    "is_attack",
}


def load_swat_file(
    path: str | Path,
    *,
    assume_attack: bool = False,
    sample_stride: int = 1,
) -> pd.DataFrame:
    """Load a SWaT historian CSV/XLSX into timestamp, label, and numeric tag columns."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"SWaT historian file not found: {source}")
    if sample_stride <= 0:
        raise ValueError("sample_stride must be positive")

    raw = _read_table(source)
    if raw.empty:
        raise ValueError(f"SWaT historian file contains no rows: {source}")
    raw.columns = _deduplicate([_normalize_name(column) for column in raw.columns])
    timestamp_column = _find_column(raw.columns, _TIMESTAMP_NAMES)
    label_column = _find_column(raw.columns, _LABEL_NAMES)

    if timestamp_column is None:
        timestamp = pd.Series(pd.RangeIndex(len(raw)), name="timestamp")
    else:
        timestamp = _parse_timestamp(raw.pop(timestamp_column))
    if label_column is None:
        labels = pd.Series(assume_attack, index=raw.index, dtype=bool)
    else:
        labels = raw.pop(label_column).map(_is_attack_label).astype(bool)

    numeric = _coerce_tags(raw)
    if numeric.shape[1] < 2:
        raise ValueError("SWaT CSV must contain at least two numeric sensor or actuator tags")
    frame = pd.concat(
        [
            timestamp.reset_index(drop=True),
            labels.rename("is_attack").reset_index(drop=True),
            numeric,
        ],
        axis=1,
    )
    frame = frame.iloc[::sample_stride].reset_index(drop=True)
    if frame["timestamp"].isna().all():
        frame["timestamp"] = pd.RangeIndex(len(frame)) * sample_stride
    return frame


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, engine="openpyxl")
    if path.suffix.lower() not in {".csv", ".txt"}:
        raise ValueError("SWaT historian input must be CSV, TXT, XLSX, or XLSM")
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp1252", low_memory=False)


def _normalize_name(value: object) -> str:
    name = str(value).strip().strip('"').replace("/", "_")
    name = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    return name or "unnamed"


def _deduplicate(columns: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for column in columns:
        counts[column] = counts.get(column, 0) + 1
        suffix = f"_{counts[column]}" if counts[column] > 1 else ""
        result.append(f"{column}{suffix}")
    return result


def _find_column(columns: pd.Index, candidates: set[str]) -> str | None:
    for column in columns:
        if str(column).lower() in candidates:
            return str(column)
    return None


def _parse_timestamp(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values.astype(str).str.strip(), errors="coerce", dayfirst=True)
    if parsed.notna().any():
        return parsed.rename("timestamp")
    return values.rename("timestamp")


def _is_attack_label(value: object) -> bool:
    if value is None or value is pd.NA:
        return False
    if isinstance(value, (float, np.floating)) and np.isnan(float(value)):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value) < 0 or float(value) == 1
    normalized = str(value).strip().lower()
    return normalized in {"attack", "abnormal", "anomaly", "true", "1", "-1", "yes"}


def _coerce_tags(frame: pd.DataFrame) -> pd.DataFrame:
    converted: dict[str, pd.Series] = {}
    replacements = {
        "active": 1.0,
        "inactive": 0.0,
        "open": 1.0,
        "closed": 0.0,
        "on": 1.0,
        "off": 0.0,
    }
    for column in frame.columns:
        values = frame[column]
        if values.dtype == object:
            lowered = values.astype(str).str.strip().str.lower()
            values = lowered.map(lambda value: replacements.get(value, value))
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.notna().mean() >= 0.95:
            converted[str(column)] = numeric.astype(float).reset_index(drop=True)
    return pd.DataFrame(converted)
