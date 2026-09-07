"""
batting_pipeline.py

Standalone inference module for the Cricket Batting Shot Classifier + Stage 2
comparison report. No notebook / Colab dependency — this is what your backend
actually imports and calls at request time. The notebook
(batting_full_pipeline.ipynb) is only used for TRAINING; it produces the model
files this module loads.

--------------------------------------------------------------------------
Setup (run once, in your backend's environment)
--------------------------------------------------------------------------
pip install tensorflow opencv-python-headless mediapipe fastdtw scipy numpy

ffmpeg must also be installed on the system (used to re-encode the annotated
video to H.264 for browser playback) — e.g. `apt-get install ffmpeg` on Linux.

--------------------------------------------------------------------------
Required files (produced by the training notebook — copy them next to this
script, or point the *_PATH constants below / the matching env vars at
wherever your backend stores them)
--------------------------------------------------------------------------
    - batting_shot_classifier.keras   (trained model)
    - batting_class_names.json        (class name list)
    - reference_library.npz           (cached reference keypoint sequences)
    - pose_landmarker_lite.task       (MediaPipe pose model — auto-downloaded
                                        on first run if not already present)

--------------------------------------------------------------------------
Usage from your backend (e.g. FastAPI)
--------------------------------------------------------------------------
    from batting_pipeline import generate_report, generate_annotated_report_video

    report = generate_report("path/to/uploaded_video.mp4")
    # -> JSON-serializable dict: shot classification + Stage 2 comparison scores

    # or, if you also want the skeleton-overlay + report-panel video:
    h264_video_path, report = generate_annotated_report_video("path/to/uploaded_video.mp4")
"""

import os
import json
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from tensorflow import keras
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean


# ============================================================================
# Paths — override via env vars, or just edit the defaults below to match
# wherever your backend keeps the model artifacts.
# ============================================================================
MODEL_PATH = os.environ.get("BATTING_MODEL_PATH", "model/batting_shot_classifier.keras")
CLASS_NAMES_PATH = os.environ.get("BATTING_CLASS_NAMES_PATH", "model/batting_class_names.json")
REFERENCE_LIBRARY_PATH = os.environ.get("BATTING_REFERENCE_LIBRARY_PATH", "reference/reference_library.npz")
POSE_LANDMARKER_PATH = os.environ.get("BATTING_POSE_LANDMARKER_PATH", "pose_landmarker_lite.task")
POSE_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)


# ============================================================================
# Config — MUST match what the training notebook used. Do not change these
# without retraining the model; they define the model's input shape/feature
# layout.
# ============================================================================
SEQUENCE_LENGTH = 30       # frames per input sequence
FEATURES_PER_KEYPOINT = 3  # x, y, visibility

# MediaPipe Pose landmark indices we keep (left/right shoulder, elbow, wrist,
# hip, knee, ankle, heel, foot_index + nose) — see
# https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
KEEP_LANDMARKS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 0]

# Named lookup into KEEP_LANDMARKS / each feature row, in the same order as above.
JOINT_IDX = {
    "l_shoulder": 0, "r_shoulder": 1, "l_elbow": 2, "r_elbow": 3,
    "l_wrist": 4, "r_wrist": 5, "l_hip": 6, "r_hip": 7,
    "l_knee": 8, "r_knee": 9, "l_ankle": 10, "r_ankle": 11,
    "l_heel": 12, "r_heel": 13, "l_foot_index": 14, "r_foot_index": 15, "nose": 16,
}

NUM_FEATURES = len(KEEP_LANDMARKS) * FEATURES_PER_KEYPOINT

# Used for drawing the skeleton overlay in generate_annotated_report_video()
POSE_CONNECTIONS = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24),
                     (23, 24), (23, 25), (25, 27), (27, 29), (29, 31), (24, 26), (26, 28),
                     (28, 30), (30, 32), (15, 17), (15, 19), (15, 21), (16, 18), (16, 20),
                     (16, 22), (27, 31), (28, 32)]


