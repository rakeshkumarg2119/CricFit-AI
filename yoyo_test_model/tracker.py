"""
ShuttleCadenceTracker: feed it frames (live or looped over a video), then
call finalize() once the session is over.

This class is now deliberately thin - it only does pose capture and raw
signal bookkeeping. The actual logic lives in:
    segmentation.py - turns the motion signal into running legs / rests
    cadence.py      - counts steps within a leg
    report.py       - assembles the final JSON report

Note: frames where MediaPipe finds no pose are skipped entirely - all
internal series (timestamps included) are indexed by DETECTED frames, not
raw video frames.
"""

import time
from typing import Optional

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from . import config
from .segmentation import segment_movement
from .report import build_report


class ShuttleCadenceTracker:

    def __init__(self, model_path: str = config.DEFAULT_MODEL_PATH):
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._start_time = None

        # left-minus-right ankle-y, NOT the average - see cadence.py
        # docstring for why the average was the root cause of 0 detected
        # steps on real footage.
        self._ankle_diff_series = []
        self._hip_x_series = []        # informative for side-on filming
        self._body_scale_series = []   # informative for end-on filming
        self._timestamps_sec = []
        self._frames_processed = 0     # all frames fed in, pose or not
        self._closed = False
        self._last_signal_used = None

    def start(self):
        self._start_time = time.time()

    def process_frame(self, frame_bgr: np.ndarray, timestamp_ms: int = None) -> dict:
        if self._start_time is None:
            self.start()
        if timestamp_ms is None:
            timestamp_ms = int((time.time() - self._start_time) * 1000)

        self._frames_processed += 1

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            lm = result.pose_landmarks[0]
            ankle_diff = lm[config.LEFT_ANKLE].y - lm[config.RIGHT_ANKLE].y
            avg_hip_x = (lm[config.LEFT_HIP].x + lm[config.RIGHT_HIP].x) / 2.0

            # torso length (shoulder-to-hip distance) as a proxy for
            # distance from camera: shrinks running away, grows running
            # toward. Track both this and hip-x - whichever actually varies
            # over the session tells us which way the camera was pointed.
            left_torso = np.hypot(lm[config.LEFT_SHOULDER].x - lm[config.LEFT_HIP].x,
                                   lm[config.LEFT_SHOULDER].y - lm[config.LEFT_HIP].y)
            right_torso = np.hypot(lm[config.RIGHT_SHOULDER].x - lm[config.RIGHT_HIP].x,
                                    lm[config.RIGHT_SHOULDER].y - lm[config.RIGHT_HIP].y)
            body_scale = (left_torso + right_torso) / 2.0

            self._ankle_diff_series.append(ankle_diff)
            self._hip_x_series.append(avg_hip_x)
            self._body_scale_series.append(body_scale)
            self._timestamps_sec.append(timestamp_ms / 1000.0)

        return self._live_stats()

    def _select_motion_signal(self) -> np.ndarray:
        """Picks whichever tracked signal (hip-x or body-scale) actually
        shows real movement over the session, so the same code handles
        side-on footage and end-on footage without being told which one
        was used to film."""
        x = np.array(self._hip_x_series)
        scale = np.array(self._body_scale_series)
        if len(x) < 3:
            return x
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
        legs, _ = segment_movement(signal, np.array(self._timestamps_sec), self._estimated_fps())
        elapsed = self._timestamps_sec[-1] - self._timestamps_sec[0]
        return {
            "legs_so_far": len(legs),
            "elapsed_sec": round(float(elapsed), 1),
        }

    def finalize(self, manual_input: dict, reference: Optional[dict] = None) -> dict:
        """
        manual_input: {"yoyo_level": "16.3"} (the reported level.shuttle
                      score the test administrator/app already recorded).
                      Optional "measured_test_duration_sec" for a sanity
                      cross-check.
        reference:    optional {"target_board": "BCCI",
                      "target_yoyo_score": 17.1}
        """
        ankle_diff_series = np.array(self._ankle_diff_series)
        body_scale_series = np.array(self._body_scale_series)
        signal = self._select_motion_signal()
        timestamps = np.array(self._timestamps_sec)
        fps = self._estimated_fps()

        legs, _ = segment_movement(signal, timestamps, fps) if len(signal) >= 3 else ([], [])

        return build_report(
            legs=legs,
            ankle_diff_series=ankle_diff_series,
            body_scale_series=body_scale_series,
            timestamps=timestamps,
            fps=fps,
            last_signal_used=self._last_signal_used,
            frames_processed=self._frames_processed,
            manual_input=manual_input,
            reference=reference,
        )

    def close(self):
        if not self._closed:
            self._landmarker.close()
            self._closed = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
