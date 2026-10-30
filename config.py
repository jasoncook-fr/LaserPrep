# ============================================================
# LASERPREP CONFIGURATION
# Version : 2.2B
# Milestone : 1.1 - Diagnostics Infrastructure
# ============================================================
from pathlib import Path

# declare batch processing ADMIN folders
HOME = Path.home()
REPORT_RETENTION_DAYS = 7

BATCH_ROOT = HOME / "Nextcloud" / "LaserPrep" / "STUDENTS"
ADMIN_ROOT = HOME / "Nextcloud" / "LaserPrep" / "ADMIN"

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
DISPLAY_STROKE_WIDTH_MM = 0.01
LASER_STROKE_WIDTH_MM = 0.01

# ============================================================
# LASER COLOUR CONFIGURATION
# ============================================================
FIT_TOLERANCE_MM = 1.0
COLOUR_TOLERANCE = 25.0

# ============================================================
# Complexity Analysis
# ============================================================
COMPLEXITY_WARNING_OBJECTS = 20000
COMPLEXITY_HIGH_OBJECTS = 100000
COMPLEXITY_ABORT_OBJECTS = 250000
# Estimated vector point complexity in the source PDF.
# Used for early rejection before SVG export/import.
COMPLEXITY_WARNING_POINTS = 250000
COMPLEXITY_HIGH_POINTS = 1000000
COMPLEXITY_ABORT_POINTS = 2000000

# ============================================================
# Suspiciously small / densely detailed PDF detection
# ============================================================
SUSPECT_SCALE_MAX_MM = 200.0
SUSPECT_SCALE_MIN_OBJECTS = 2000

# ============================================================
# DIAGNOSTICS
# ============================================================
DEBUG_MODE = True
DEBUG_REPORT = True
DEBUG_EXPORT_GEOMETRY = True
DEBUG_EXPORT_TEXT = True
DEBUG_EXPORT_MERGED = True
DEBUG_COLOUR_GEOMETRY = (0, 0, 255)
DEBUG_COLOUR_TEXT = (255, 0, 0)
SOFTWARE_STAMP_MIN_GLYPHS = 20
SOFTWARE_STAMP_MIN_WIDTH_MM = 40.0
SOFTWARE_STAMP_MIN_HEIGHT_MM = 2.0
SOFTWARE_STAMP_MAX_HEIGHT_MM = 4.5

# ============================================================
# COLLINEAR OVERLAP DIAGNOSTIC
# ============================================================
# Same-colour straight lines are flagged when they are almost
# parallel, physically close, and substantially overlapping.
# These values are diagnostic thresholds only; no geometry is
# automatically modified by this detector.
COLLINEAR_ANGLE_TOLERANCE_DEG = 1.0
COLLINEAR_SEPARATION_TOLERANCE_MM = 0.50
COLLINEAR_MIN_SEGMENT_LENGTH_MM = 1.00
COLLINEAR_MIN_OVERLAP_RATIO = 0.80
# ------------------------------------------------------------
# Collinear / redundant geometry warning thresholds
# ------------------------------------------------------------
# Number of non-exact overlap groups before a warning is issued.
COLLINEAR_OVERLAP_WARNING_GROUPS = 100
# Number of non-exact overlap groups at which the file is rejected.
COLLINEAR_OVERLAP_REJECT_GROUPS = 700

# Optional nearest-neighbour ordering of disconnected laser-cutting strokes.
OPTIMIZE_CUT_ORDER = True
