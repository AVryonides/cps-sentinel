"""Deterministic synthetic PV and load profile generation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from cps_sentinel.config import Settings


def generate_profiles(settings: Settings) -> pd.DataFrame:
    """Generate reproducible, non-negative PV and load profiles."""
    reference = generate_reference_profiles(settings)
    simulation = settings.simulation
    profile = simulation.profiles
    periods = len(reference)
    rng = np.random.default_rng(settings.random_seed)

    pv_multiplier = np.clip(1 + rng.normal(0, profile.pv_variability_fraction, periods), 0, None)
    pv_kw = np.clip(reference["pv_kw"].to_numpy() * pv_multiplier, 0, None)
    load_noise = rng.normal(0, profile.load_noise_std_kw, periods)
    load_kw = np.clip(reference["load_kw"].to_numpy() + load_noise, 0, None)

    return pd.DataFrame({"timestamp": reference["timestamp"], "pv_kw": pv_kw, "load_kw": load_kw})


def generate_reference_profiles(settings: Settings) -> pd.DataFrame:
    """Generate noise-free time-based inputs for the independent digital twin."""
    simulation = settings.simulation
    profile = simulation.profiles
    periods = simulation.duration_hours * 60 // simulation.timestep_minutes
    timestamps = pd.date_range(
        start=simulation.start_time,
        periods=periods,
        freq=pd.Timedelta(minutes=simulation.timestep_minutes),
    )
    hours = timestamps.hour.to_numpy(dtype=float) + timestamps.minute.to_numpy(dtype=float) / 60
    pv_kw = profile.pv_peak_kw * _daylight_shape(hours)
    morning = profile.load_morning_peak_kw * _gaussian_peak(hours, center=7.5, width=1.4)
    evening = profile.load_evening_peak_kw * _gaussian_peak(hours, center=19.0, width=2.0)
    load_kw = profile.load_base_kw + morning + evening
    return pd.DataFrame({"timestamp": timestamps, "pv_kw": pv_kw, "load_kw": load_kw})


def _daylight_shape(hours: NDArray[np.float64]) -> NDArray[np.float64]:
    daylight = np.zeros_like(hours)
    mask = (hours >= 6.0) & (hours <= 18.0)
    daylight[mask] = np.sin(np.pi * (hours[mask] - 6.0) / 12.0) ** 1.35
    return daylight


def _gaussian_peak(hours: NDArray[np.float64], center: float, width: float) -> NDArray[np.float64]:
    return np.exp(-0.5 * ((hours - center) / width) ** 2)
