"""Aggregate persistent row-level detections into explainable events."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class EventRecord:
    event_id: int
    start_time: str
    end_time: str
    duration_steps: int
    likely_event: str
    affected_component: str
    confidence: float
    severity: str
    evidence: tuple[str, ...]


def aggregate_events(frame: pd.DataFrame) -> list[EventRecord]:
    """Convert contiguous detected rows into event records."""
    events: list[EventRecord] = []
    active_indices = list(frame.index[frame["detected"]])
    if not active_indices:
        return events

    groups: list[list[int]] = [[int(active_indices[0])]]
    for index in active_indices[1:]:
        current = int(index)
        if current == groups[-1][-1] + 1:
            groups[-1].append(current)
        else:
            groups.append([current])

    for event_id, indices in enumerate(groups, start=1):
        event_rows = frame.loc[indices]
        severity = max(
            event_rows["severity"].astype(str),
            key=lambda value: SEVERITY_RANK.get(value, 0),
        )
        evidence = tuple(
            sorted(
                {
                    feature
                    for item in event_rows["physics_evidence"].astype(str)
                    for feature in item.split("|")
                    if feature
                }
            )
        )
        events.append(
            EventRecord(
                event_id=event_id,
                start_time=str(event_rows["timestamp"].iloc[0]),
                end_time=str(event_rows["timestamp"].iloc[-1]),
                duration_steps=len(event_rows),
                likely_event=str(event_rows["likely_event"].mode().iloc[0]),
                affected_component=str(event_rows["affected_component"].mode().iloc[0]),
                confidence=float(event_rows["confidence"].max()),
                severity=severity,
                evidence=evidence,
            )
        )
    return events


def write_events(events: list[EventRecord], path: str | Path) -> Path:
    """Write event records as human-readable JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([asdict(event) for event in events], indent=2) + "\n",
        encoding="utf-8",
    )
    return output
