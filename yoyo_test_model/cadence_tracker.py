"""
CricFit AI - Yo-Yo Test Shuttle & Cadence Tracker  (v2.1)

WHY THIS WAS REWRITTEN
-----------------------
v1 modeled the Yo-Yo test as "player running in place" and tracked ankle
Y-position (vertical bob) for the whole clip, then divided total distance by
total time for an "avg speed", and split the whole clip into 3 equal TIME
windows to detect a fatigue trend.

That's wrong because a Yo-Yo test is NOT continuous running in place:
  - Player sprints 20m out, turns, sprints 20m back, then WALKS for a
    mandatory ~10s recovery, then the beep forces the next (faster) shuttle.
  - Speed is not constant - it increases every level. distance/time over the
    whole session is not a real pace, it's diluted by rest-walks.
  - "Fatigue" only makes sense compared shuttle-to-shuttle, not across
    arbitrary equal time-thirds that mix running and resting unevenly.

v2 instead:
  1. Tracks the player's **apparent body scale** (shoulder-to-hip distance in
     the frame) to find the two turn-lines and segment the clip into:
     running legs / turns / rest-walks. This works whether the camera is
     side-on (lateral motion) OR facing straight down the running lane
     (which is how most people naturally film it, phone in hand, standing
     at the start line) - body scale shrinks/grows as the player gets
     farther/closer regardless of which way they're actually moving in the
     frame, unlike raw horizontal position which only works side-on.
  2. Only computes step cadence (vertical bob) *inside* running legs.
  3. Groups legs into shuttles (out+back = 1 shuttle) and computes
     cadence/pace per shuttle, so trend = shuttle-over-shuttle, not
     arbitrary time-thirds.
  4. Flags rest-window compliance (real Yo-Yo tests fail you if you don't
     get back to the line before the 10s countdown ends).
  5. Does NOT compute a fake "avg_speed_mps" from manual distance/time.
     Distance/speed for a given level.shuttle score is looked up from the
     official Yo-Yo IR1 protocol table (Bangsbo, Iaia & Krustrup, 2008),
     see YOYO_IR1_LEVEL_TABLE below. Table covers scores up to 23.8/3640m;
     anything beyond that returns an explicit "outside tabulated range"
     note rather than a guess.
  6. Cross-checks the video-detected shuttle count against how many
     shuttles the reported score implies should have happened - catches
     clips that start mid-test or cut off early.

v2.1 CHANGES (bug fixes)
------------------------
  a. Rest-compliance direction was INVERTED. The beep schedule is
     40m / level-speed + 10s recovery, so a player at-or-above beep pace
     produces gaps >= ~10s. A gap notably UNDER 10s means the player was
     LATE back to the line (the violation); gaps OVER 10s are fine (early
     finisher idling until the next beep). Fixed the check + note.
  b. Recovery windows are now measured directly between the end of each
     back-leg and the start of the next out-leg. Previously they were taken
     from the segmentation 'rests' list, which also contained the idle wait
     before the first sprint, the tail after the last one, and cone-turn
     pauses - all of which polluted the compliance check.
  c. analyze_video_file() now raises a clear error if the video can't be
     opened, instead of silently producing a junk all-zeros report.
  d. Step-peak prominence is now adaptive per leg (scaled to that leg's own
     ankle-bob amplitude, with a floor), replacing the fixed default that
     needed per-clip manual tuning.
  e. Tracks how many frames had no detected pose and reports it - frames
     without a pose are excluded from all series, and a high drop rate
     explains downstream index/label mismatches.
  f. __main__ takes yoyo_level / target score as CLI args instead of
     hardcoded values.

v2.2 CHANGES (fixes real sprint frames being mislabeled RESTING)
------------------------------------------------------------------
Root cause found by reviewing yoyo_demo_whatsapp.mp4 frame-by-frame: the
overlay label was index-aligned correctly (that was already fixed in
v2.1), but the *segmentation itself* was misclassifying genuine sprinting
as rest, on both toward/away-camera and side-on footage:

  g. Turn-point detection was running on the same LIGHTLY-smoothed signal
     used for rate calculation. Running gait causes body_scale (and to a
     lesser extent hip_x) to wobble every stride - arm swing and torso
     rotation change the shoulder-hip projection independent of real
     distance/position change. That wobble was getting picked up by
     find_peaks() as fake turn-points mid-sprint, chopping one real leg
     into several short fragments, each too brief/low-displacement to
     clear LEG_AVG_RATE_THRESHOLD or MIN_LEG_DURATION_SEC on its own - so
     they fell through to "rest". This was worst early/close to camera,
     where gait wobble is a larger fraction of the frame than it is once
     the player is far away.
     Fix: turn-points are now found on a SEPARATE, more heavily smoothed
     copy of the signal (TURN_POINT_SMOOTH_WINDOW_SEC), with a minimum
     spacing between accepted peaks (TURN_POINT_MIN_SPACING_SEC) so gait
     noise can no longer register as a turn. The lightly-smoothed signal
     is still used for the actual rate/displacement math, so short real
     legs aren't blurred away either - two different smoothing windows
     for two different jobs, instead of one window trying to do both.
  h. Rate-per-candidate-segment was computed from just the two endpoint
     samples (displacement between a and b, divided by duration). A
     single noisy endpoint sample (mid-gait-cycle, arbitrary phase) could
     understate a real sprint's rate enough to fail the threshold - this
     hit hardest at the LAST segment before the clip ends, since that
     endpoint is an arbitrary video cutoff, not a real turn, so it's not
     an extremum and is more exposed to single-sample noise than an
     interior turn-point is.
     Fix: rate is now a least-squares slope over every sample in the
     candidate span (see _segment_rate), not a two-point difference - one
     noisy sample can no longer flip a real sprint into a false "rest".

Requires: opencv-python, mediapipe, numpy, scipy
Also requires pose_landmarker_lite.task in the working directory.
"""

