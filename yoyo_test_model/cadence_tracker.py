"""
CricFit AI - Yo-Yo Test Cadence Tracker

Ported from the validated Colab notebook (yoyo_cadence_pipeline.ipynb).
Wraps MediaPipe PoseLandmarker (Tasks API) to track ankle y-position and
compute running cadence (steps/sec).

Two ways to use it:

1) LIVE / BACKEND INTEGRATION (for the FastAPI teammate):
    tracker = CadenceTracker()
    tracker.start()

    # for each incoming frame from the websocket (as a decoded BGR numpy array):
    live_stats = tracker.process_frame(frame)
    # live_stats = {"steps_so_far": int, "live_cadence": float, "elapsed_sec": float}
    # -> send this back over the socket for a live counter in the UI, if wanted

    # once the test session ends:
    report = tracker.finalize(
        manual_input={"distance_m": 400.0, "time_sec": 480.0, "yoyo_level": "16.3"},
        reference={"target_board": "BCCI", "target_yoyo_score": 17.1},
    )
    tracker.close()
    # `report` is the exact JSON structure to send to Groq

2) OFFLINE TESTING (matches the notebook, for validating on a saved clip):
    report = analyze_video_file("clip.mp4", manual_input={...}, reference={...})

Requires: opencv-python, mediapipe, numpy, scipy
Also requires pose_landmarker_lite.task in the working directory (or pass model_path).
Download it with:
    wget -O pose_landmarker_lite.task \
      https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task
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

LEFT_ANKLE = 27
RIGHT_ANKLE = 28

DEFAULT_MODEL_PATH = "pose_landmarker_lite.task"

# Tuned defaults from notebook validation on real running-in-place footage.
# Re-tune these (see the notebook's plotting cells) if a different camera
# setup or distance from camera starts mis-counting steps.
MIN_STEP_INTERVAL_SEC = 0.25   # a step cycle won't be faster than this
PEAK_PROMINENCE = 0.01         # minimum bump size to count as a step; raise if noise is counted


class CadenceTracker:
    """
    Feed it frames one at a time (live feed) or in a loop (offline video),
    then call finalize() once the test session is over to get the report JSON.
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
        self._timestamps_sec = []
        self._closed = False

    def start(self):
        """Call once before the first process_frame (process_frame also calls this
        automatically on first use, so this is optional but explicit is clearer)."""
        self._start_time = time.time()

    def process_frame(self, frame_bgr: np.ndarray, timestamp_ms: int = None) -> dict:
        """
        Feed a single BGR frame (e.g. from cv2.VideoCapture, or decoded from a
        websocket JPEG/PNG frame with cv2.imdecode).

        timestamp_ms: pass this explicitly when replaying a video file (frame_idx *
                      frame_interval_ms, see analyze_video_file below). Omit it for a
                      live feed - it will use wall-clock time since start() instead.

        Returns a small dict for live UI feedback (running step count / cadence so far).
        This is a cheap incremental estimate - the authoritative numbers come from
        finalize().
        """
        if self._start_time is None:
            self.start()

        if timestamp_ms is None:
            timestamp_ms = int((time.time() - self._start_time) * 1000)

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            landmarks = result.pose_landmarks[0]
            avg_ankle_y = (landmarks[LEFT_ANKLE].y + landmarks[RIGHT_ANKLE].y) / 2.0
            self._ankle_y_series.append(avg_ankle_y)
            self._timestamps_sec.append(timestamp_ms / 1000.0)

        return self._live_stats()

    def _live_stats(self) -> dict:
        if len(self._ankle_y_series) < 2:
            return {"steps_so_far": 0, "live_cadence": 0.0, "elapsed_sec": 0.0}

        series = np.array(self._ankle_y_series)
        peaks, _ = find_peaks(
            -series,
            distance=max(1, int(MIN_STEP_INTERVAL_SEC * self._estimated_fps())),
            prominence=PEAK_PROMINENCE,
        )
        elapsed = self._timestamps_sec[-1] - self._timestamps_sec[0]
        cadence = len(peaks) / elapsed if elapsed > 0 else 0.0
        return {
            "steps_so_far": int(len(peaks)),
            "live_cadence": round(float(cadence), 2),
            "elapsed_sec": round(float(elapsed), 1),
        }

    def _estimated_fps(self) -> float:
        if len(self._timestamps_sec) < 2:
            return 30.0
        duration = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return (len(self._timestamps_sec) - 1) / duration if duration > 0 else 30.0

    def finalize(self, manual_input: dict, reference: dict = None) -> dict:
        """
        Call once the test session ends. Runs the full peak-detection pass over the
        whole session and builds the final JSON report - this is what gets sent to Groq.

        manual_input: dict with "distance_m" and "time_sec" (and optionally "yoyo_level").
                      avg_speed_mps is computed automatically if not supplied.
        reference:    optional dict, e.g. {"target_board": "BCCI", "target_yoyo_score": 17.1}
        """
        series = np.array(self._ankle_y_series)
        timestamps = np.array(self._timestamps_sec)

        if len(series) < 2:
            cadence_metrics = {
                "avg_steps_per_sec": 0.0,
                "cadence_by_third": [0.0, 0.0, 0.0],
                "cadence_trend": "insufficient_data",
                "analysis_duration_sec": 0.0,
            }
        else:
            fps = self._estimated_fps()
            peaks, _ = find_peaks(
                -series,
                distance=max(1, int(MIN_STEP_INTERVAL_SEC * fps)),
                prominence=PEAK_PROMINENCE,
            )
            duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 1.0
            avg_cadence = len(peaks) / duration if duration > 0 else 0.0

            window_edges = np.linspace(0, len(series), 4).astype(int)
            window_cadences = []
            for i in range(3):
                start, end = window_edges[i], window_edges[i + 1]
                window_peaks = [p for p in peaks if start <= p < end]
                window_duration = (timestamps[end - 1] - timestamps[start]) if end > start else 1.0
                window_cadences.append(len(window_peaks) / window_duration if window_duration > 0 else 0.0)

            trend = "stable"
            if window_cadences[-1] < window_cadences[0] * 0.9:
                trend = "declining"
            elif window_cadences[-1] > window_cadences[0] * 1.1:
                trend = "increasing"

            cadence_metrics = {
                "avg_steps_per_sec": round(float(avg_cadence), 2),
                "cadence_by_third": [round(float(c), 2) for c in window_cadences],
                "cadence_trend": trend,
                "analysis_duration_sec": round(float(duration), 1),
            }

        distance_m = manual_input.get("distance_m", 0.0)
        time_sec = manual_input.get("time_sec", 0.0)
        avg_speed_mps = manual_input.get(
            "avg_speed_mps",
            (distance_m / time_sec) if time_sec > 0 else 0.0,
        )

        reference = reference or {}
        target_score = reference.get("target_yoyo_score")
        current_level = manual_input.get("yoyo_level")

        # Deterministic comparison against the target - computed here in Python,
        # not left for the LLM to work out, since exact numeric comparisons
        # are the kind of thing LLMs occasionally get wrong.
        comparison = {
            "meets_target": None,
            "gap_to_target": None,
        }
        if target_score is not None and current_level is not None:
            try:
                current_numeric = float(current_level)
                target_numeric = float(target_score)
                comparison["meets_target"] = current_numeric >= target_numeric
                comparison["gap_to_target"] = round(target_numeric - current_numeric, 2)
            except (TypeError, ValueError):
                # yoyo_level wasn't a clean number (e.g. "16.3" parses fine, but
                # guard against unexpected formats) - leave comparison as None
                # rather than guessing.
                pass

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "manual_input": {
                "distance_m": distance_m,
                "time_sec": time_sec,
                "avg_speed_mps": round(float(avg_speed_mps), 2),
                "yoyo_level": current_level,
            },
            "cadence_metrics": cadence_metrics,
            "reference": reference,
            "comparison": comparison,
        }
        return report

    def close(self):
        """Release the MediaPipe landmarker. Always call this when done (or use
        the tracker as a context manager, see __enter__/__exit__ below)."""
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
    """
    Offline mode - matches the notebook exactly. Processes a full saved video file
    and returns the final JSON report. Useful for re-validating on new test clips
    without needing a live camera.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval_ms = int(1000 / fps)

    tracker = CadenceTracker(model_path=model_path)
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
    # Quick manual test: python cadence_tracker.py path/to/video.mp4
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cadence_tracker.py <video_path>")
        sys.exit(1)

    result = analyze_video_file(
        sys.argv[1],
        manual_input={"distance_m": 400.0, "time_sec": 480.0, "yoyo_level": "16.3"},
        reference={"target_board": "BCCI", "target_yoyo_score": 17.1},
    )
    print(json.dumps(result, indent=2))
