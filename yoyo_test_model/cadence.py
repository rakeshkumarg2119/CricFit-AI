"""
Step cadence counting, scoped to a single running leg's frame range.

Root-cause history worth keeping visible: the first version of this
averaged left-ankle-y and right-ankle-y together. During running the two
ankles bob in OPPOSITE phase (one plants while the other swings) -
averaging two opposite-phase signals cancels almost all of the real signal,
leaving only the much smaller whole-body center-of-mass bounce plus
landmark jitter. That's what produced 0 detected steps on real footage.
Confirmed with a synthetic gait signal before shipping the fix: the
averaged signal's peak-to-peak amplitude collapsed to roughly the noise
floor (and occasionally still found a few "steps" out of pure noise -
silently wrong rather than obviously broken).

Fix: track left-ankle-y MINUS right-ankle-y instead of the average. This
preserves the alternating step signal at roughly 10x the amplitude in
testing. Both directions of extrema in this difference signal are counted
as steps (one footfall each).
"""

import numpy as np
from scipy.signal import find_peaks

try:
    from . import config
except (ImportError, ValueError):
    import config


def cadence_in_range(start_idx, end_idx, diff_series, timestamps, fps,
                      body_scale_series=None, max_body_scale=None):
    """
    diff_series: left-ankle-y MINUS right-ankle-y (see module docstring),
                 NOT the average. Each footfall shows up as an extremum in
                 EITHER direction here, so both find_peaks(diff) and
                 find_peaks(-diff) are counted as steps.

    Peak prominence is ADAPTIVE - scaled to this leg's own ankle-bob
    amplitude instead of a fixed constant. A clean periodic bob has peak
    prominence of roughly half its peak-to-peak swing, so 0.4 x ptp is
    slightly conservative and auto-tunes to camera distance and running
    speed. The floor only matters for legs with a nearly-flat bob.

    Confidence flag: checked against real footage - when the player is
    far/small in frame, ankle landmarks are only a handful of pixels apart
    and neither the algorithm nor a human eye can reliably resolve
    individual footfalls (confirmed by manually reviewing frames leg-by-leg
    before adding this). Rather than silently report a number that may be
    undercounted, each leg's average body_scale during its own window is
    compared to the biggest body_scale seen anywhere in the session (i.e.
    how close the player got to camera at best); below
    CADENCE_CONFIDENCE_THRESHOLD_PCT of that and the leg is flagged "low"
    confidence instead of "high".
    """
    sub_diff = diff_series[start_idx:end_idx]
    sub_t = timestamps[start_idx:end_idx]
    if len(sub_diff) < 3:
        return {"steps": 0, "cadence": 0.0, "duration_sec": 0.0,
                "confidence": "unknown", "avg_body_scale_pct_of_max": None}

    prominence = max(config.CADENCE_PROMINENCE_FLOOR, 0.4 * float(np.ptp(sub_diff)))
    min_spacing = max(1, int(config.MIN_STEP_INTERVAL_SEC * fps))

    max_idx, _ = find_peaks(sub_diff, distance=min_spacing, prominence=prominence)
    min_idx, _ = find_peaks(-sub_diff, distance=min_spacing, prominence=prominence)
    n_steps = len(max_idx) + len(min_idx)

    duration = sub_t[-1] - sub_t[0] if len(sub_t) > 1 else 1.0
    cadence = n_steps / duration if duration > 0 else 0.0

    confidence = "unknown"
    avg_scale_pct = None
    if body_scale_series is not None and max_body_scale:
        sub_scale = body_scale_series[start_idx:end_idx]
        if len(sub_scale) > 0:
            avg_scale_pct = round(float(np.mean(sub_scale) / max_body_scale) * 100, 1)
            confidence = "high" if avg_scale_pct >= config.CADENCE_CONFIDENCE_THRESHOLD_PCT else "low"

    return {
        "steps": int(n_steps),
        "cadence": round(float(cadence), 2),
        "duration_sec": round(float(duration), 2),
        "confidence": confidence,
        "avg_body_scale_pct_of_max": avg_scale_pct,
    }
