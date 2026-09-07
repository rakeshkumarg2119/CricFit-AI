"""
Yo-Yo IR1 protocol reference table, adapted from Bangsbo, Iaia & Krustrup
(2008), "The Yo-Yo Intermittent Recovery Test: A Useful Tool for Evaluation
of Physical Performance in Intermittent Sports", Sports Med 38(1):37-51.

Each speed level has N shuttles (2 x 20m each) at a fixed speed before the
next speed step. A reported score like "16.3" means speed level 16, 3rd
shuttle at that speed - keyed here as (speed_level, shuttle_in_level).

This is pure reference data + lookup, kept separate from tracking/vision
logic since it never touches a frame or a landmark.
"""

# (speed_level, shuttles_in_level, speed_kmh)
_YOYO_IR1_SPEED_STAGES = [
    (5, 1, 10.0),
    (9, 1, 12.0),
    (11, 2, 13.0),
    (12, 3, 13.5),
    (13, 4, 14.0),
    (14, 8, 14.5),
    (15, 8, 15.0),
    (16, 8, 15.5),
    (17, 8, 16.0),
    (18, 8, 16.5),
    (19, 8, 17.0),
    (20, 8, 17.5),
    (21, 8, 18.0),
    (22, 8, 18.5),
    (23, 8, 19.0),
]


def _build_yoyo_ir1_table():
    table = {}
    global_shuttle_count = 0
    for speed_level, n_shuttles, speed_kmh in _YOYO_IR1_SPEED_STAGES:
        for shuttle_in_level in range(1, n_shuttles + 1):
            global_shuttle_count += 1
            table[(speed_level, shuttle_in_level)] = {
                "speed_kmh": speed_kmh,
                "distance_m": global_shuttle_count * 40,  # 2 x 20m per shuttle
                "cumulative_shuttle_number": global_shuttle_count,
            }
    return table


# Table covers up to score 23.8 / 3640m (elite-range). Scores beyond that
# aren't in the published protocol table and return a "beyond tabulated
# range" note rather than a guessed number.
YOYO_IR1_LEVEL_TABLE = _build_yoyo_ir1_table()


def parse_level_shuttle(yoyo_level: str):
    """'16.3' -> (16, 3). Returns None if it doesn't parse as level.shuttle."""
    try:
        text = str(yoyo_level).strip()
        speed_level_str, shuttle_str = text.split(".")
        return int(speed_level_str), int(shuttle_str)
    except (ValueError, AttributeError):
        return None


def lookup_level_reference(yoyo_level: str):
    """Looks up speed/distance for a reported level.shuttle score against
    the Yo-Yo IR1 protocol table. Returns explicit None + note on anything
    that doesn't resolve, rather than guessing."""
    if yoyo_level is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None, "note": "no yoyo_level given"}

    parsed = parse_level_shuttle(yoyo_level)
    if parsed is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None,
                "note": f"'{yoyo_level}' isn't in level.shuttle format (e.g. '16.3')"}

    entry = YOYO_IR1_LEVEL_TABLE.get(parsed)
    if entry is None:
        return {"speed_kmh": None, "distance_m": None,
                "cumulative_shuttle_number": None,
                "note": f"score {yoyo_level} is outside the tabulated YYIR1 "
                        f"range (table covers up to 23.8 / 3640m) - "
                        f"double check the reported score"}
    return {**entry, "note": None}
