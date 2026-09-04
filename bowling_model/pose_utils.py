"""MediaPipe Task API pose extraction + hand-crafted joint-angle features.
Generated from the notebook's pose-extraction cell."""
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from config import LM, SEQUENCE_LENGTH, ANGLE_NAMES, POSE_MODEL_PATH

_video_options = mp_vision.PoseLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=POSE_MODEL_PATH),
    running_mode=mp_vision.RunningMode.VIDEO,
    num_poses=1,
    min_pose_detection_confidence=0.4,
    min_tracking_confidence=0.4,
)

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32),
]

def _angle(a, b, c):
    """Angle at point b, formed by points a-b-c, in degrees. Points are (x, y)."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def extract_landmark_sequence(video_path, sequence_length=SEQUENCE_LENGTH):
    """Returns a list of length sequence_length; each entry is either a dict
    {landmark_name: (x, y, z, visibility)} or None if pose wasn't detected on that
    sampled frame. Coordinates are MediaPipe's normalized [0,1] image coords."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    if total_frames <= 0:
        cap.release()
        return None

    wanted = set(np.linspace(0, max(total_frames - 1, 0), sequence_length).astype(int).tolist())
    results_by_frame = {}

    with mp_vision.PoseLandmarker.create_from_options(_video_options) as landmarker:
        frame_idx = 0
        while cap.isOpened() and len(results_by_frame) < len(wanted):
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in wanted:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = int(frame_idx * 1000 / fps)
                res = landmarker.detect_for_video(mp_image, timestamp_ms)
                if res.pose_landmarks:
                    lm = res.pose_landmarks[0]  # first detected person
                    frame_dict = {
                        name: (lm[idx].x, lm[idx].y, lm[idx].z, lm[idx].visibility)
                        for name, idx in LM.items()
                    }
                else:
                    frame_dict = None
                results_by_frame[frame_idx] = frame_dict
            frame_idx += 1
    cap.release()

    ordered = [results_by_frame.get(i) for i in sorted(wanted)]
    while len(ordered) < sequence_length:
        ordered.append(ordered[-1] if ordered else None)
    return ordered[:sequence_length]


def compute_frame_angles(frame_landmarks):
    """dict of landmark -> (x,y,z,vis) -> dict of ANGLE_NAMES -> degrees."""
    if frame_landmarks is None:
        return None
    p = {k: (v[0], v[1]) for k, v in frame_landmarks.items()}
    try:
        angles = {
            "l_elbow_angle": _angle(p["l_shoulder"], p["l_elbow"], p["l_wrist"]),
            "r_elbow_angle": _angle(p["r_shoulder"], p["r_elbow"], p["r_wrist"]),
            "l_knee_angle": _angle(p["l_hip"], p["l_knee"], p["l_ankle"]),
            "r_knee_angle": _angle(p["r_hip"], p["r_knee"], p["r_ankle"]),
            "l_shoulder_angle": _angle(p["l_elbow"], p["l_shoulder"], p["l_hip"]),
            "r_shoulder_angle": _angle(p["r_elbow"], p["r_shoulder"], p["r_hip"]),
            "l_hip_angle": _angle(p["l_shoulder"], p["l_hip"], p["l_knee"]),
            "r_hip_angle": _angle(p["r_shoulder"], p["r_hip"], p["r_knee"]),
            "trunk_lean_angle": _angle(
                p["nose"],
                ((p["l_shoulder"][0] + p["r_shoulder"][0]) / 2, (p["l_shoulder"][1] + p["r_shoulder"][1]) / 2),
                ((p["l_hip"][0] + p["r_hip"][0]) / 2, (p["l_hip"][1] + p["r_hip"][1]) / 2),
            ),
        }
    except KeyError:
        return None
    return angles


def extract_angle_feature_vector(video_path):
    """Full clip -> fixed-length feature vector: mean/std/min/max per angle.
    Returns (feature_vector, n_valid_frames) or (None, 0) if pose was never detected."""
    seq = extract_landmark_sequence(video_path)
    if seq is None:
        return None, 0

    angle_rows = []
    for frame in seq:
        angles = compute_frame_angles(frame)
        if angles is not None:
            angle_rows.append([angles[name] for name in ANGLE_NAMES])

    if len(angle_rows) < 5:
        return None, len(angle_rows)

    arr = np.array(angle_rows)
    feature_vector = np.concatenate([arr.mean(axis=0), arr.std(axis=0),
                                      arr.min(axis=0), arr.max(axis=0)])
    return feature_vector, len(angle_rows)


def feature_names():
    stats = ["mean", "std", "min", "max"]
    return [f"{name}_{stat}" for stat in stats for name in ANGLE_NAMES]


def extract_normalized_pose_sequence(video_path):
    """Full clip -> (SEQUENCE_LENGTH, n_landmarks*2) array of (x, y) coords, centered on
    hip midpoint and scaled by torso length, for DTW comparison."""
    seq = extract_landmark_sequence(video_path)
    if seq is None:
        return None

    names = list(LM.keys())
    frames = []
    last_valid = None
    for frame in seq:
        if frame is None:
            frames.append(last_valid)
            continue
        hip_mid = np.array([(frame["l_hip"][0] + frame["r_hip"][0]) / 2,
                             (frame["l_hip"][1] + frame["r_hip"][1]) / 2])
        shoulder_mid = np.array([(frame["l_shoulder"][0] + frame["r_shoulder"][0]) / 2,
                                  (frame["l_shoulder"][1] + frame["r_shoulder"][1]) / 2])
        torso_len = max(np.linalg.norm(shoulder_mid - hip_mid), 1e-6)
        coords = []
        for name in names:
            x, y = frame[name][0], frame[name][1]
            coords.extend([(x - hip_mid[0]) / torso_len, (y - hip_mid[1]) / torso_len])
        frames.append(np.array(coords))
        last_valid = frames[-1]

    if all(f is None for f in frames):
        return None
    first_valid = next(f for f in frames if f is not None)
    frames = [f if f is not None else first_valid for f in frames]
    return np.array(frames)


