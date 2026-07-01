from pathlib import Path

import numpy as np
import pandas as pd

from cps_sentinel.config import load_settings
from cps_sentinel.swat import (
    SwatAttackWindow,
    SwatDetector,
    aggregate_swat_events,
    evaluate_swat_detection,
    load_swat_file,
    load_swat_scheduled_file,
)

ROOT = Path(__file__).resolve().parents[2]


def _swat_frame(rows: int, *, attack_start: int | None = None) -> pd.DataFrame:
    index = np.arange(rows)
    attack = np.zeros(rows, dtype=bool)
    if attack_start is not None:
        attack[attack_start : attack_start + 50] = True
    lit101 = 500 + 15 * np.sin(index / 20)
    fit101 = 2.5 + 0.15 * np.cos(index / 15)
    mv101 = (np.sin(index / 30) > 0).astype(float)
    lit101 = lit101 + attack * 180
    fit101 = fit101 - attack * 1.8
    return pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-01-01", periods=rows, freq="s"),
            "LIT101": lit101,
            "FIT101": fit101,
            "MV101": mv101,
            "Normal/Attack": np.where(attack, "Attack", "Normal"),
        }
    )


def test_load_swat_csv_normalizes_schema_and_labels(tmp_path: Path) -> None:
    source = tmp_path / "swat.csv"
    frame = _swat_frame(20, attack_start=8)
    frame["P101"] = np.where((np.arange(20) // 2) % 2, "Active", "Inactive")
    frame.to_csv(source, index=False)

    loaded = load_swat_file(source, sample_stride=2)

    assert list(loaded.columns[:2]) == ["timestamp", "is_attack"]
    assert len(loaded) == 10
    assert loaded["is_attack"].sum() == 6
    assert set(loaded["P101"]) == {0.0, 1.0}


def test_load_swat_excel_workbook(tmp_path: Path) -> None:
    source = tmp_path / "swat.xlsx"
    _swat_frame(12, attack_start=6).to_excel(source, index=False)

    loaded = load_swat_file(source)

    assert len(loaded) == 12
    assert loaded["is_attack"].sum() == 6
    assert {"LIT101", "FIT101", "MV101"}.issubset(loaded.columns)


def test_load_swat_scheduled_excel_labels_official_windows(tmp_path: Path) -> None:
    source = tmp_path / "scheduled.xlsx"
    rows = [
        ["", "P1", "", ""],
        ["GMT +0", "FIT 101", "LIT 101", "MV 101"],
        ["timestamp", "value", "value", "value"],
    ]
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=140, freq="s")
    for index, timestamp in enumerate(timestamps):
        rows.append(
            [
                timestamp.isoformat().replace("+00:00", "Z"),
                2.5 + index / 100,
                500 + index,
                "Open" if index % 2 else "Closed",
            ]
        )
    pd.DataFrame(rows).to_excel(source, index=False, header=False)

    loaded = load_swat_scheduled_file(
        source,
        attack_windows=(
            SwatAttackWindow(
                "synthetic scheduled attack",
                "2026-01-01T00:01:00Z",
                "2026-01-01T00:01:30Z",
            ),
        ),
        start="2026-01-01T00:00:30Z",
        end="2026-01-01T00:01:40Z",
    )

    assert list(loaded.columns[:2]) == ["timestamp", "is_attack"]
    assert loaded["is_attack"].sum() > 0
    assert loaded["timestamp"].min() >= pd.Timestamp("2026-01-01T00:00:30")
    assert {"FIT_101", "LIT_101", "MV_101"}.issubset(loaded.columns)
    assert set(loaded["MV_101"]) == {0.0, 1.0}


def test_swat_detector_is_time_safe_and_detects_attack_event(tmp_path: Path) -> None:
    normal_path = tmp_path / "normal.csv"
    attack_path = tmp_path / "attack.csv"
    _swat_frame(500).to_csv(normal_path, index=False)
    _swat_frame(300, attack_start=120).to_csv(attack_path, index=False)
    settings = load_settings(ROOT / "config" / "default.yaml")

    normal = load_swat_file(normal_path)
    attack = load_swat_file(attack_path)
    result = SwatDetector(settings.swat, settings.random_seed).fit(normal).detect(attack)
    evaluation = evaluate_swat_detection(result)
    events = aggregate_swat_events(result, settings.swat)

    assert "Normal_Attack" not in result.columns
    assert evaluation.recall > 0.70
    assert evaluation.detected_attack_events == 1
    assert any(event.overlaps_labeled_attack for event in events)
    assert any("LIT101" in event.top_affected_tags for event in events)


def test_missing_swat_tags_are_rejected(tmp_path: Path) -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")
    normal = load_swat_file(_write_csv(tmp_path / "normal.csv", _swat_frame(200)))
    attack = load_swat_file(_write_csv(tmp_path / "attack.csv", _swat_frame(150)))
    detector = SwatDetector(settings.swat, settings.random_seed).fit(normal)

    attack = attack.drop(columns="FIT101")

    try:
        detector.detect(attack)
    except ValueError as error:
        assert "FIT101" in str(error)
    else:
        raise AssertionError("missing trained SWaT tag was accepted")


def _write_csv(path: Path, frame: pd.DataFrame) -> Path:
    frame.to_csv(path, index=False)
    return path
