"""Bowling-vs-batting pre-check feature extraction (Task API). Generated from the
notebook's action-filter cell. (build_action_filter_model / train_action_filter are
only needed for retraining, not included here -- see the notebook.)"""
import os
import random
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from pose_utils import compute_frame_angles
from config import LM, ANGLE_NAMES, POSE_MODEL_PATH

POSITIVE_PREFIX = "Bowling_action"
NEGATIVE_PREFIX = "batting_stance"

_image_options = mp_vision.PoseLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=POSE_MODEL_PATH),
    running_mode=mp_vision.RunningMode.IMAGE,
    num_poses=1,
    min_pose_detection_confidence=0.4,
)

def extract_image_angle_features(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with mp_vision.PoseLandmarker.create_from_options(_image_options) as landmarker:
        res = landmarker.detect(mp_image)
    if not res.pose_landmarks:
        return None
    lm = res.pose_landmarks[0]
    frame = {name: (lm[idx].x, lm[idx].y, lm[idx].z, lm[idx].visibility)
             for name, idx in LM.items()}
    angles = compute_frame_angles(frame)
    return None if angles is None else np.array([angles[n] for n in ANGLE_NAMES], dtype="float32")


def index_action_dataset(image_dataset_dir=IMAGE_DATASET_DIR, max_per_class=1500):
    pos_paths, neg_paths = [], []
    for folder in sorted(os.listdir(image_dataset_dir)):
        folder_path = os.path.join(image_dataset_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        images = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                    images.append(os.path.join(root, f))

        if folder.startswith(POSITIVE_PREFIX):
            pos_paths += images
        elif folder.startswith(NEGATIVE_PREFIX):
            neg_paths += images

    random.seed(42)
    random.shuffle(pos_paths)
    random.shuffle(neg_paths)
    return pos_paths[:max_per_class], neg_paths[:max_per_class]


