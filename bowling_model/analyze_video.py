"""Full inference pipeline (Task API). This is what a frontend/backend upload
handler imports: `from analyze_video import load_models, generate_report`.
Call load_models() once at process startup, then generate_report(video_path) per upload.
Generated from the notebook's pipeline cell.

Usage (CLI):
    python analyze_video.py --video path/to/clip.mp4
    python analyze_video.py --video path/to/clip.mp4 --annotate --out report.json
"""
import argparse
import json
import os
import joblib
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from tensorflow import keras
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean

from config import (ARM_MODEL_PATH, PACE_MODEL_PATH, ARM_META_PATH, PACE_META_PATH,
                     ACTION_FILTER_MODEL_PATH, ACTION_FILTER_META_PATH,
                     REFERENCE_LIBRARY_PATH, ARM_CLASSES, PACE_CLASSES, POSE_MODEL_PATH)
from pose_utils import (extract_angle_feature_vector, extract_normalized_pose_sequence,
                         _video_options, POSE_CONNECTIONS)
from action_filter import extract_image_angle_features

action_model = action_scaler = arm_model = arm_scaler = pace_model = pace_scaler = ref = None

def load_models():
    """Reloads all three Keras models + sidecars + the reference library from disk,
    and sets them as the globals used below -- for use after a runtime restart, or
    standalone in the exported backend package."""
    global action_model, action_scaler, arm_model, arm_scaler, pace_model, pace_scaler, ref
    from tensorflow import keras
    action_model = keras.models.load_model(ACTION_FILTER_MODEL_PATH)
    action_scaler = joblib.load(ACTION_FILTER_META_PATH)["scaler"]
    arm_meta = joblib.load(ARM_META_PATH)
    arm_model = keras.models.load_model(ARM_MODEL_PATH)
    arm_scaler = arm_meta["scaler"]
    pace_meta = joblib.load(PACE_META_PATH)
    pace_model = keras.models.load_model(PACE_MODEL_PATH)
    pace_scaler = pace_meta["scaler"]
    ref = np.load(REFERENCE_LIBRARY_PATH, allow_pickle=True)
    return action_model, action_scaler, arm_model, arm_scaler, pace_model, pace_scaler, ref


def is_bowling_action(video_path, sample_frames=5):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if total <= 0:
        return True, 0.0

    wanted = set(np.linspace(0, total - 1, sample_frames).astype(int).tolist())
    cap = cv2.VideoCapture(video_path)
    votes, frame_idx = [], 0
    tmp_frame_path = video_path + "._filter_frame.jpg"
    while cap.isOpened() and len(votes) < len(wanted):
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in wanted:
            cv2.imwrite(tmp_frame_path, frame)
            feat = extract_image_angle_features(tmp_frame_path)
            if feat is not None:
                feat_scaled = action_scaler.transform([feat]).astype("float32")
                prob = float(action_model.predict(feat_scaled, verbose=0)[0][0])
                votes.append(prob)
        frame_idx += 1
    cap.release()
    if os.path.isfile(tmp_frame_path):
        os.remove(tmp_frame_path)

    if not votes:
        return True, 0.0
    avg_conf = float(np.mean(votes))
    return avg_conf >= 0.5, round(avg_conf, 3)


def classify(model, scaler, classes, feature_vector):
    scaled = scaler.transform([feature_vector]).astype("float32")
    prob = float(model.predict(scaled, verbose=0)[0][0])
    pred_idx = 1 if prob >= 0.5 else 0
    confidence = prob if pred_idx == 1 else 1.0 - prob
    return {"label": classes[pred_idx], "confidence": round(confidence, 3)}


def find_closest_match(user_seq, ref):
    best_dist, best_idx = None, None
    for i, ref_seq in enumerate(ref["sequences"]):
        dist, _ = fastdtw(user_seq, ref_seq, dist=euclidean)
        if best_dist is None or dist < best_dist:
            best_dist, best_idx = dist, i
    return best_idx, best_dist


def comparison_metrics(user_seq, ref_seq):
    """All metrics are relative to the single matched reference clip, not absolute
    biomechanical measurements."""
    _, dtw_path = fastdtw(user_seq, ref_seq, dist=euclidean)
    aligned_user = np.array([user_seq[i] for i, _ in dtw_path])
    aligned_ref = np.array([ref_seq[j] for _, j in dtw_path])

    frame_dists = np.linalg.norm(aligned_user - aligned_ref, axis=1)
    similarity_pct = round(max(0.0, 100.0 - float(frame_dists.mean()) * 20), 1)
    symmetry_score = round(float(1.0 - np.std(frame_dists) / (np.mean(frame_dists) + 1e-6)), 3)
    timing_deviation_frames = round(float(np.mean(np.abs(
        np.diff([i for i, _ in dtw_path]) - np.diff([j for _, j in dtw_path])
    ))), 2) if len(dtw_path) > 1 else 0.0

    return {
        "movement_quality_similarity_pct": similarity_pct,
        "symmetry_score": symmetry_score,
        "coordination_timing_deviation_frames": timing_deviation_frames,
        "caveats": [
            "All metrics are RELATIVE to the single matched reference clip, not "
            "absolute/clinical measurements.",
            "Assumes the uploaded video's camera angle roughly matches the "
            "reference dataset's angle.",
        ],
    }


