"""
Splits a session's motion signal (body_scale or hip_x) into running legs and
rest-walks. This is the core "where are the sprints" logic - kept isolated
from pose capture and cadence counting so it can be tested/tuned on its own
(see the synthetic-signal tests used to validate this before shipping).
"""

import numpy as np
from scipy.signal import find_peaks

from . import config
from .signal_utils import smooth, segment_rate


def _refine_span(a, b, smoothed, timestamps, fps):
    """A REST->next-leg boundary is a SPEED change, not a DIRECTION change
    (the player already turned at the far/near line; the rest-walk
    continues a beat in roughly the same heading as the sprint that follows
    it). Pure extrema detection can only ever find direction reversals, so
    this boundary never shows up as a turn-point - a long rest immediately
    followed by a real leg gets evaluated as one span whose average rate is
    diluted below LEG_AVG_RATE_THRESHOLD by the rest portion, so a genuine
    sprint at the end of that span falls through to "rest" entirely
    undetected. Confirmed against synthetic rest-then-sprint data before
    shipping this.

    Scans a span that failed the whole-span rate test for a point where a
    trailing sub-window's rate clears the threshold and stays cleared
    through the end of the span, and returns that as a synthetic split
    point.
    """
    duration = timestamps[b] - timestamps[a]
    if duration < 2 * config.MIN_LEG_DURATION_SEC:
        return None
    win = max(2, int(config.MIN_LEG_DURATION_SEC * fps))
    step = max(1, win // 4)
    for start in range(a, b - win, step):
        end = start + win
        window_rate, _ = segment_rate(smoothed[start:end + 1], timestamps[start:end + 1])
        if window_rate < config.LEG_AVG_RATE_THRESHOLD:
            continue
        # require the fast rate to hold to the END of the span too, not
        # just in one window - otherwise a brief noise blip mid-rest would
        # falsely split it. 0.7x tolerance absorbs a real deceleration into
        # a turn or the video's tail cutoff.
        tail_rate, _ = segment_rate(smoothed[start:b + 1], timestamps[start:b + 1])
        if tail_rate >= config.LEG_AVG_RATE_THRESHOLD * 0.7:
            return start
    return None


def segment_movement(scale_series: np.ndarray, timestamps: np.ndarray, fps: float):
    """Finds every turnaround (local peak/trough) in the motion signal -
    each one IS a turn-line moment, whether it's the far cone or the near
    start/finish line - then classifies each monotonic stretch between
    consecutive turnarounds as a running leg or a rest-walk by its AVERAGE
    rate (displacement / duration), not an instantaneous/smoothed
    derivative.

    `scale_series` is apparent body size (shoulder-to-hip distance) or
    hip-x, whichever the caller picked as the dominant signal - this makes
    segmentation work whether the camera is side-on or facing straight down
    the running lane.

    Returns:
        legs:  list of (start_idx, end_idx, direction) for real running
               stretches (direction: +1/-1, whichever way the run went).
        rests: list of (start_idx, end_idx) for stretches too slow to be a
               leg but long enough to be a real recovery walk (brief
               cone-turn pauses are dropped as noise, not counted as rest).

    Note: `rests` may also include the idle wait before the first sprint
    and the tail after the last one. Fine for plotting/diagnostics; the
    caller (report.py) measures actual recovery-window compliance directly
    from leg boundaries instead of from this list.
    """
    n = len(scale_series)
    if n < 3:
        return [], []

    # LIGHT smoothing for rate/displacement math - deliberately short so it
    # doesn't blur a real short leg.
    smooth_frames = max(1, int(config.SIGNAL_SMOOTH_WINDOW_SEC * fps))
    smoothed = smooth(scale_series, smooth_frames)

    # SEPARATE, heavier smoothing used ONLY to locate turn-points - see
    # config.py for why these need to be different windows.
    turn_smooth_frames = max(1, int(config.TURN_POINT_SMOOTH_WINDOW_SEC * fps))
    turn_signal = smooth(scale_series, turn_smooth_frames)

    min_spacing_frames = max(1, int(config.TURN_POINT_MIN_SPACING_SEC * fps))
    max_idx, _ = find_peaks(turn_signal, prominence=config.MIN_LEG_DISPLACEMENT,
                             distance=min_spacing_frames)
    min_idx, _ = find_peaks(-turn_signal, prominence=config.MIN_LEG_DISPLACEMENT,
                             distance=min_spacing_frames)
    turn_points = sorted(set([0, n - 1]) | set(max_idx.tolist()) | set(min_idx.tolist()))

    legs = []
    for a, b in zip(turn_points[:-1], turn_points[1:]):
        duration = timestamps[b] - timestamps[a]
        rate, direction = segment_rate(smoothed[a:b + 1], timestamps[a:b + 1])
        if rate >= config.LEG_AVG_RATE_THRESHOLD and duration >= config.MIN_LEG_DURATION_SEC:
            legs.append((a, b, direction))
            continue
        # whole-span average failed, but a long span can be a REST followed
        # by a genuine same-direction LEG with no extremum at the boundary
        # between them - only worth checking spans well longer than one
        # real leg, a short rejected fragment is just noise.
        split = _refine_span(a, b, smoothed, timestamps, fps)
        if split is not None:
            sub_duration = timestamps[b] - timestamps[split]
            sub_rate, sub_direction = segment_rate(smoothed[split:b + 1], timestamps[split:b + 1])
            if sub_rate >= config.LEG_AVG_RATE_THRESHOLD and sub_duration >= config.MIN_LEG_DURATION_SEC:
                legs.append((split, b, sub_direction))
        # else: not fast/sustained enough to be a leg on its own.

    # Rests are judged on the GAP BETWEEN accepted legs, not on any one
    # inter-extrema fragment in isolation - a real turn/recovery pause is
    # rarely perfectly still, and testing each internal fragment
    # individually can silently drop the whole pause instead of reporting
    # it as rest.
    rests = []
    prev_end = 0
    for leg_start, leg_end, _ in legs:
        if leg_start > prev_end:
            gap_duration = timestamps[leg_start] - timestamps[prev_end]
            if gap_duration >= config.MIN_REST_DURATION_SEC:
                rests.append((prev_end, leg_start))
        prev_end = leg_end
    if n - 1 > prev_end:
        gap_duration = timestamps[n - 1] - timestamps[prev_end]
        if gap_duration >= config.MIN_REST_DURATION_SEC:
            rests.append((prev_end, n - 1))

    return legs, rests