import time
import json
from datetime import datetime, timezone

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from scipy.signal import find_peaks

LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12

DEFAULT_MODEL_PATH = "pose_landmarker_lite.task"

# --- test-structure constants (fixed by the Yo-Yo IR1 protocol itself) ---
SHUTTLE_LEG_M = 20.0          # one-way distance between the two lines
REST_WINDOW_SEC = 10.0        # mandatory recovery window between shuttles

# v2.1: how far under the 10s window a recovery gap can fall before it is
# counted as "late back to the line". Absorbs frame-quantization + pose
# jitter around the turn moment. NOT part of the official protocol - a
# measurement-noise allowance only.
LATE_TOLERANCE_SEC = 1.5

# --- tuning knobs, same role as v1, re-tuned per motion axis ---
MIN_STEP_INTERVAL_SEC = 0.25

# v2.1: replaces the old fixed STEP_PEAK_PROMINENCE (0.01), which needed
# per-clip manual tuning and produced 0-2 steps on real sprints when too
# high. Prominence is now scaled per leg to that leg's own ankle-bob
# amplitude (see _cadence_in_range); this floor only kicks in for legs with
# an almost-flat bob (e.g. very distant camera), where nothing meaningful
# can be detected anyway.
CADENCE_PROMINENCE_FLOOR = 0.004

# --- segmentation knobs (extrema + average-rate based - see _segment_movement) ---
SIGNAL_SMOOTH_WINDOW_SEC = 0.2     # LIGHT smoothing, just to stop landmark
                                    # jitter creating spurious tiny peaks -
                                    # deliberately much shorter than a real
                                    # leg (~1-1.5s). A wider window (v2's
                                    # original 0.6s, used for instantaneous
                                    # velocity thresholding) blurred real
                                    # legs below the moving threshold, which
                                    # was the actual cause of 0 legs detected
                                    # on real footage - fixed by dropping
                                    # instantaneous-velocity classification
                                    # entirely in favor of per-leg avg rate.

# v2.2: SEPARATE, heavier smoothing used ONLY to find turn-points (not for
# rate calc - see SIGNAL_SMOOTH_WINDOW_SEC above, which stays light so real
# short legs aren't blurred). This is v2's original 0.6s window, repurposed:
# it's fine for turn-point finding to blur across a stride-cycle (a real
# turn is one event lasting well over a full gait cycle), it was only wrong
# when used for the rate math itself.
TURN_POINT_SMOOTH_WINDOW_SEC = 0.6

# v2.2: minimum spacing (seconds) enforced between accepted turn-points via
# find_peaks(distance=...). A real out-leg or back-leg takes >= ~1s even at
# the fastest levels (see MIN_LEG_DURATION_SEC) - two "turns" closer than
# that are gait wobble, not two real direction changes, and were the main
# source of a real sprint getting chopped into rest-classified fragments.
TURN_POINT_MIN_SPACING_SEC = 1.0
LEG_AVG_RATE_THRESHOLD = 0.06      # body-scale units/sec, averaged over a
                                    # whole candidate leg (displacement /
                                    # duration) - NOT an instantaneous/
                                    # smoothed derivative. Distinguishes a
                                    # sprint leg from the slower rest-walk
                                    # between two turn points, both of which
                                    # are found the same way (local extrema
                                    # of body_scale). Tune per camera
                                    # distance/framing: too low = rest-walk
                                    # counted as a leg, too high = a genuine
                                    # but shorter/farther-out leg misses it.
MIN_REST_DURATION_SEC = 1.5        # a "paused" stretch shorter than this is
                                    # just the cone turn, not the 10s recovery
