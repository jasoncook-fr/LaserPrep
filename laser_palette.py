"""
laser_palette.py

Official LaserPrep colour palette.

Version 0.7
"""
from config import COLOUR_TOLERANCE

# ============================================================
# OFFICIAL LASER COLOURS
# ============================================================

OFFICIAL_LASER_COLORS = {

    "BLACK":   (0,   0,   0),

    "RED":     (255, 0,   0),
    "GREEN":   (0,   255, 0),
    "BLUE":    (0,   0,   255),

    "CYAN":    (0,   255, 255),
    "MAGENTA": (255, 0,   255),
    "YELLOW":  (255, 255, 0),
}

# ============================================================
# REVERSE LOOKUP
# ============================================================

RGB_TO_NAME = {
    rgb: name
    for name, rgb in OFFICIAL_LASER_COLORS.items()
}

# ============================================================
# HELPERS
# ============================================================

def is_official(rgb):
    """
    Returns True if the RGB tuple is one of the
    official laser colours.
    """

    return rgb in OFFICIAL_LASER_COLORS.values()

def colour_name(rgb):
    """
    Returns the official laser colour name.

    Returns None if the colour is not official.
    """

    return RGB_TO_NAME.get(rgb)

# ============================================================
# NEAREST OFFICIAL COLOUR CLASSIFIER
# ============================================================

def classify_colour(rgb):
    """
    Returns:

        (status, name, distance)

    status is one of:

        "OFFICIAL"
        "NEAR"
        "UNSUPPORTED"
    """

    # Exact match

    name = colour_name(rgb)

    if name is not None:
        return ("OFFICIAL", name, 0.0)

    best_name = None
    best_distance = None

    r1, g1, b1 = rgb

    for name, rgb2 in OFFICIAL_LASER_COLORS.items():

        r2, g2, b2 = rgb2

        distance = (
            (r1-r2)**2 +
            (g1-g2)**2 +
            (b1-b2)**2
        ) ** 0.5

        if (
            best_distance is None
            or
            distance < best_distance
        ):
            best_distance = distance
            best_name = name

    if best_distance <= COLOUR_TOLERANCE:
        return ("NEAR", best_name, best_distance)

    return ("UNSUPPORTED", None, best_distance)

def snap_colour(rgb):
    """
    Returns the colour that should be used by LaserPrep.

    OFFICIAL:
        Returned unchanged.

    NEAR:
        Snapped to the official laser colour.

    UNSUPPORTED:
        Returned unchanged.
    """

    status, name, distance = classify_colour(rgb)

    if status == "OFFICIAL":
        return rgb

    if status == "NEAR":
        return OFFICIAL_LASER_COLORS[name]

    return rgb