# ============================================================================
# One-time setup, run at import time: pose landmarker, trained model, class
# names, reference library. Doing this at import (not per-request) means your
# backend should import this module ONCE at startup, not per-request.
# ============================================================================
def _ensure_pose_landmarker_file():
    if not os.path.exists(POSE_LANDMARKER_PATH):
        print(f"[batting_pipeline] Downloading pose landmarker model to {POSE_LANDMARKER_PATH} ...")
        urllib.request.urlretrieve(POSE_LANDMARKER_URL, POSE_LANDMARKER_PATH)


_ensure_pose_landmarker_file()

_base_options = mp_tasks.BaseOptions(model_asset_path=POSE_LANDMARKER_PATH)
_pose_options = mp_vision.PoseLandmarkerOptions(
    base_options=_base_options,
    running_mode=mp_vision.RunningMode.IMAGE,
    min_pose_detection_confidence=0.4,
    min_tracking_confidence=0.4,
)
landmarker = mp_vision.PoseLandmarker.create_from_options(_pose_options)

model = keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH) as f:
    CLASS_NAMES = json.load(f)

_ref_cache = np.load(REFERENCE_LIBRARY_PATH)
REFERENCE_LIBRARY = {k: _ref_cache[k] for k in _ref_cache.files}

print(f"[batting_pipeline] Ready: {len(CLASS_NAMES)} classes, "
      f"{len(REFERENCE_LIBRARY)} reference clips loaded.")


# ============================================================================
# Pose extraction: video/image -> keypoint sequence
# ============================================================================
def extract_keypoint_sequence(video_path, sequence_length=SEQUENCE_LENGTH):
    """cuDNN's fused GRU kernel only accepts masks that are right-padded — real
    frames first, then zero-padding only at the very end, never a zero row in
    the middle. A single frame with no detected pose (motion blur, brief
    occlusion, bad angle, etc.) is forward-filled (and backward-filled for the
    very first frame, if needed) from the nearest successfully-detected frame,
    so every "real" frame in the clip carries real keypoints. True padding
    only happens at the end, if the clip has fewer than sequence_length
    readable frames."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return None
    frame_indices = np.linspace(0, max(total_frames - 1, 0), sequence_length).astype(int)
    sequence = []  # list of (feats or None)
    frame_idx = 0
    wanted = list(frame_indices)
    next_i = 0
    while cap.isOpened() and next_i < len(wanted):
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx == wanted[next_i]:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)
            if result.pose_landmarks:
                lm = result.pose_landmarks[0]
                frame_feats = []
                for idx in KEEP_LANDMARKS:
                    p = lm[idx]
                    frame_feats.extend([p.x, p.y, p.visibility])
            else:
                frame_feats = None  # no pose detected on this sampled frame
            sequence.append(frame_feats)
            next_i += 1
        frame_idx += 1
    cap.release()
    if len(sequence) == 0 or all(f is None for f in sequence):
        return None

    # Forward-fill missing frames from the last successful detection...
    last_good = None
    for i in range(len(sequence)):
        if sequence[i] is not None:
            last_good = sequence[i]
        elif last_good is not None:
            sequence[i] = last_good
    # ...then backward-fill any still-missing frames at the very start of the clip.
    first_good = next(f for f in sequence if f is not None)
    for i in range(len(sequence)):
        if sequence[i] is None:
            sequence[i] = first_good

    seq = np.array(sequence, dtype=np.float32)
    if seq.shape[0] < sequence_length:
        pad = np.zeros((sequence_length - seq.shape[0], NUM_FEATURES), dtype=np.float32)
        seq = np.vstack([seq, pad])
    return seq


def extract_keypoint_sequence_from_image(image_path, sequence_length=SEQUENCE_LENGTH):
    """Images have no motion to sample across, so pose detection runs once and
    that single frame's keypoints are repeated for the full sequence length."""
    frame = cv2.imread(image_path)
    if frame is None:
        return None
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_image)
    if not result.pose_landmarks:
        return None
    lm = result.pose_landmarks[0]
    frame_feats = []
    for idx in KEEP_LANDMARKS:
        p = lm[idx]
        frame_feats.extend([p.x, p.y, p.visibility])
    frame_feats = np.array(frame_feats, dtype=np.float32)
    return np.tile(frame_feats, (sequence_length, 1))