MIN_LEG_DISPLACEMENT = 0.03        # body-scale distance a "moving" segment
                                    # must cover to count as a real leg, not
                                    # camera jitter or a stumble-in-place -
                                    # smaller than the old x-position value
                                    # since torso-length change per leg is a
                                    # smaller quantity than a full-frame
                                    # horizontal traverse
MIN_LEG_DURATION_SEC = 1.0          # a real 20m sprint leg takes at least
                                    # ~1-1.5s even at the fastest levels -
                                    # anything shorter that still cleared the
                                    # displacement check is a noise blip, not
                                    # an actual leg. This is what was missing
                                    # before: displacement alone let a brief
                                    # jittery spike count as a "leg" even
                                    # though no real runner moves that fast

# Yo-Yo IR1 protocol table, adapted from Bangsbo, Iaia & Krustrup (2008),
# "The Yo-Yo Intermittent Recovery Test: A Useful Tool for Evaluation of
# Physical Performance in Intermittent Sports", Sports Med 38(1):37-51.
# Each speed level has N shuttles (2 x 20m each) at a fixed speed before the
# next speed step. The reported score "16.3" means speed level 16, 3rd
# shuttle at that speed -> keyed here as (speed_level, shuttle_in_level).
_YOYO_IR1_SPEED_STAGES = [
    # (speed_level, shuttles_in_level, speed_kmh)
    (5, 1, 10.0),
    (9, 1, 12.0),
    (11, 2, 13.0),
    (12, 3, 13.5),
    (13, 4, 14.0),
    (14, 8, 14.5),
    (15, 8, 15.0),
    (16, 8, 15.5),
    (17, 8, 16.0),
    (18, 8, 16.5),
    (19, 8, 17.0),
    (20, 8, 17.5),
    (21, 8, 18.0),
    (22, 8, 18.5),
    (23, 8, 19.0),
]

def _build_yoyo_ir1_table():
    table = {}
    global_shuttle_count = 0
    for speed_level, n_shuttles, speed_kmh in _YOYO_IR1_SPEED_STAGES:
        for shuttle_in_level in range(1, n_shuttles + 1):
            global_shuttle_count += 1
            table[(speed_level, shuttle_in_level)] = {
                "speed_kmh": speed_kmh,
                "distance_m": global_shuttle_count * 40,  # 2 x 20m per shuttle
                "cumulative_shuttle_number": global_shuttle_count,
            }
    return table

YOYO_IR1_LEVEL_TABLE = _build_yoyo_ir1_table()
# Table covers up to score 23.8 / 3640m (elite-range). Scores beyond that
# aren't in the published protocol table and will return a "beyond tabulated
# range" note rather than a guessed number.


def _parse_level_shuttle(yoyo_level: str):
    """'16.3' -> (16, 3). Returns None if it doesn't parse as level.shuttle."""
    try:
        text = str(yoyo_level).strip()
        speed_level_str, shuttle_str = text.split(".")
        return int(speed_level_str), int(shuttle_str)
    except (ValueError, AttributeError):
        return None


def _lookup_level_reference(yoyo_level: str):
    """Looks up speed/distance for a reported level.shuttle score against the
    Yo-Yo IR1 protocol table. Returns explicit None + note on anything that
    doesn't resolve, rather than guessing."""
    if yoyo_level is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None, "note": "no yoyo_level given"}

    parsed = _parse_level_shuttle(yoyo_level)
    if parsed is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None,
                "note": f"'{yoyo_level}' isn't in level.shuttle format (e.g. '16.3')"}

    entry = YOYO_IR1_LEVEL_TABLE.get(parsed)
    if entry is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None,
                "note": f"score {yoyo_level} is outside the tabulated YYIR1 "
                        f"range (table covers up to 23.8 / 3640m) - "
                        f"double check the reported score"}
    return {**entry, "note": None}


