"""
report.py

LaserPrep operator report.

Version 1.0
"""

from pathlib import Path


def _yes_no(value: bool) -> str:
    return "PASS" if value else "FAIL"


def write_report(report, filename: str) -> None:
    """
    Write the LaserPrep operator report.

    Parameters
    ----------
    report
        GeometryReport (or LaserPrepReport in the future).

    filename
        Output report filename.
    """

    lines = []

    lines.append("LaserPrep Report")
    lines.append("=" * 60)
    lines.append("")

    #
    # GENERAL INFORMATION
    #

    lines.append("GENERAL INFORMATION")
    lines.append("-" * 60)

    if hasattr(report, "input_file"):
        lines.append(f"Input file           : {report.input_file}")

    if hasattr(report, "page_width_mm"):
        lines.append(
            f"Page size            : "
            f"{report.page_width_mm:.2f} × "
            f"{report.page_height_mm:.2f} mm"
        )

    if hasattr(report, "machine_width_mm"):
        lines.append(
            f"Laser bed            : "
            f"{report.machine_width_mm:.0f} × "
            f"{report.machine_height_mm:.0f} mm"
        )

    if hasattr(report, "machine_fits"):
        lines.append(
            f"Machine size check   : "
            f"{_yes_no(report.machine_fits)}"
        )

    if hasattr(report, "object_count"):
        lines.append(
            f"Objects              : {report.object_count}"
        )

    if hasattr(report, "path_count"):
        lines.append(
            f"Paths                : {report.path_count}"
        )

    if hasattr(report, "bezier_count"):
        lines.append(
            f"Bezier curves        : {report.bezier_count}"
        )

    if hasattr(report, "raster_images"):
        lines.append(
            f"Raster images        : {report.raster_images}"
        )

    if hasattr(report, "live_text"):
        lines.append(
            f"Live text            : {report.live_text}"
        )

    lines.append("")

    #
    # CLEANUP
    #

    lines.append("CLEANUP")
    lines.append("-" * 60)

    if hasattr(report, "removed_zero_length"):
        lines.append(
            f"Removed zero-length  : {report.removed_zero_length}"
        )

    if hasattr(report, "removed_duplicates"):
        lines.append(
            f"Removed duplicates   : {report.removed_duplicates}"
        )

    if hasattr(report, "colours_corrected"):
        lines.append(
            f"Colours corrected    : {report.colours_corrected}"
        )

    lines.append("")

    #
    # ATTENTION
    #

    attention = []

    if getattr(report, "near_overlap_candidates", 0):
        attention.append(
            f"Near-overlapping geometry "
            f"({report.near_overlap_candidates} candidates)"
        )

    if getattr(report, "machine_fits", True) is False:
        attention.append(
            "Drawing exceeds laser machine dimensions."
        )

    if getattr(report, "live_text", 0):
        attention.append(
            "Live text remains in the drawing."
        )

    if getattr(report, "raster_images", 0):
        attention.append(
            "Raster images detected."
        )

    lines.append("ATTENTION")
    lines.append("-" * 60)

    if attention:

        for item in attention:
            lines.append(f"- {item}")

    else:

        lines.append("No operator attention required.")

    lines.append("")

    Path(filename).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
