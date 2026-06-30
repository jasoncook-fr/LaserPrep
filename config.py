# ============================================================
# LARGE LASER
# ============================================================

LARGE_BED_WIDTH_MM = 1000.0
LARGE_BED_HEIGHT_MM = 600.0

DISPLAY_OFFSET_X_MM = 10.0
DISPLAY_OFFSET_Y_MM = 10.0

LARGE_USABLE_WIDTH_MM = LARGE_BED_WIDTH_MM - (2 * DISPLAY_OFFSET_X_MM)
LARGE_USABLE_HEIGHT_MM = LARGE_BED_HEIGHT_MM - (2 * DISPLAY_OFFSET_Y_MM)


# ============================================================
# SMALL LASER
# ============================================================

SMALL_BED_WIDTH_MM = 700.0
SMALL_BED_HEIGHT_MM = 500.0

SMALL_USABLE_WIDTH_MM = SMALL_BED_WIDTH_MM - (2 * DISPLAY_OFFSET_X_MM)
SMALL_USABLE_HEIGHT_MM = SMALL_BED_HEIGHT_MM - (2 * DISPLAY_OFFSET_Y_MM)


# ============================================================
# DISPLAY
# ============================================================

DISPLAY_STROKE_WIDTH_MM = 0.20
LASER_STROKE_WIDTH_MM = 0.01

# ============================================================
# LASER COLOUR CONFIGURATION
# ============================================================

# Maximum RGB distance for automatic colour recognition.
#
# Colours farther away than this are considered unsupported.
#
# Increase this if student files frequently contain
# slightly incorrect colours.
#
# Decrease it if you want stricter validation.

FIT_TOLERANCE_MM = 1.0
COLOUR_TOLERANCE = 25.0
