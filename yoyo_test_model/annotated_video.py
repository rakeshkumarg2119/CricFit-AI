"""
Annotated (skeleton-overlay) video for the Yo-Yo test module.

This ported the ALREADY-VALIDATED overlay logic from
`yoyo_cadence_pipeline.ipynb` (section 10, v2.3) rather than inventing a new
drawing style - the notebook version was tested frame-by-frame against real
footage and had two real bugs fixed in it (index misalignment between
"raw video frame" and "frame with a detected pose"; genuine sprints briefly
getting mislabeled RESTING). Re-deriving those fixes from scratch here would
have been a mistake.

Unlike the batting/bowling annotated-video functions (which overlay a
static end-of-clip summary panel), this draws a LIVE per-frame state label
- RUNNING (shuttle N) / RESTING / TURN / NO POSE - because that's what the
notebook's testing showed was actually useful for a Yo-Yo test: seeing the
segmentation's decision frame-by-frame, not just the final numbers.

Kept in its own file, separate from tracker.py/video_pipeline.py - this
does its own frame loop (needed to access the internal `legs`/`rests`
segmentation, which finalize() computes but doesn't expose).

Requires ffmpeg on the system PATH.
"""

import os

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from . import config
from .segmentation import segment_movement
from .tracker import ShuttleCadenceTracker

# Standard 33-point MediaPipe Pose connections, hardcoded - same fix the
# notebook made: mp.solutions.pose.POSE_CONNECTIONS (legacy drawing_utils)
# is deprecated/removed in newer mediapipe builds, so it can't be relied on.
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
]


def _draw_pose_landmarks(frame, landmarks, w, h):
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in POSE_CONNECTIONS:
        if a < len(points) and b < len(points):
            cv2.line(frame, points[a], points[b], (0, 200, 255), 2)
    for x, y in points:
        cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)
    return frame


def _frame_state_label(det_idx, legs, rests):
    """Which state + shuttle number a given DETECTED-frame index falls
    into. `legs`/`rests` are index ranges into the series of frames WHERE A
    POSE WAS DETECTED - not the raw video frame number. The two diverge
    whenever any frame loses its pose, and every divergence shifts all
    later labels if you mix them up (this was one of the notebook's fixed
    bugs)."""
    for i, (s, e, _) in enumerate(legs):
        if s <= det_idx < e:
            shuttle_num = (i // 2) + 1
            return f"RUNNING (shuttle {shuttle_num})"
    for s, e in rests:
        if s <= det_idx < e:
            return "RESTING"
    return "TURN"


def generate_annotated_video(video_path: str, output_path: str, manual_input: dict,
                              reference: dict = None,
                              model_path: str = config.DEFAULT_MODEL_PATH):
    """Runs the full Yo-Yo pipeline AND produces one video with the skeleton
    + live RUNNING/RESTING/TURN/NO POSE label baked in. Returns
    (h264_video_path, report) - same return shape as the batting/bowling
    annotated-video functions.

    Does its own tracker pass (rather than calling video_pipeline's
    analyze_video_file) because it needs `legs` AND `rests` for the overlay,
    and finalize() only returns legs internally, discarding rests."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video file: {video_path}")

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
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

    # Re-derive legs/rests the same way finalize() does internally (same
    # signal, same fps -> deterministic, same result) since finalize()
    # doesn't expose rests on its own.
    signal = tracker._select_motion_signal()
    timestamps = np.array(tracker._timestamps_sec)
    legs, rests = segment_movement(signal, timestamps, tracker._estimated_fps()) if len(signal) >= 3 else ([], [])
    tracker.close()

    if "error" in report:
        return None, report

    # Second pass, purely for drawing - same pattern the batting/bowling
    # annotated-video functions use (re-run pose detection rather than
    # caching landmarks from the first pass).
    cap2 = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (frame_w, frame_h))

    landmarker2 = mp_vision.PoseLandmarker.create_from_options(
        mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
        )
    )

    frame_idx = 0   # counts ALL video frames - drives the detection timestamp
    det_idx = 0     # counts frames WHERE A POSE WAS FOUND - drives the label
    try:
        while cap2.isOpened():
            ret, frame = cap2.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = landmarker2.detect_for_video(mp_image, frame_idx * frame_interval_ms)

            if result.pose_landmarks:
                frame = _draw_pose_landmarks(frame, result.pose_landmarks[0], frame_w, frame_h)
                label = _frame_state_label(det_idx, legs, rests)
                det_idx += 1
            else:
                label = "NO POSE"

            cv2.rectangle(frame, (10, 10), (360, 55), (0, 0, 0), -1)
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

            writer.write(frame)
            frame_idx += 1
    finally:
        cap2.release()
        writer.release()
        landmarker2.close()

    # Same WhatsApp-safe re-encode settings validated in the notebook.
    h264_path = output_path.replace(".mp4", "_h264.mp4")
    cmd = (
        f'ffmpeg -y -i "{output_path}" -c:v libx264 -profile:v baseline '
        f'-level 3.0 -pix_fmt yuv420p -movflags +faststart -crf 26 '
        f'-preset veryfast -an "{h264_path}"'
    )
    ret_code = os.system(cmd)
    if ret_code != 0 or not os.path.exists(h264_path):
        return output_path, report

    return h264_path, report
