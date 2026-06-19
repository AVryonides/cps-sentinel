"""Phase 0 landing page for the CPS Sentinel dashboard."""

from pathlib import Path

import streamlit as st

from cps_sentinel.config import load_settings

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = load_settings(ROOT / "config" / "default.yaml")

st.set_page_config(page_title="CPS Sentinel", page_icon="🛡️", layout="wide")
st.title("CPS Sentinel")
st.caption("Digital Twin-Based Security and Health Monitoring for Cyber-Physical Systems")

left, middle, right = st.columns(3)
left.metric("Project phase", "4 - Detection and diagnosis")
middle.metric("Simulation horizon", f"{SETTINGS.simulation.duration_hours} hours")
right.metric("Timestep", f"{SETTINGS.simulation.timestep_minutes} minutes")

st.info(
    "Hybrid physics-aware and statistical detection is available from the command line. "
    "A later dashboard phase will expose detection evidence interactively."
)
