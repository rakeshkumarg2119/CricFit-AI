"""
Small, pure numeric helpers shared by segmentation.py and cadence.py. No
tracking state, no MediaPipe - just numpy in, numpy out. Kept separate so
they're easy to unit-test in isolation from anything camera/video-related.
"""

import numpy as np


def smooth(signal, window):
    """Edge-safe moving average.

    Plain np.convolve(..., mode="same") implicitly zero-pads past the array
    boundary, which drags the smoothed value toward 0 for roughly the last
    half-window of samples - exactly where the LAST leg of a clip lives
    (video just ends there, no closing turn). That artificial pull can
    create a fake extremum right at the tail, chopping the final real leg
    into slivers too short to pass MIN_LEG_DURATION_SEC. Edge-padding with
    the boundary value itself (not zero) removes that artifact.
    """
    if window <= 1:
        return signal
    pad_left = window // 2
    pad_right = window - 1 - pad_left
    padded = np.pad(signal, (pad_left, pad_right), mode="edge")
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode="valid")


def segment_rate(signal_window: np.ndarray, time_window: np.ndarray):
    """Robust rate/direction for one candidate span: a least-squares slope
    over every sample, not a two-point (end - start) / duration difference.

    A two-point difference lives or dies on exactly two samples; if either
    lands on a noisy point in the running-gait cycle (arm swing/torso
    rotation shifting body_scale independent of real translation), a
    genuine sprint's measured rate can come out near zero. This hits
    hardest at the LAST leg of a clip, since its end is an arbitrary video
    cutoff, not a real turn-point extremum, so it has no reason to land on
    a "clean" phase of the gait cycle. A regression slope over the whole
    span uses all the data instead of two arbitrary points, so one noisy
    sample can't flip a real sprint into a false "rest" classification.
    """
    if len(time_window) < 2:
        return 0.0, 1
    slope = float(np.polyfit(time_window, signal_window, 1)[0])
    direction = 1 if slope >= 0 else -1
    return abs(slope), direction