class ShuttleCadenceTracker:
    """
    Feed it frames (live or looped over a video), then call finalize() once
    the test session is over.

    Unlike v1, this does NOT assume continuous in-place running: it segments
    the session into running legs / turns / rest-walks first, and only
    reports cadence for the running legs.

    Note: frames where MediaPipe finds no pose are skipped entirely - all
    internal series (timestamps included) are indexed by DETECTED frames,
    not by raw video frames. Anything indexing into these series must count
    detected frames, not raw frame numbers.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._start_time = None
        self._ankle_y_series = []
        self._hip_x_series = []        # horizontal position - informative for
                                        # side-on filming (lateral runs)
        self._body_scale_series = []   # apparent body size - informative for
                                        # end-on filming (toward/away runs)
        self._timestamps_sec = []
        self._frames_processed = 0     # v2.1: all frames fed in, pose or not
        self._closed = False
        self._last_signal_used = None

    def start(self):
        self._start_time = time.time()

    def process_frame(self, frame_bgr: np.ndarray, timestamp_ms: int = None) -> dict:
        if self._start_time is None:
            self.start()
        if timestamp_ms is None:
            timestamp_ms = int((time.time() - self._start_time) * 1000)

        # v2.1: count every frame fed in, so finalize() can report the
        # pose-detection drop rate.
        self._frames_processed += 1

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            lm = result.pose_landmarks[0]
            avg_ankle_y = (lm[LEFT_ANKLE].y + lm[RIGHT_ANKLE].y) / 2.0
            avg_hip_x = (lm[LEFT_HIP].x + lm[RIGHT_HIP].x) / 2.0
            # torso length (shoulder-to-hip distance) as a proxy for distance
            # from camera: shrinks as the player runs away, grows as they run
            # toward the camera. Track both this and hip-x - whichever one
            # actually varies over the session tells us which way the camera
            # was pointed, without needing to ask upfront.
            left_torso = np.hypot(lm[LEFT_SHOULDER].x - lm[LEFT_HIP].x,
                                   lm[LEFT_SHOULDER].y - lm[LEFT_HIP].y)
            right_torso = np.hypot(lm[RIGHT_SHOULDER].x - lm[RIGHT_HIP].x,
                                    lm[RIGHT_SHOULDER].y - lm[RIGHT_HIP].y)
            body_scale = (left_torso + right_torso) / 2.0
            self._ankle_y_series.append(avg_ankle_y)
            self._hip_x_series.append(avg_hip_x)
            self._body_scale_series.append(body_scale)
            self._timestamps_sec.append(timestamp_ms / 1000.0)

        return self._live_stats()

    def _select_motion_signal(self) -> np.ndarray:
        """Picks whichever tracked signal (hip-x or body-scale) actually
        shows real movement over the session, so the same code handles
        side-on footage (hip-x varies) and end-on footage - camera facing
        down the running lane (body-scale varies) without needing to be
        told which one was used to film."""
        x = np.array(self._hip_x_series)
        scale = np.array(self._body_scale_series)
        if len(x) < 3:
            return x
        # normalize each to its own typical size so a comparison across the
        # two different units (frame-width fraction vs torso-length fraction)
        # is fair, then use whichever has the larger overall swing.
        x_range = np.ptp(x) / (np.mean(x) + 1e-6)
        scale_range = np.ptp(scale) / (np.mean(scale) + 1e-6)
        self._last_signal_used = "hip_x (side-on)" if x_range >= scale_range else "body_scale (toward/away)"
        return x if x_range >= scale_range else scale

    def _estimated_fps(self) -> float:
        if len(self._timestamps_sec) < 2:
            return 30.0
        duration = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return (len(self._timestamps_sec) - 1) / duration if duration > 0 else 30.0

    def _live_stats(self) -> dict:
        if len(self._body_scale_series) < 2:
            return {"legs_so_far": 0, "elapsed_sec": 0.0}
        signal = self._select_motion_signal()
        legs, _ = self._segment_movement(signal, np.array(self._timestamps_sec))
        elapsed = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return {
            "legs_so_far": len(legs),
            "elapsed_sec": round(float(elapsed), 1),
        }

    # v2.2: robust rate/direction for one candidate span, replacing the old
    # (smoothed[b] - smoothed[a]) / duration two-point difference. A
    # two-point difference lives or dies on exactly two samples; if either
    # one lands on a noisy point in the running-gait cycle (arm swing/torso
    # rotation shifting body_scale independent of real translation), a
    # genuine sprint's measured rate can come out near zero. This hit the
    # LAST leg of a clip hardest, since its end (n-1) is an arbitrary video
    # cutoff, not a real turn-point extremum, so it has no reason to land on
    # a "clean" phase of the gait cycle the way a detected extremum usually
    # does. A least-squares slope over every sample in the span uses all the
    # data instead of two arbitrary points, so one noisy sample can't flip a
    # real sprint into a false "rest" classification.
    def _segment_rate(self, signal_window: np.ndarray, time_window: np.ndarray):
        if len(time_window) < 2:
            return 0.0, 1
        slope = float(np.polyfit(time_window, signal_window, 1)[0])
        direction = 1 if slope >= 0 else -1
        return abs(slope), direction

    # v2.2: a REST->next-leg boundary is a SPEED change, not a DIRECTION
    # change (the player already turned at the far/near line; the rest-walk
    # continues a beat in roughly the same heading as the sprint that
    # follows it). Pure extrema detection can only ever find direction
    # reversals, so this boundary never shows up as a turn-point - a long
    # rest is followed immediately by a real leg with no extremum between
    # them, and the two get evaluated together as one span whose average
    # rate is diluted below LEG_AVG_RATE_THRESHOLD by the rest portion, so
    # a genuine sprint at the end of that span was falling through to
    # "rest" entirely undetected. Confirmed against synthetic
    # rest-then-sprint data before shipping this - see debugging notes.
    # This scans a span that failed the whole-span rate test for a point
    # where a trailing sub-window's rate clears the threshold and stays
    # cleared through the end of the span, and returns that as a synthetic
    # split point.
    def _refine_span(self, a, b, smoothed, timestamps, fps):
        duration = timestamps[b] - timestamps[a]
        if duration < 2 * MIN_LEG_DURATION_SEC:
            return None
        win = max(2, int(MIN_LEG_DURATION_SEC * fps))
        step = max(1, win // 4)
        for start in range(a, b - win, step):
            end = start + win
            window_rate, _ = self._segment_rate(smoothed[start:end + 1], timestamps[start:end + 1])
            if window_rate < LEG_AVG_RATE_THRESHOLD:
                continue
            # require the fast rate to hold to the END of the span too, not
            # just in one window - otherwise a brief noise blip mid-rest
            # would falsely split it. 0.7x tolerance absorbs a real
            # deceleration into a turn or the video's tail cutoff.
            tail_rate, _ = self._segment_rate(smoothed[start:b + 1], timestamps[start:b + 1])
            if tail_rate >= LEG_AVG_RATE_THRESHOLD * 0.7:
                return start
        return None

    # v2.2: edge-safe moving average. Plain np.convolve(..., mode="same")
    # implicitly zero-pads past the array boundary, which drags the
    # smoothed value toward 0 for roughly the last half-window of samples -
    # exactly where the LAST leg of a clip lives (video just ends there,
    # no closing turn). That artificial pull created a fake extremum right
    # at the tail in testing, chopping the final real leg into slivers too
    # short to pass MIN_LEG_DURATION_SEC. Edge-padding with the boundary
    # value itself (not zero) removes that artifact.
    @staticmethod
    def _smooth(signal, window):
        if window <= 1:
            return signal
        pad_left = window // 2
        pad_right = window - 1 - pad_left
        padded = np.pad(signal, (pad_left, pad_right), mode="edge")
        kernel = np.ones(window) / window
        return np.convolve(padded, kernel, mode="valid")

    # ---- segmentation: turnaround (extrema) + average-rate classification ----
    def _segment_movement(self, scale_series: np.ndarray, timestamps: np.ndarray):
        """Finds every turnaround (local peak/trough) in body-scale directly
        - each one IS a turn-line moment, by definition, whether it's the
        far cone or the near start/finish line - then classifies each
        monotonic stretch between consecutive turnarounds as a running leg
        or a rest-walk by its AVERAGE rate (displacement / duration), not an
        instantaneous/smoothed derivative.

        This replaces an earlier velocity-threshold state machine that had
        two compounding problems on real footage: (1) a real leg is often
        only ~1-1.5s peak-to-trough, comparable to or shorter than the
        smoothing window needed to quiet landmark jitter, so smoothing
        diluted real sprint velocity below the "moving" threshold and whole
        legs were misread as rest/noise; and (2) when a leg WAS detected as
        one continuous "moving" stretch, validating it by start-vs-end
        displacement broke for any stretch containing more than one
        turnaround (e.g. a quick cone turn with no full stop) - an out-leg
        and back-leg roughly cancel out, so the pair failed the displacement
        check and got dropped entirely. Extrema-based splitting can't
        conflate two legs (each candidate is monotonic by construction), and
        average-rate classification isn't diluted by smoothing the way an
        instantaneous derivative is.

        `scale_series` is apparent body size (shoulder-to-hip distance),
        not position - this makes segmentation work whether the camera is
        side-on or facing straight down the running lane (the far more
        common real-world setup).

        See _segment_rate() for how a candidate span's rate/direction is now
        computed (v2.2 - regression slope, not a two-point difference).

        Returns:
            legs:  list of (start_idx, end_idx, direction) for real running
                   stretches (direction: +1 = getting farther/smaller,
                   -1 = getting closer/bigger - whichever way the run went).
            rests: list of (start_idx, end_idx) for stretches too slow to be
                   a leg but long enough to be the actual 10s recovery walk
                   (brief cone-turn pauses are dropped as noise, not
                   counted as rest).

        v2.1 note: `rests` may also include the idle wait BEFORE the first
        sprint and the tail AFTER the last one (both are slow stretches too).
        That's fine for plotting/diagnostics, but compliance reporting no
        longer uses this list - see finalize(), which measures recovery
        windows directly between leg boundaries instead.
        """
        n = len(scale_series)
        if n < 3:
            return [], []

        fps = self._estimated_fps()

        # v2.2: LIGHT smoothing (rate/displacement math) - unchanged from
        # v2.1, deliberately short so it doesn't blur a real short leg.
        smooth_frames = max(1, int(SIGNAL_SMOOTH_WINDOW_SEC * fps))
        smoothed = self._smooth(scale_series, smooth_frames)

        # v2.2: SEPARATE, heavier smoothing used ONLY to locate turn-points.
        # Running gait (arm swing / torso rotation) wobbles body_scale and
        # hip_x every stride - on the light-smoothed signal that wobble was
        # getting picked up as fake turn-points mid-sprint, chopping one
        # real leg into several fragments too short/slow to individually
        # clear LEG_AVG_RATE_THRESHOLD or MIN_LEG_DURATION_SEC, so a genuine
        # sprint kept falling through to "rest". A real turn is one event
        # spanning well over a full gait cycle, so it's safe to blur across
        # strides when just LOOKING for turns, even though that same
        # blurring would be wrong for the rate math itself.
        turn_smooth_frames = max(1, int(TURN_POINT_SMOOTH_WINDOW_SEC * fps))
        turn_signal = self._smooth(scale_series, turn_smooth_frames)

        min_spacing_frames = max(1, int(TURN_POINT_MIN_SPACING_SEC * fps))
        max_idx, _ = find_peaks(turn_signal, prominence=MIN_LEG_DISPLACEMENT,
                                 distance=min_spacing_frames)
        min_idx, _ = find_peaks(-turn_signal, prominence=MIN_LEG_DISPLACEMENT,
                                 distance=min_spacing_frames)
        turn_points = sorted(set([0, n - 1]) | set(max_idx.tolist()) | set(min_idx.tolist()))

        legs = []
        for a, b in zip(turn_points[:-1], turn_points[1:]):
            duration = timestamps[b] - timestamps[a]
            rate, direction = self._segment_rate(smoothed[a:b + 1], timestamps[a:b + 1])
            if rate >= LEG_AVG_RATE_THRESHOLD and duration >= MIN_LEG_DURATION_SEC:
                legs.append((a, b, direction))
                continue
            # v2.2: whole-span average failed, but a long span can be a
            # REST followed by a genuine same-direction LEG with no
            # extremum at the boundary between them (see _refine_span).
            # Only worth checking spans well longer than one real leg -
            # a short rejected fragment is just noise, not a hidden leg.
            split = self._refine_span(a, b, smoothed, timestamps, fps)
            if split is not None:
                sub_duration = timestamps[b] - timestamps[split]
                sub_rate, sub_direction = self._segment_rate(
                    smoothed[split:b + 1], timestamps[split:b + 1])
                if sub_rate >= LEG_AVG_RATE_THRESHOLD and sub_duration >= MIN_LEG_DURATION_SEC:
                    legs.append((split, b, sub_direction))
            # else: not fast/sustained enough to be a leg on its own - see
            # below for how the resulting gap is judged, rather than judging
            # this one fragment in isolation.

        # Rests are judged on the GAP BETWEEN accepted legs, not on any one
        # inter-extrema fragment in isolation. A real ~2-3s turn/recovery
        # pause is rarely perfectly still - a bit of wobble while turning
        # creates a few small extrema inside it, each too brief on its own
        # to clear MIN_REST_DURATION_SEC. Testing each fragment individually
        # (the earlier approach) silently dropped the whole pause instead of
        # reporting it as rest. Testing the full span between legs fixes
        # this regardless of how it's internally fragmented.
        rests = []
        prev_end = 0
        for leg_start, leg_end, _ in legs:
            if leg_start > prev_end:
                gap_duration = timestamps[leg_start] - timestamps[prev_end]
                if gap_duration >= MIN_REST_DURATION_SEC:
                    rests.append((prev_end, leg_start))
            prev_end = leg_end
        if n - 1 > prev_end:
            gap_duration = timestamps[n - 1] - timestamps[prev_end]
            if gap_duration >= MIN_REST_DURATION_SEC:
                rests.append((prev_end, n - 1))

        return legs, rests

    def _cadence_in_range(self, start_idx, end_idx, y_series, timestamps, fps):
        """Step cadence computed ONLY within a running leg's frame range.

        v2.1: peak prominence is now ADAPTIVE - scaled to this leg's own
        ankle-bob amplitude instead of a fixed constant. A clean periodic
        bob has peak prominence of roughly half its peak-to-peak swing, so
        0.4 x ptp is slightly conservative and auto-tunes to camera
        distance and running speed. The floor only matters for legs with a
        nearly-flat bob (very distant camera), where nothing detectable
        exists anyway."""
        sub_y = y_series[start_idx:end_idx]
        sub_t = timestamps[start_idx:end_idx]
        if len(sub_y) < 3:
            return {"steps": 0, "cadence": 0.0, "duration_sec": 0.0}

        prominence = max(CADENCE_PROMINENCE_FLOOR, 0.4 * float(np.ptp(sub_y)))

        peaks, _ = find_peaks(
            -sub_y,
            distance=max(1, int(MIN_STEP_INTERVAL_SEC * fps)),
            prominence=prominence,
        )
        duration = sub_t[-1] - sub_t[0] if len(sub_t) > 1 else 1.0
        cadence = len(peaks) / duration if duration > 0 else 0.0
        return {
            "steps": int(len(peaks)),
            "cadence": round(float(cadence), 2),
            "duration_sec": round(float(duration), 2),
        }

    def finalize(self, manual_input: dict, reference: dict = None) -> dict:
        """
        manual_input: {"yoyo_level": "16.3"}  (the reported level.shuttle score
                      the test administrator/app already recorded - NOT
                      distance_m/time_sec, since those aren't independently
                      meaningful for this test, see module docstring).
                      Optional "measured_test_duration_sec" for a sanity
                      cross-check against how long the clip actually ran.
        reference:    optional dict, e.g. {"target_board": "BCCI",
                      "target_yoyo_score": 17.1}
        """
        y_series = np.array(self._ankle_y_series)
        signal = self._select_motion_signal()
        timestamps = np.array(self._timestamps_sec)
        fps = self._estimated_fps()

        # v2.1: rests are no longer consumed here (compliance is measured
        # directly from leg boundaries below); they remain available from
        # _segment_movement for plotting/diagnostics.
        legs, _ = self._segment_movement(signal, timestamps) if len(signal) >= 3 else ([], [])

        # pair consecutive legs into shuttles (out + back = 1 shuttle);
        # an odd leg left over at the end (test cut off mid-shuttle) is kept
        # as a partial and flagged, not silently merged or dropped.
        shuttle_reports = []
        direction_anomaly = False
        for i in range(0, len(legs) - 1, 2):
            out_leg, back_leg = legs[i], legs[i + 1]
            if out_leg[2] == back_leg[2]:
                # two legs in a row went the same direction - segmentation
                # likely split one real leg into two (e.g. a mid-sprint
                # stumble briefly dropped below the speed threshold)
                direction_anomaly = True
            out_stats = self._cadence_in_range(out_leg[0], out_leg[1], y_series, timestamps, fps)
            back_stats = self._cadence_in_range(back_leg[0], back_leg[1], y_series, timestamps, fps)
            shuttle_reports.append({
                "shuttle_index": len(shuttle_reports) + 1,
                "out_leg": out_stats,
                "back_leg": back_stats,
                "combined_cadence": round(
                    (out_stats["cadence"] + back_stats["cadence"]) / 2, 2
                ),
            })

        partial_leg_flag = (len(legs) % 2 == 1)

        # v2.1: recovery windows are measured directly between the end of
        # each back-leg and the start of the next out-leg. This skips cone
        # turns (out->back gaps), the idle wait before the first sprint, and
        # the tail after the last one - none of which are recoveries.
        #
        # Direction of the check: the beep schedule is 40m / level-speed +
        # 10s recovery, so a player running at-or-above beep pace produces
        # gaps >= ~10s. A gap notably UNDER 10s means the player was LATE
        # back to the line and cut into the mandatory recovery - that's the
        # violation. Gaps OVER 10s are fine: the player finished that
        # shuttle faster than beep pace and idled until the next beep.
        rest_gaps_sec = [
            round(float(timestamps[legs[i + 1][0]] - timestamps[legs[i][1]]), 2)
            for i in range(1, len(legs) - 1, 2)
        ]
        late_recoveries = [g for g in rest_gaps_sec if g < REST_WINDOW_SEC - LATE_TOLERANCE_SEC]

        rest_compliance = {
            "rest_gaps_sec": rest_gaps_sec,
            "late_recovery_count": len(late_recoveries),
            "all_recoveries_ok": (len(late_recoveries) == 0) if rest_gaps_sec else None,
            "note": "Gaps notably UNDER 10s mean the player was late back to "
                    "the line and cut into the mandatory recovery - flag for "
                    "review, not an automatic fail call. Gaps OVER 10s are "
                    "NOT a violation: the player finished that shuttle faster "
                    "than beep pace and idled until the next beep.",
        }

        if len(shuttle_reports) >= 2:
            first_cadence = shuttle_reports[0]["combined_cadence"]
            last_cadence = shuttle_reports[-1]["combined_cadence"]
            if last_cadence < first_cadence * 0.9:
                trend = "declining"
            elif last_cadence > first_cadence * 1.1:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        yoyo_level = manual_input.get("yoyo_level")
        measured_duration = manual_input.get("measured_test_duration_sec")
        video_duration = round(float(timestamps[-1] - timestamps[0]), 1) if len(timestamps) > 1 else 0.0

        duration_cross_check = None
        if measured_duration is not None and video_duration > 0:
            duration_cross_check = {
                "measured_test_duration_sec": measured_duration,
                "video_analyzed_duration_sec": video_duration,
                "discrepancy_sec": round(float(measured_duration - video_duration), 1),
            }

        level_reference = _lookup_level_reference(yoyo_level)
        shuttle_count_cross_check = None
        expected_shuttles = level_reference.get("cumulative_shuttle_number")
        if expected_shuttles is not None:
            detected = len(shuttle_reports)
            shuttle_count_cross_check = {
                "expected_from_reported_score": expected_shuttles,
                "detected_in_video": detected,
                "note": (
                    "video shuttle count is lower than expected - clip likely "
                    "starts mid-test or misses some reps"
                    if detected < expected_shuttles else
                    "video shuttle count exceeds expected - check the reported "
                    "score, or the clip includes warm-up shuttles before the "
                    "test proper started"
                    if detected > expected_shuttles else
                    "matches reported score"
                ),
            }

        # v2.1: report the pose-detection drop rate. All series (and every
        # index derived from them) refer to DETECTED frames only; a high
        # drop count explains misaligned overlays and short/patchy signals.
        pose_detection = {
            "frames_processed": self._frames_processed,
            "frames_with_pose": len(self._timestamps_sec),
            "frames_without_pose": self._frames_processed - len(self._timestamps_sec),
        }

        reference = reference or {}
        target_score = reference.get("target_yoyo_score")
        comparison = {"meets_target": None, "gap_to_target": None}
        if target_score is not None and yoyo_level is not None:
            try:
                # NOTE: level.shuttle notation (e.g. 16.8) compares correctly
                # as a plain float as long as shuttle count per level stays
                # single-digit (true for the standard IR1 protocol). This is
                # intentional, not an oversight - don't "fix" it into a
                # separate level/shuttle split unless the protocol changes.
                current_numeric = float(yoyo_level)
                target_numeric = float(target_score)
                comparison["meets_target"] = current_numeric >= target_numeric
                comparison["gap_to_target"] = round(target_numeric - current_numeric, 2)
            except (TypeError, ValueError):
                pass

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "manual_input": {
                "yoyo_level": yoyo_level,
                "duration_cross_check": duration_cross_check,
            },
            "level_reference": level_reference,
            "shuttle_count_cross_check": shuttle_count_cross_check,
            "pose_detection": pose_detection,
            "shuttle_metrics": {
                "motion_signal_used": self._last_signal_used,
                "shuttles_detected": len(shuttle_reports),
                "partial_leg_at_end": partial_leg_flag,
                "direction_anomaly_detected": direction_anomaly,
                "cadence_trend": trend,
                "shuttles": shuttle_reports,
            },
            "rest_compliance": rest_compliance,
            "reference": reference,
            "comparison": comparison,
        }
        return report

    def close(self):
        if not self._closed:
            self._landmarker.close()
            self._closed = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def analyze_video_file(video_path: str, manual_input: dict, reference: dict = None,
                        model_path: str = DEFAULT_MODEL_PATH) -> dict:
    cap = cv2.VideoCapture(video_path)
    # v2.1: fail loudly on an unopenable file instead of silently producing
    # an all-zeros "insufficient_data" report.
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval_ms = int(1000 / fps)

    tracker = ShuttleCadenceTracker(model_path=model_path)
    try:
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            tracker.process_frame(frame, timestamp_ms=frame_idx * frame_interval_ms)
            frame_idx += 1
    finally:
        cap.release()

    report = tracker.finalize(manual_input=manual_input, reference=reference)
    tracker.close()
    return report


if __name__ == "__main__":
    import sys
    # v2.1: yoyo_level and target score are CLI args, not hardcoded values.
    if len(sys.argv) < 2:
        print("Usage: python cadence_tracker.py <video_path> [yoyo_level] [target_score]")
        print("       e.g. python cadence_tracker.py test.mp4 16.3 17.1")
        sys.exit(1)

    video_arg = sys.argv[1]
    level_arg = sys.argv[2] if len(sys.argv) > 2 else "16.3"
    target_arg = sys.argv[3] if len(sys.argv) > 3 else "17.1"

    result = analyze_video_file(
        video_arg,
        manual_input={"yoyo_level": level_arg},
        reference={"target_board": "BCCI", "target_yoyo_score": float(target_arg)},
    )
    print(json.dumps(result, indent=2))