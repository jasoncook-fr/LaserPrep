"""
main.py

LaserPrep application entry point.

Version 0.5
"""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from pdf_reader import read_pdf
from project import Project
from svg_writer import write_svg
from geometry_cleanup import (
    analyse,
    remove_zero_length_lines,
    remove_duplicate_lines,
)
from config import (
    DISPLAY_OFFSET_X_MM,
    DISPLAY_OFFSET_Y_MM,
    LARGE_USABLE_WIDTH_MM,
    LARGE_USABLE_HEIGHT_MM,
    SMALL_USABLE_WIDTH_MM,
    SMALL_USABLE_HEIGHT_MM,
)


# ============================================================
# Folder Selection
# ============================================================

def choose_folder() -> Path | None:
    """Ask the user to choose a folder containing PDF files."""

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(
        title="Select the folder containing the student PDF files"
    )

    root.destroy()

    if not folder:
        return None

    return Path(folder)


# ============================================================
# Main
# ============================================================

def main() -> None:

    folder = choose_folder()

    if folder is None:
        print("No folder selected.")
        return

    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    project = Project(folder.name)

    print("=" * 60)
    print(f"Project : {project.name}")
    print(f"PDFs    : {len(pdf_files)}")
    print("=" * 60)
    print()

    # ========================================================
    # Read every PDF
    # ========================================================

    for pdf in pdf_files:

        print(f"Reading {pdf.name}...")

        drawing = read_pdf(pdf)
        #drawing.geometry_report = geometry
        geometry = analyse(drawing)

        removed_zero = remove_zero_length_lines(drawing)

        removed_duplicates = remove_duplicate_lines(drawing)

        # ----------------------------------------------------
        # Decide whether rotation is required
        # ----------------------------------------------------

        rotated = False

        if not drawing.fits(
            LARGE_USABLE_WIDTH_MM,
            LARGE_USABLE_HEIGHT_MM,
        ):

            if drawing.fits_after_rotation(
                LARGE_USABLE_WIDTH_MM,
                LARGE_USABLE_HEIGHT_MM,
            ):

                drawing.rotate90()
                rotated = True

        # ----------------------------------------------------
        # Move drawing to display position
        # ----------------------------------------------------

        drawing.move_to(
            DISPLAY_OFFSET_X_MM,
            DISPLAY_OFFSET_Y_MM,
        )

        # ----------------------------------------------------
        # Add drawing to project
        # ----------------------------------------------------

        project.add(drawing)

        # ----------------------------------------------------
        # Validation report
        # ----------------------------------------------------

        print()
        print("Validation")
        print("-------------------------------------")

        print(
            f"Drawing Size : "
            f"{drawing.drawing_width:.2f} × "
            f"{drawing.drawing_height:.2f} mm"
        )

        print(
            f"Rotation     : "
            f"{'Applied' if rotated else 'Not required'}"
        )

        print(
            f"Large Laser  : "
            f"{'✓ YES' if drawing.fits(LARGE_USABLE_WIDTH_MM, LARGE_USABLE_HEIGHT_MM) else '✗ NO'}"
        )

        print(
            f"Small Laser  : "
            f"{'✓ YES' if drawing.fits(SMALL_USABLE_WIDTH_MM, SMALL_USABLE_HEIGHT_MM) else '✗ NO'}"
        )

        print()

        print("Geometry")
        print("-------------------------------------")
        print(f"Zero-length lines : {geometry.zero_length_lines}")
        print(f"Tiny segments     : {geometry.tiny_lines}")
        print(f"Duplicate lines   : {geometry.duplicate_lines}")

        if geometry.shortest_line_mm is not None:
            print(
                f"Shortest segment  : "
                f"{geometry.shortest_line_mm:.6f} mm"
            )
        print(f"Removed zero-length : {removed_zero}")
        print(f"Removed duplicates  : {removed_duplicates}")

        print()

    # ========================================================
    # Export SVG
    # ========================================================

    output_file = folder / f"{project.name}.svg"

    print("Writing SVG...")
    write_svg(project, output_file)

    print()
    print("=" * 60)
    print("Finished")
    print("=" * 60)
    print(f"Output : {output_file}")
    print()

    project.summary()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
