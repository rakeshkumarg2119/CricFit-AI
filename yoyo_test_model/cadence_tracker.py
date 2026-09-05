"""
CricFit AI - Yo-Yo Test Shuttle & Cadence Tracker  (v2 - redesigned)

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
  1. Tracks horizontal (x) ankle/hip position to find the two turn-lines and
     segment the clip into: running legs / turns / rest-walks.
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

DEFAULT_MODEL_PATH = "pose_landmarker_lite.task"

# --- test-structure constants (fixed by the Yo-Yo IR1 protocol itself) ---
SHUTTLE_LEG_M = 20.0          # one-way distance between the two lines
REST_WINDOW_SEC = 10.0        # mandatory recovery window between shuttles

# --- tuning knobs, same role as v1, re-tuned per motion axis ---
MIN_STEP_INTERVAL_SEC = 0.25
STEP_PEAK_PROMINENCE = 0.01      # for vertical ankle-bob (step detection)

# --- movement state-machine knobs (replaces old peak-based turn detection) ---
VELOCITY_SMOOTH_WINDOW_SEC = 0.3   # smooths frame noise before speed check
MOVING_VELOCITY_THRESHOLD = 0.05   # normalized-x units/sec - tune per camera
                                    # distance/framing: too low = rest counted
                                    # as running, too high = slow parts of a
                                    # real sprint get miscounted as resting
MIN_REST_DURATION_SEC = 1.5        # a "paused" stretch shorter than this is
                                    # just the cone turn, not the 10s recovery
MIN_LEG_DISPLACEMENT = 0.15        # normalized-x distance a "moving" segment
                                    # must cover to count as a real leg, not
                                    # camera jitter or a stumble-in-place

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
        self._ankle_x_series = []   # horizontal position, drives shuttle segmentation
        self._timestamps_sec = []
        self._closed = False

    def start(self):
        self._start_time = time.time()

    def process_frame(self, frame_bgr: np.ndarray, timestamp_ms: int = None) -> dict:
        if self._start_time is None:
            self.start()
        if timestamp_ms is None:
            timestamp_ms = int((time.time() - self._start_time) * 1000)

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            lm = result.pose_landmarks[0]
            avg_ankle_y = (lm[LEFT_ANKLE].y + lm[RIGHT_ANKLE].y) / 2.0
            # hip x is steadier than ankle x for tracking overall body travel
            avg_hip_x = (lm[LEFT_HIP].x + lm[RIGHT_HIP].x) / 2.0
            self._ankle_y_series.append(avg_ankle_y)
            self._ankle_x_series.append(avg_hip_x)
            self._timestamps_sec.append(timestamp_ms / 1000.0)

        return self._live_stats()

    def _estimated_fps(self) -> float:
        if len(self._timestamps_sec) < 2:
            return 30.0
        duration = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return (len(self._timestamps_sec) - 1) / duration if duration > 0 else 30.0

    def _live_stats(self) -> dict:
        if len(self._ankle_x_series) < 2:
            return {"legs_so_far": 0, "elapsed_sec": 0.0}
        legs, _ = self._segment_movement(np.array(self._ankle_x_series),
                                          np.array(self._timestamps_sec))
        elapsed = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return {
            "legs_so_far": len(legs),
            "elapsed_sec": round(float(elapsed), 1),
        }

    # ---- segmentation: velocity state-machine (moving vs paused) ----
    def _segment_movement(self, x_series: np.ndarray, timestamps: np.ndarray):
        """Classifies every frame as MOVING (real sprint) or PAUSED, using
        smoothed left-right velocity - not peak detection - so standing at
        a cone doesn't get mistaken for part of a run.

        Returns:
            legs:  list of (start_idx, end_idx, direction) for real running
                   stretches (direction: +1 or -1, whichever way x moved).
            rests: list of (start_idx, end_idx) for paused stretches long
                   enough to be the actual 10s recovery walk (short pauses
                   at the cone turn are dropped, not counted as rest).
        """
        n = len(x_series)
        if n < 3:
            return [], []

        fps = self._estimated_fps()
        raw_velocity = np.gradient(x_series, timestamps)
        smooth_frames = max(1, int(VELOCITY_SMOOTH_WINDOW_SEC * fps))
        if smooth_frames > 1:
            kernel = np.ones(smooth_frames) / smooth_frames
            velocity = np.convolve(raw_velocity, kernel, mode="same")
        else:
            velocity = raw_velocity

        moving_mask = np.abs(velocity) > MOVING_VELOCITY_THRESHOLD

        # collapse into contiguous same-state runs
        segments = []
        start = 0
        state = moving_mask[0]
        for i in range(1, n):
            if moving_mask[i] != state:
                segments.append((start, i, state))
                start = i
                state = moving_mask[i]
        segments.append((start, n, state))

        legs, rests = [], []
        for start_idx, end_idx, is_moving in segments:
            duration = timestamps[end_idx - 1] - timestamps[start_idx] if end_idx > start_idx else 0.0
            if is_moving:
                displacement = abs(x_series[end_idx - 1] - x_series[start_idx])
                if displacement >= MIN_LEG_DISPLACEMENT:
                    direction = 1 if np.mean(velocity[start_idx:end_idx]) > 0 else -1
                    legs.append((start_idx, end_idx, direction))
                # else: too little travel to be a real leg - drop as noise
            else:
                if duration >= MIN_REST_DURATION_SEC:
                    rests.append((start_idx, end_idx))
                # else: brief pause at the cone turn, not a real rest - drop
        return legs, rests

    def _cadence_in_range(self, start_idx, end_idx, y_series, timestamps, fps):
        """Step cadence computed ONLY within a running leg's frame range."""
        sub_y = y_series[start_idx:end_idx]
        sub_t = timestamps[start_idx:end_idx]
        if len(sub_y) < 3:
            return {"steps": 0, "cadence": 0.0, "duration_sec": 0.0}
        peaks, _ = find_peaks(
            -sub_y,
            distance=max(1, int(MIN_STEP_INTERVAL_SEC * fps)),
            prominence=STEP_PEAK_PROMINENCE,
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
        x_series = np.array(self._ankle_x_series)
        timestamps = np.array(self._timestamps_sec)
        fps = self._estimated_fps()

        legs, rests = self._segment_movement(x_series, timestamps) if len(x_series) >= 3 else ([], [])

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

        # rests are already isolated by the state machine (paused stretches
        # long enough to be a real 10s recovery walk, cone-turn pauses
        # already filtered out) - just report their durations directly.
        rest_gaps_sec = [round(float(timestamps[e - 1] - timestamps[s]), 2) for s, e in rests]

        rest_compliance = {
            "rest_gaps_sec": rest_gaps_sec,
            "all_within_10s": all(g <= REST_WINDOW_SEC + 0.5 for g in rest_gaps_sec) if rest_gaps_sec else None,
            "note": "gaps notably over 10s suggest the player was late back to "
                    "the line for that recovery window - flag for review, not "
                    "an automatic fail call.",
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
            "shuttle_metrics": {
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
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval_ms = int(1000 / fps)

    tracker = ShuttleCadenceTracker(model_path=model_path)
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        tracker.process_frame(frame, timestamp_ms=frame_idx * frame_interval_ms)
        frame_idx += 1
    cap.release()

    report = tracker.finalize(manual_input=manual_input, reference=reference)
    tracker.close()
    return report


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cadence_tracker.py <video_path>")
        sys.exit(1)

    result = analyze_video_file(
        sys.argv[1],
        manual_input={"yoyo_level": "16.3"},
        reference={"target_board": "BCCI", "target_yoyo_score": 17.1},
    )
    print(json.dumps(result, indent=2))