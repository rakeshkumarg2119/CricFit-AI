"""
CricFit AI — Model Coordinator & Inference Service
==================================================
Provides unified interface to execute the three vision machine learning pipelines:
1. Batting Shot Classifier & Stage 2 DTW Biomechanical Comparison
2. Bowling Action Filter, Arm/Pace Classifiers & Pro Reference Matcher
3. Yo-Yo Shuttle Cadence Tracker & Rest Compliance Monitor
"""

import os
import sys
import uuid
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
VIDEOS_DIR = os.path.join(OUTPUTS_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

_batting_ready = False
_bowling_ready = False
_yoyo_ready = False


def _init_batting():
    global _batting_ready
    batting_dir = os.path.join(PROJECT_ROOT, "batting_model")
    if batting_dir not in sys.path:
        sys.path.insert(0, batting_dir)
    _batting_ready = True


def _init_bowling():
    global _bowling_ready
    bowling_dir = os.path.join(PROJECT_ROOT, "bowling_model")
    if bowling_dir not in sys.path:
        sys.path.insert(0, bowling_dir)
    _bowling_ready = True


def _init_yoyo():
    global _yoyo_ready
    yoyo_dir = os.path.join(PROJECT_ROOT, "yoyo_test_model")
    if yoyo_dir not in sys.path:
        sys.path.insert(0, yoyo_dir)
    _yoyo_ready = True


def analyze_batting(video_path: str, generate_video: bool = True) -> tuple:
    """
    Runs batting shot classification and biomechanical comparison.
    Returns: (raw_report_dict, annotated_video_path_or_None)
    """
    _init_batting()
    
    # Switch working dir temporarily so relative paths in batting_model resolve properly
    orig_cwd = os.getcwd()
    batting_dir = os.path.join(PROJECT_ROOT, "batting_model")
    try:
        os.chdir(batting_dir)
        import batting_pipeline
        
        annotated_video_path = None
        if generate_video:
            out_filename = f"batting_annotated_{uuid.uuid4().hex[:8]}.mp4"
            out_path = os.path.join(VIDEOS_DIR, out_filename)
            try:
                h264_path, report = batting_pipeline.generate_annotated_report_video(
                    video_path, output_path=out_path
                )
                annotated_video_path = h264_path if h264_path and os.path.exists(h264_path) else out_path
            except Exception as e:
                print(f"[WARN] Batting video annotation failed: {e}. Falling back to report only.")
                report = batting_pipeline.generate_report(video_path)
        else:
            report = batting_pipeline.generate_report(video_path)

        return report, annotated_video_path
    finally:
        os.chdir(orig_cwd)


def analyze_bowling(video_path: str, generate_video: bool = True) -> tuple:
    """
    Runs bowling action filter, arm/pace classifier, and pro match comparison.
    Returns: (raw_report_dict, annotated_video_path_or_None)
    """
    _init_bowling()
    
    orig_cwd = os.getcwd()
    bowling_dir = os.path.join(PROJECT_ROOT, "bowling_model")
    try:
        os.chdir(bowling_dir)
        import analyze_video as bowling_pipeline
        bowling_pipeline.load_models()

        annotated_video_path = None
        if generate_video:
            out_filename = f"bowling_annotated_{uuid.uuid4().hex[:8]}.mp4"
            out_path = os.path.join(VIDEOS_DIR, out_filename)
            try:
                h264_path, report = bowling_pipeline.generate_annotated_video(
                    video_path, output_path=out_path
                )
                annotated_video_path = h264_path if h264_path and os.path.exists(h264_path) else out_path
            except Exception as e:
                print(f"[WARN] Bowling video annotation failed: {e}. Falling back to report only.")
                report = bowling_pipeline.generate_report(video_path)
        else:
            report = bowling_pipeline.generate_report(video_path)

        return report, annotated_video_path
    finally:
        os.chdir(orig_cwd)


def analyze_yoyo(video_path: str, manual_input: dict = None, reference: dict = None) -> tuple:
    """
    Runs Yo-Yo shuttle cadence tracking and 10s rest compliance verification.
    Returns: (raw_report_dict, None)
    """
    _init_yoyo()
    manual_input = manual_input or {"yoyo_level": "16.5"}
    reference = reference or {"target_board": "BCCI", "target_yoyo_score": 16.5}

    orig_cwd = os.getcwd()
    yoyo_dir = os.path.join(PROJECT_ROOT, "yoyo_test_model")
    try:
        os.chdir(yoyo_dir)
        import video_pipeline as yoyo_pipeline
        
        # Point to pose landmarker
        pose_model_path = os.path.join(PROJECT_ROOT, "batting_model", "pose_landmarker.task")
        if not os.path.exists(pose_model_path):
            pose_model_path = os.path.join(yoyo_dir, "pose_landmarker_lite.task")
            
        report = yoyo_pipeline.analyze_video_file(
            video_path=video_path,
            manual_input=manual_input,
            reference=reference,
            model_path=pose_model_path
        )
        return report, None
    finally:
        os.chdir(orig_cwd)
