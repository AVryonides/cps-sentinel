"""Ingest NASA PCoE MATLAB battery files into a stable cycle-level contract."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

REQUIRED_COLUMNS = (
    "battery_id",
    "cycle_index",
    "source_cycle_index",
    "timestamp",
    "ambient_temperature_c",
    "capacity_ah",
    "discharge_duration_s",
    "minimum_voltage_v",
    "maximum_temperature_c",
)


def load_nasa_battery(path: str | Path) -> pd.DataFrame:
    """Load discharge-cycle health measurements from one NASA MATLAB file."""
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"NASA battery file not found: {source}")
    payload = loadmat(source, simplify_cells=True)
    battery_id = source.stem
    battery = payload.get(battery_id)
    if not isinstance(battery, dict) or "cycle" not in battery:
        raise ValueError(f"{source.name} does not contain the expected '{battery_id}.cycle' data")

    cycles = battery["cycle"]
    if isinstance(cycles, dict):
        cycles = [cycles]
    records: list[dict[str, object]] = []
    discharge_index = 0
    for source_index, cycle in enumerate(cycles, start=1):
        if not isinstance(cycle, dict) or str(cycle.get("type", "")).lower() != "discharge":
            continue
        data = cycle.get("data")
        if not isinstance(data, dict) or "Capacity" not in data:
            continue
        discharge_index += 1
        voltage = _numeric_array(data.get("Voltage_measured"))
        temperature = _numeric_array(data.get("Temperature_measured"))
        elapsed = _numeric_array(data.get("Time"))
        records.append(
            {
                "battery_id": battery_id,
                "cycle_index": discharge_index,
                "source_cycle_index": source_index,
                "timestamp": _matlab_datetime(cycle.get("time")),
                "ambient_temperature_c": float(cycle.get("ambient_temperature", np.nan)),
                "capacity_ah": float(np.asarray(data["Capacity"]).squeeze()),
                "discharge_duration_s": float(elapsed[-1]) if elapsed.size else np.nan,
                "minimum_voltage_v": float(np.min(voltage)) if voltage.size else np.nan,
                "maximum_temperature_c": (
                    float(np.max(temperature)) if temperature.size else np.nan
                ),
            }
        )
    if not records:
        raise ValueError(f"{source.name} contains no discharge capacity records")
    return pd.DataFrame.from_records(records, columns=REQUIRED_COLUMNS)


def load_nasa_batteries(path: str | Path) -> pd.DataFrame:
    """Load and combine all NASA battery MATLAB files below a path."""
    source = Path(path)
    files = [source] if source.is_file() else sorted(source.glob("B*.mat"))
    if not files:
        raise ValueError(f"No NASA B*.mat files found at: {source}")
    return pd.concat([load_nasa_battery(file) for file in files], ignore_index=True)


def _numeric_array(value: Any) -> np.ndarray:
    if value is None:
        return np.array([], dtype=float)
    return np.asarray(value, dtype=float).reshape(-1)


def _matlab_datetime(value: Any) -> str:
    parts = _numeric_array(value)
    if parts.size < 6:
        return ""
    second = int(parts[5])
    microsecond = round((float(parts[5]) - second) * 1_000_000)
    timestamp = datetime(
        int(parts[0]),
        int(parts[1]),
        int(parts[2]),
        int(parts[3]),
        int(parts[4]),
        second,
        microsecond,
        tzinfo=UTC,
    )
    return timestamp.isoformat()