# ============================================================================
# Stage 2: reference-comparison metric functions
# ============================================================================
def get_joint_xy(seq, frame_idx, joint_name):
    base = JOINT_IDX[joint_name] * FEATURES_PER_KEYPOINT
    x, y = seq[frame_idx, base], seq[frame_idx, base + 1]
    return np.array([x, y])


def angle_at(seq, frame_idx, a, b, c):
    """Angle at joint b, formed by points a-b-c, in degrees."""
    pa, pb, pc = get_joint_xy(seq, frame_idx, a), get_joint_xy(seq, frame_idx, b), get_joint_xy(seq, frame_idx, c)
    v1, v2 = pa - pb, pc - pb
    denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-8
    cos_angle = np.clip(np.dot(v1, v2) / denom, -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


def dtw_align(user_seq, ref_seq):
    """Aligns the two sequences frame-by-frame using DTW on flattened keypoints.
    Returns (distance, path) where path is a list of (user_idx, ref_idx) pairs."""
    distance, path = fastdtw(user_seq, ref_seq, dist=euclidean)
    return distance, path


def movement_quality_score(user_seq, ref_seq, dtw_distance):
    """Lower DTW distance = closer match to reference. Converted to a 0-100
    similarity number for readability. This is a RELATIVE similarity measure,
    not a calibrated fitness score."""
    SCALE = 50.0
    normalized = dtw_distance / (len(user_seq) * SCALE)
    similarity = max(0.0, 100.0 - normalized * 100.0)
    return round(similarity, 1)


def symmetry_score(seq, frame_idx):
    """Compares left vs right elbow and knee angles at a given frame.
    Smaller difference = more symmetric."""
    l_elbow = angle_at(seq, frame_idx, "l_shoulder", "l_elbow", "l_wrist")
    r_elbow = angle_at(seq, frame_idx, "r_shoulder", "r_elbow", "r_wrist")
    l_knee = angle_at(seq, frame_idx, "l_hip", "l_knee", "l_ankle")
    r_knee = angle_at(seq, frame_idx, "r_hip", "r_knee", "r_ankle")
    elbow_diff = abs(l_elbow - r_elbow)
    knee_diff = abs(l_knee - r_knee)
    avg_diff = (elbow_diff + knee_diff) / 2.0
    score = max(0.0, 100.0 - avg_diff)
    return round(score, 1), {"elbow_angle_diff_deg": round(elbow_diff, 1),
                              "knee_angle_diff_deg": round(knee_diff, 1)}


def coordination_deviation(user_seq, ref_seq):
    """Compares the TIMING of hip rotation vs shoulder rotation (a simple
    proxy for kinetic-chain sequencing) between user and reference."""
    def rotation_signal(seq, joint_a, joint_b):
        return np.array([abs(get_joint_xy(seq, i, joint_a)[0] - get_joint_xy(seq, i, joint_b)[0])
                          for i in range(len(seq))])

    user_hip = rotation_signal(user_seq, "l_hip", "r_hip")
    user_shoulder = rotation_signal(user_seq, "l_shoulder", "r_shoulder")
    ref_hip = rotation_signal(ref_seq, "l_hip", "r_hip")
    ref_shoulder = rotation_signal(ref_seq, "l_shoulder", "r_shoulder")

    user_lag = np.argmax(user_shoulder) - np.argmax(user_hip)
    ref_lag = np.argmax(ref_shoulder) - np.argmax(ref_hip)
    return abs(user_lag - ref_lag)


def mobility_proxy(user_seq, ref_seq, path):
    """APPROXIMATE. Compares front-knee flexion at the DTW-aligned
    peak-flexion frame. Camera-angle dependent."""
    user_knee_angles = [angle_at(user_seq, i, "l_hip", "l_knee", "l_ankle") for i in range(len(user_seq))]
    ref_knee_angles = [angle_at(ref_seq, i, "l_hip", "l_knee", "l_ankle") for i in range(len(ref_seq))]
    user_min_idx = int(np.argmin(user_knee_angles))
    aligned_ref_idx = next((r for (u, r) in path if u == user_min_idx), int(np.argmin(ref_knee_angles)))
    deviation_deg = abs(user_knee_angles[user_min_idx] - ref_knee_angles[aligned_ref_idx])
    return round(deviation_deg, 1)


def balance_proxy(user_seq, ref_seq):
    """WEAK PROXY ONLY. Sideways drift of the hip midpoint over the clip,
    compared to the reference's drift. Not a real balance/COM measurement."""
    def hip_midpoint_drift(seq):
        xs = [(get_joint_xy(seq, i, "l_hip")[0] + get_joint_xy(seq, i, "r_hip")[0]) / 2 for i in range(len(seq))]
        return np.std(xs)
    user_drift = hip_midpoint_drift(user_seq)
    ref_drift = hip_midpoint_drift(ref_seq)
    return round(float(user_drift - ref_drift), 4)


def core_stability_proxy(user_seq, ref_seq):
    """WEAK PROXY ONLY. Trunk-angle (hip-mid to shoulder-mid vector) deviation
    from vertical, variance across the clip vs reference. Not a real core
    strength/stability measurement."""
    def trunk_angle_variance(seq):
        angles = []
        for i in range(len(seq)):
            hip_mid = (get_joint_xy(seq, i, "l_hip") + get_joint_xy(seq, i, "r_hip")) / 2
            shoulder_mid = (get_joint_xy(seq, i, "l_shoulder") + get_joint_xy(seq, i, "r_shoulder")) / 2
            vec = shoulder_mid - hip_mid
            angle = np.degrees(np.arctan2(vec[0], -vec[1]))
            angles.append(angle)
        return np.var(angles)
    user_var = trunk_angle_variance(user_seq)
    ref_var = trunk_angle_variance(ref_seq)
    return round(float(user_var - ref_var), 2)


def _json_safe(obj):
    """Recursively converts numpy scalar/array types to plain Python types so
    the report dict can be safely passed to json.dumps()."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


# ============================================================================
# The two functions your backend actually calls
# ============================================================================
def generate_report(video_path):
    """Runs Stage 1 (classification) + Stage 2 (comparison vs reference clip)
    on a video and returns a single JSON-serializable dict."""
    user_seq = extract_keypoint_sequence(video_path)
    if user_seq is None:
        return {"error": "Could not extract pose from video. Check the file/camera visibility."}

    pred = model.predict(np.expand_dims(user_seq, axis=0), verbose=0)[0]
    pred_idx = int(np.argmax(pred))
    shot_label = CLASS_NAMES[pred_idx]
    confidence = float(pred[pred_idx])

    report = {
        "shot_classification": {
            "label": shot_label,
            "confidence": round(confidence, 3)
        }
    }

    ref_seq = REFERENCE_LIBRARY.get(shot_label)
    if ref_seq is None:
        report["comparison"] = {"note": f"No reference clip available for '{shot_label}' yet."}
        return _json_safe(report)

    dtw_distance, path = dtw_align(user_seq, ref_seq)
    symmetry, symmetry_detail = symmetry_score(user_seq, frame_idx=len(user_seq) // 2)

    report["comparison"] = {
        "movement_quality_similarity_pct": movement_quality_score(user_seq, ref_seq, dtw_distance),
        "symmetry_score": symmetry,
        "symmetry_detail": symmetry_detail,
        "coordination_timing_deviation_frames": int(coordination_deviation(user_seq, ref_seq)),
        "mobility_indicator_deg_deviation": mobility_proxy(user_seq, ref_seq, path),
        "balance_indicator": balance_proxy(user_seq, ref_seq),
        "core_stability_indicator": core_stability_proxy(user_seq, ref_seq),
    }

    report["caveats"] = [
        "All metrics are RELATIVE to a single reference clip, not absolute/clinical measurements.",
        "mobility_indicator, balance_indicator, and core_stability_indicator are approximate proxies, not validated biomechanical measurements.",
        "Accuracy depends on the uploaded video's camera angle roughly matching the reference clip's angle.",
    ]

    return _json_safe(report)


def draw_pose_landmarks(frame, landmarks, width, height):
    pts = [(int(p.x * width), int(p.y * height)) for p in landmarks]
    for a, b in POSE_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 255, 150), 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 3, (0, 200, 255), -1)


def generate_annotated_report_video(video_path, output_path="annotated_report.mp4",
                                     panel_side="right", panel_width=380):
    """Runs the full pipeline AND produces one video: skeleton overlay + a side
    report panel (shot name, confidence, metrics). Returns (h264_video_path, report).
    Requires ffmpeg on the system PATH."""
    report = generate_report(video_path)
    if "error" in report:
        return None, report

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    canvas_width = width + panel_width
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (canvas_width, height))

    cls = report["shot_classification"]
    comp = report.get("comparison", {})

    lines = [
        (cls["label"].upper().replace("_", " "), (255, 255, 255), 0.75, 2),
        (f"Confidence: {cls['confidence']*100:.1f}%", (180, 180, 180), 0.5, 1),
        ("", None, 0, 0),
    ]
    if comp and "movement_quality_similarity_pct" in comp:
        lines += [
            (f"Movement Quality  {comp['movement_quality_similarity_pct']}%", (120, 255, 150), 0.5, 1),
            (f"Symmetry          {comp['symmetry_score']}", (120, 255, 150), 0.5, 1),
            (f"Coordination dev  {comp['coordination_timing_deviation_frames']}f", (120, 210, 255), 0.5, 1),
            (f"Mobility dev      {comp['mobility_indicator_deg_deviation']}deg", (120, 210, 255), 0.5, 1),
            (f"Balance idx       {comp['balance_indicator']}", (120, 180, 255), 0.5, 1),
            (f"Core idx          {comp['core_stability_indicator']}", (120, 180, 255), 0.5, 1),
            ("", None, 0, 0),
            ("(approximate, vs reference clip)", (120, 120, 120), 0.4, 1),
        ]
    else:
        lines.append(("No reference clip set for this class yet", (120, 120, 120), 0.4, 1))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
        if result.pose_landmarks:
            draw_pose_landmarks(frame, result.pose_landmarks[0], width, height)

        canvas = np.zeros((height, canvas_width, 3), dtype=np.uint8)
        if panel_side == "right":
            canvas[:, :width] = frame
            panel_x0 = width
        else:
            canvas[:, panel_width:] = frame
            panel_x0 = 0

        overlay = canvas.copy()
        cv2.rectangle(overlay, (panel_x0, 0), (panel_x0 + panel_width, height), (25, 25, 25), -1)
        canvas = cv2.addWeighted(overlay, 0.88, canvas, 0.12, 0)
        cv2.line(canvas, (panel_x0, 0), (panel_x0, height), (80, 80, 80), 2)

        y = 45
        for text, color, scale, thickness in lines:
            if text == "":
                y += 18
                continue
            cv2.putText(canvas, text, (panel_x0 + 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
            y += int(32 * scale) + 14

        out.write(canvas)

    cap.release()
    out.release()

    h264_path = output_path.replace(".mp4", "_h264.mp4")
    os.system(f"ffmpeg -y -loglevel error -i {output_path} -vcodec libx264 {h264_path}")
    return h264_path, report


# ============================================================================
# Quick local test (run: python batting_pipeline.py path/to/video.mp4)
# ============================================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python batting_pipeline.py <video_path>")
        raise SystemExit(1)
    result = generate_report(sys.argv[1])
    print(json.dumps(result, indent=2))
