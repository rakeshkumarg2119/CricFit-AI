"""Bowling analysis model package. Import surface for the backend.

Usage:
    from bowling_model import load_models, generate_report, generate_annotated_video

    load_models()  # once, at server startup
    report = generate_report(video_path)
"""
from .analyze_video import load_models, generate_report, generate_annotated_video

__all__ = ["load_models", "generate_report", "generate_annotated_video"]