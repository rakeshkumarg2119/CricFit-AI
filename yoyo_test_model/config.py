"""
All tuning knobs and fixed constants live here, in one place. When tuning
against new footage (different camera distance/angle/fps), this is the only
file that should need editing.
"""

# --- pose landmark indices (MediaPipe Pose) ---
LEFT_ANKLE, RIGHT_ANKLE = 27, 28
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12

DEFAULT_MODEL_PATH = "pose_landmarker_lite.task"

# --- test-structure constants (fixed by the Yo-Yo IR1 protocol itself) ---
SHUTTLE_LEG_M = 20.0          # one-way distance between the two lines
REST_WINDOW_SEC = 10.0        # mandatory recovery window between shuttles

# how far under the 10s window a recovery gap can fall before it is counted
# as "late back to the line". Absorbs frame-quantization + pose jitter
# around the turn moment. NOT part of the official protocol - a
# measurement-noise allowance only.
LATE_TOLERANCE_SEC = 1.5

# --- step-cadence knobs ---
MIN_STEP_INTERVAL_SEC = 0.25

# peak prominence floor for step detection - only matters for legs with an
# almost-flat bob (very distant camera), where nothing meaningful can be
# detected anyway. Prominence is otherwise scaled per-leg to that leg's own
# ankle-bob amplitude (see cadence.cadence_in_range).
CADENCE_PROMINENCE_FLOOR = 0.004

# below this % of the session's largest observed body_scale, a leg's
# cadence is flagged "low confidence" rather than reported as a bare
# number - at that distance from camera, ankle landmarks are only a few
# pixels apart and individual footfalls aren't reliably resolvable.
# Confirmed by manually reviewing real footage frame-by-frame before
# adding this - see cadence.py docstring.
CADENCE_CONFIDENCE_THRESHOLD_PCT = 50.0

# --- segmentation knobs (extrema + average-rate based - see segmentation.py) ---
SIGNAL_SMOOTH_WINDOW_SEC = 0.2     # LIGHT smoothing for rate/displacement
                                    # math - deliberately short so it
                                    # doesn't blur a real short leg
                                    # (~1-1.5s).

# SEPARATE, heavier smoothing used ONLY to locate turn-points, not for rate
# calc. Running gait (arm swing/torso rotation) wobbles body_scale and
# hip_x every stride; on a lightly-smoothed signal that wobble registers as
# fake turn-points mid-sprint, chopping one real leg into fragments too
# short/slow to individually clear LEG_AVG_RATE_THRESHOLD or
# MIN_LEG_DURATION_SEC. A real turn is one event spanning well over a full
# gait cycle, so it's safe to blur across strides when just LOOKING for
# turns, even though that blurring is wrong for the rate math itself.
TURN_POINT_SMOOTH_WINDOW_SEC = 0.6

# minimum spacing (seconds) enforced between accepted turn-points. A real
# out-leg or back-leg takes >= ~1s even at the fastest levels - two "turns"
# closer than that are gait wobble, not two real direction changes.
TURN_POINT_MIN_SPACING_SEC = 1.0

LEG_AVG_RATE_THRESHOLD = 0.06      # body-scale units/sec, averaged over a
                                    # whole candidate leg (displacement /
                                    # duration) - NOT an instantaneous/
                                    # smoothed derivative. Distinguishes a
                                    # sprint leg from the slower rest-walk
                                    # between two turn points. Tune per
                                    # camera distance/framing: too low =
                                    # rest-walk counted as a leg, too high =
                                    # a genuine but shorter/farther-out leg
                                    # misses it.

MIN_REST_DURATION_SEC = 1.5        # a "paused" stretch shorter than this is
                                    # just the cone turn, not the 10s
                                    # recovery

MIN_LEG_DISPLACEMENT = 0.03        # body-scale distance a "moving" segment
                                    # must cover to count as a real leg, not
                                    # camera jitter or a stumble-in-place

MIN_LEG_DURATION_SEC = 1.0          # a real 20m sprint leg takes at least
                                    # ~1-1.5s even at the fastest levels -
                                    # anything shorter that still cleared
                                    # the displacement check is a noise
                                    # blip, not an actual leg
