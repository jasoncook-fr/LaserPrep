# ============================================================
# LASERPREP CONFIGURATION
# Version : 2.2B
# Milestone : 1.1 - Diagnostics Infrastructure
# ============================================================
from pathlib import Path

# declare batch processing folder
BATCH_ROOT = Path("/home/jaz/Nextcloud/Dev/ENSAM/TMP/TEST_FILES")

# -------------------------------------------------------------
# Debug
# -------------------------------------------------------------

DEBUG = True

# ============================================================
# LARGE LASER
# ============================================================

LARGE_BED_WIDTH_MM = 1000.0
LARGE_BED_HEIGHT_MM = 600.0

DISPLAY_OFFSET_X_MM = 5.0
DISPLAY_OFFSET_Y_MM = 5.0

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

# ============================================================
# Complexity Analysis
# ============================================================

# Number of imported vector objects before warning the operator.
COMPLEXITY_WARNING_OBJECTS = 20000

# Number of imported vector objects considered unusually high.
COMPLEXITY_HIGH_OBJECTS = 100000

# Maximum number of imported vector objects LaserPrep will attempt
# to process. Files above this limit are rejected.
COMPLEXITY_ABORT_OBJECTS = 250000


# ============================================================
# DIAGNOSTICS
# ============================================================

# Master switch for the Diagnostics subsystem.
#
# False:
#     LaserPrep behaves exactly as the production version.
#
# True:
#     Additional diagnostic information is generated.
#
# NOTE:
#     During Milestone 1.1 this only enables the framework.
#     Later milestones will generate:
#
#       debug/
#           report.txt
#           geometry_raw.svg
#           text_raw.svg
#           merged_raw.svg
#

DEBUG_MODE = True


# Write a detailed report.txt
DEBUG_REPORT = True


# Export intermediate SVG files.
#
# (Not used yet in Milestone 1.1.)
DEBUG_EXPORT_GEOMETRY = True
DEBUG_EXPORT_TEXT = True
DEBUG_EXPORT_MERGED = True


# Override colours in exported debug SVGs.
#
# Geometry -> Blue
# Text     -> Red
#
# (Implemented in a later milestone.)

DEBUG_COLOUR_GEOMETRY = (0, 0, 255)
DEBUG_COLOUR_TEXT = (255, 0, 0)

SOFTWARE_STAMP_MIN_GLYPHS = 20
SOFTWARE_STAMP_MIN_WIDTH_MM = 40.0
SOFTWARE_STAMP_MIN_HEIGHT_MM = 2.0
SOFTWARE_STAMP_MAX_HEIGHT_MM = 4.5
