"""
Runs a saved video file (from upload OR a record-then-send capture -
they're the same file format by the time it gets here) through the tracker
frame by frame and returns the finalized report.
"""

import cv2

from . import config
from .tracker import ShuttleCadenceTracker


def analyze_video_file(video_path: str, manual_input: dict, reference: dict = None,
                        model_path: str = config.DEFAULT_MODEL_PATH) -> dict:
    cap = cv2.VideoCapture(video_path)
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
