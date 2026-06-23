"""Robust ingestion for authorized SWaT historian files."""

from __future__ import annotations

import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class SwatAttackWindow:
    """Attack interval from an official SWaT collection note."""

    name: str
    start: str
    end: str


SWAT_A4_A5_JUL_2019_ATTACK_WINDOWS: tuple[SwatAttackWindow, ...] = (
    SwatAttackWindow("FIT401 spoofing", "2019-07-20T07:08:46Z", "2019-07-20T07:10:31Z"),
    SwatAttackWindow("LIT301 spoofing", "2019-07-20T07:15:00Z", "2019-07-20T07:19:32Z"),
    SwatAttackWindow("P601 unauthorized start", "2019-07-20T07:26:57Z", "2019-07-20T07:30:48Z"),
    SwatAttackWindow(
        "MV201 and P101 multi-point attack",
        "2019-07-20T07:38:50Z",
        "2019-07-20T07:46:20Z",
    ),
    SwatAttackWindow("MV501 unauthorized close", "2019-07-20T07:54:00Z", "2019-07-20T07:56:00Z"),
    SwatAttackWindow("P301 unauthorized stop", "2019-07-20T08:02:56Z", "2019-07-20T08:16:18Z"),
)


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


def load_swat_scheduled_file(
    path: str | Path,
    *,
    attack_windows: tuple[SwatAttackWindow, ...],
    start: str | None = None,
    end: str | None = None,
    sample_stride: int = 1,
) -> pd.DataFrame:
    """Load a single SWaT run and derive labels from official attack windows."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"SWaT historian file not found: {source}")
    if sample_stride <= 0:
        raise ValueError("sample_stride must be positive")

    raw = _read_scheduled_table(source)
    if raw.empty:
        raise ValueError(f"SWaT historian file contains no rows: {source}")
    raw.columns = _deduplicate([_normalize_name(column) for column in raw.columns])
    timestamp_column = _find_column(raw.columns, _TIMESTAMP_NAMES | {"gmt_0"})
    if timestamp_column is None:
        raise ValueError("Scheduled SWaT run must contain a timestamp column")

    timestamp = _parse_timestamp(raw.pop(timestamp_column))
    mask = pd.Series(True, index=raw.index)
    if start is not None:
        mask &= timestamp >= _timestamp_boundary(start)
    if end is not None:
        mask &= timestamp <= _timestamp_boundary(end)
    raw = raw.loc[mask].reset_index(drop=True)
    timestamp = timestamp.loc[mask].reset_index(drop=True)
    labels = _labels_from_windows(timestamp, attack_windows)
    numeric = _coerce_tags(raw)
    if numeric.shape[1] < 2:
        raise ValueError("SWaT file must contain at least two numeric sensor or actuator tags")
    frame = pd.concat(
        [
            timestamp.rename("timestamp").reset_index(drop=True),
            labels.rename("is_attack").reset_index(drop=True),
            numeric,
        ],
        axis=1,
    )
    return frame.iloc[::sample_stride].reset_index(drop=True)


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, engine="openpyxl")
    if path.suffix.lower() not in {".csv", ".txt"}:
        raise ValueError("SWaT historian input must be CSV, TXT, XLSX, or XLSM")
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp1252", low_memory=False)


def _read_scheduled_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        return _read_table(path)
    raw = pd.read_excel(path, engine="openpyxl", header=None)
    if len(raw) >= 4:
        header = raw.iloc[1].where(raw.iloc[1].notna(), raw.iloc[2])
        data = raw.iloc[3:].copy()
        data.columns = header
        data = data.dropna(axis=1, how="all")
        return data
    return pd.read_excel(path, engine="openpyxl")


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
    text = values.astype(str).str.strip()
    parsed = pd.to_datetime(text, errors="coerce", utc=True, format="mixed")
    if parsed.notna().sum() == 0:
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True, utc=True, format="mixed")
    if parsed.notna().any():
        return parsed.dt.tz_convert(None).rename("timestamp")
    return values.rename("timestamp")


def _labels_from_windows(
    timestamp: pd.Series, attack_windows: tuple[SwatAttackWindow, ...]
) -> pd.Series:
    labels = pd.Series(False, index=timestamp.index, dtype=bool)
    for window in attack_windows:
        start = _timestamp_boundary(window.start)
        end = _timestamp_boundary(window.end)
        labels |= (timestamp >= start) & (timestamp <= end)
    return labels


def _timestamp_boundary(value: str) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is not None:
        return parsed.tz_convert(None)
    return parsed


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
