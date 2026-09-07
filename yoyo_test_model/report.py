"""
Turns raw segmentation output (legs) + per-leg cadence stats into the final
JSON report: pairs legs into shuttles, checks rest-window compliance,
computes a shuttle-over-shuttle cadence trend, and cross-checks against the
manually-reported Yo-Yo score.

Kept separate from ShuttleCadenceTracker so the report-assembly logic (pure
dict-building, no vision/tracking) can be read, tested, and changed without
touching pose capture or segmentation.
"""

from datetime import datetime, timezone

import numpy as np

try:
    from . import config
    from .cadence import cadence_in_range
    from .yoyo_protocol import lookup_level_reference
except (ImportError, ValueError):
    import config
    from cadence import cadence_in_range
    from yoyo_protocol import lookup_level_reference


def build_report(legs, ankle_diff_series, body_scale_series, timestamps, fps,
                  last_signal_used, frames_processed, manual_input, reference=None):
    """
    legs: output of segmentation.segment_movement() - list of
          (start_idx, end_idx, direction).
    manual_input: {"yoyo_level": "16.3", "measured_test_duration_sec": optional}
    reference: optional {"target_board": "BCCI", "target_yoyo_score": 17.1}
    """
    max_body_scale = float(np.max(body_scale_series)) if len(body_scale_series) > 0 else None

    # pair consecutive legs into shuttles (out + back = 1 shuttle); an odd
    # leg left over at the end (test cut off mid-shuttle) is kept as a
    # partial and flagged, not silently merged or dropped.
    shuttle_reports = []
    direction_anomaly = False
    for i in range(0, len(legs) - 1, 2):
        out_leg, back_leg = legs[i], legs[i + 1]
        if out_leg[2] == back_leg[2]:
            # two legs in a row went the same direction - segmentation
            # likely split one real leg into two (e.g. a mid-sprint
            # stumble briefly dropped below the speed threshold)
            direction_anomaly = True
        out_stats = cadence_in_range(out_leg[0], out_leg[1], ankle_diff_series, timestamps, fps,
                                      body_scale_series, max_body_scale)
        back_stats = cadence_in_range(back_leg[0], back_leg[1], ankle_diff_series, timestamps, fps,
                                       body_scale_series, max_body_scale)
        shuttle_reports.append({
            "shuttle_index": len(shuttle_reports) + 1,
            "out_leg": out_stats,
            "back_leg": back_stats,
            "combined_cadence": round((out_stats["cadence"] + back_stats["cadence"]) / 2, 2),
        })

    partial_leg_flag = (len(legs) % 2 == 1)

    # Recovery windows are measured directly between the end of each
    # back-leg and the start of the next out-leg - this skips cone turns
    # (out->back gaps), the idle wait before the first sprint, and the tail
    # after the last one, none of which are recoveries.
    #
    # Direction of the check: the beep schedule is 40m / level-speed + 10s
    # recovery, so a player at-or-above beep pace produces gaps >= ~10s. A
    # gap notably UNDER 10s means the player was LATE back to the line and
    # cut into the mandatory recovery - that's the violation. Gaps OVER 10s
    # are fine: the player finished faster than beep pace and idled.
    rest_gaps_sec = [
        round(float(timestamps[legs[i + 1][0]] - timestamps[legs[i][1]]), 2)
        for i in range(1, len(legs) - 1, 2)
    ]
    late_recoveries = [g for g in rest_gaps_sec if g < config.REST_WINDOW_SEC - config.LATE_TOLERANCE_SEC]

    rest_compliance = {
        "rest_gaps_sec": rest_gaps_sec,
        "late_recovery_count": len(late_recoveries),
        "all_recoveries_ok": (len(late_recoveries) == 0) if rest_gaps_sec else None,
        "note": "Gaps notably UNDER 10s mean the player was late back to "
                "the line and cut into the mandatory recovery - flag for "
                "review, not an automatic fail call. Gaps OVER 10s are "
                "NOT a violation: the player finished that shuttle faster "
                "than beep pace and idled until the next beep.",
    }

    if len(shuttle_reports) >= 2:
        first_cadence = shuttle_reports[0]["combined_cadence"]
        last_cadence = shuttle_reports[-1]["combined_cadence"]
        if last_cadence < first_cadence * 0.9:
            trend = "declining"
        elif last_cadence > first_cadence * 1.1:
            trend = "increasing"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    yoyo_level = manual_input.get("yoyo_level")
    measured_duration = manual_input.get("measured_test_duration_sec")
    video_duration = round(float(timestamps[-1] - timestamps[0]), 1) if len(timestamps) > 1 else 0.0

    duration_cross_check = None
    if measured_duration is not None and video_duration > 0:
        duration_cross_check = {
            "measured_test_duration_sec": measured_duration,
            "video_analyzed_duration_sec": video_duration,
            "discrepancy_sec": round(float(measured_duration - video_duration), 1),
        }

    level_reference = lookup_level_reference(yoyo_level)
    shuttle_count_cross_check = None
    expected_shuttles = level_reference.get("cumulative_shuttle_number")
    if expected_shuttles is not None:
        detected = len(shuttle_reports)
        shuttle_count_cross_check = {
            "expected_from_reported_score": expected_shuttles,
            "detected_in_video": detected,
            "note": (
                "video shuttle count is lower than expected - clip likely "
                "starts mid-test or misses some reps"
                if detected < expected_shuttles else
                "video shuttle count exceeds expected - check the reported "
                "score, or the clip includes warm-up shuttles before the "
                "test proper started"
                if detected > expected_shuttles else
                "matches reported score"
            ),
        }

    pose_detection = {
        "frames_processed": frames_processed,
        "frames_with_pose": len(timestamps),
        "frames_without_pose": frames_processed - len(timestamps),
    }

    reference = reference or {}
    target_score = reference.get("target_yoyo_score")
    comparison = {"meets_target": None, "gap_to_target": None}
    if target_score is not None and yoyo_level is not None:
        try:
            # NOTE: level.shuttle notation (e.g. 16.8) compares correctly as
            # a plain float as long as shuttle count per level stays
            # single-digit (true for the standard IR1 protocol).
            current_numeric = float(yoyo_level)
            target_numeric = float(target_score)
            comparison["meets_target"] = current_numeric >= target_numeric
            comparison["gap_to_target"] = round(target_numeric - current_numeric, 2)
        except (TypeError, ValueError):
            pass

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manual_input": {
            "yoyo_level": yoyo_level,
            "duration_cross_check": duration_cross_check,
        },
        "level_reference": level_reference,
        "shuttle_count_cross_check": shuttle_count_cross_check,
        "pose_detection": pose_detection,
        "shuttle_metrics": {
            "motion_signal_used": last_signal_used,
            "shuttles_detected": len(shuttle_reports),
            "partial_leg_at_end": partial_leg_flag,
            "direction_anomaly_detected": direction_anomaly,
            "cadence_trend": trend,
            "shuttles": shuttle_reports,
        },
        "rest_compliance": rest_compliance,
        "reference": reference,
        "comparison": comparison,
    }