def generate_report(video_path):
    """This is what a frontend upload handler calls: report = generate_report(video_path)"""
    passed, action_conf = is_bowling_action(video_path)
    if not passed:
        return {"error": f"Doesn't look like a bowling action (confidence: {action_conf}). "
                          f"Upload a clearer bowling clip.",
                "action_filter_confidence": action_conf}

    feature_vec, n_valid = extract_angle_feature_vector(video_path)
    if feature_vec is None:
        return {"error": f"Pose not detected reliably (only {n_valid} valid frames). "
                          f"Try a clearer, more front-on video."}

    user_seq = extract_normalized_pose_sequence(video_path)

    arm_result = classify(arm_model, arm_scaler, ARM_CLASSES, feature_vec)
    pace_result = classify(pace_model, pace_scaler, PACE_CLASSES, feature_vec)

    best_idx, best_dist = find_closest_match(user_seq, ref)
    matched_player = str(ref["players"][best_idx])
    metrics = comparison_metrics(user_seq, ref["sequences"][best_idx])

    return {
        "action_filter_confidence": action_conf,
        "arm_classification": arm_result,
        "pace_classification": pace_result,
        "closest_pro_match": {
            "player": matched_player,
            "dtw_distance": round(float(best_dist), 3),
            "note": "Lower distance = closer match. Meaningful only if your video's "
                    "camera angle matches the reference clip's angle.",
        },
        "comparison": metrics,
    }


def generate_annotated_video(video_path, output_path, panel_width=380):
    report = generate_report(video_path)
    if "error" in report:
        print(report["error"])
        return None, report

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    canvas_width = width + panel_width
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (canvas_width, height))

    arm, pace = report["arm_classification"], report["pace_classification"]
    match, comp = report["closest_pro_match"], report["comparison"]

    lines = [
        (f"{arm['label'].upper()} ARM / {pace['label'].upper()}", (255, 255, 255), 0.7, 2),
        (f"Arm conf: {arm['confidence']*100:.0f}%  Pace conf: {pace['confidence']*100:.0f}%",
         (180, 180, 180), 0.45, 1),
        ("", None, 0, 0),
        (f"Closest match: {match['player']}", (120, 255, 150), 0.55, 1),
        (f"Movement quality: {comp['movement_quality_similarity_pct']}%", (120, 210, 255), 0.5, 1),
        (f"Symmetry: {comp['symmetry_score']}", (120, 210, 255), 0.5, 1),
        ("", None, 0, 0),
        ("(approximate, single-angle reference)", (120, 120, 120), 0.4, 1),
    ]

    with mp_vision.PoseLandmarker.create_from_options(_video_options) as landmarker:
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(frame_idx * 1000 / fps)
            results = landmarker.detect_for_video(mp_image, timestamp_ms)
            if results.pose_landmarks:
                lm = results.pose_landmarks[0]
                pts = [(int(p.x * width), int(p.y * height)) for p in lm]
                for a, b in POSE_CONNECTIONS:
                    cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
                for x, y in pts:
                    cv2.circle(frame, (x, y), 3, (0, 200, 255), -1)

            canvas = np.zeros((height, canvas_width, 3), dtype=np.uint8)
            canvas[:, :width] = frame
            panel_x0 = width
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
            frame_idx += 1

    cap.release()
    out.release()

    h264_path = output_path.replace(".mp4", "_h264.mp4")
    cmd = (
        f'ffmpeg -y -loglevel error -i "{output_path}" '
        f'-vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" '
        f'-vcodec libx264 -pix_fmt yuv420p -movflags +faststart '
        f'"{h264_path}"'
    )
    ret_code = os.system(cmd)
    if ret_code != 0 or not os.path.exists(h264_path):
        print(f"ffmpeg conversion failed (exit code {ret_code}); returning raw output instead.")
        return output_path, report

    return h264_path, report



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    load_models()
    if args.annotate:
        annotated_path, report = generate_annotated_video(args.video, "annotated_report.mp4")
        if annotated_path:
            print(f"Annotated video saved: {annotated_path}")
    else:
        report = generate_report(args.video)

    print(json.dumps(report, indent=2))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"Report saved: {args.out}")


if __name__ == "__main__":
    main()
