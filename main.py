"""
main.py

LaserPrep application entry point.

Version 0.5
"""
from geometry_chains import analyse as analyse_chains
from geometry_statistics import analyse as geometry_statistics
from topology import build_paths
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from text_import import import_text
from pdf_reader import read_pdf
from project import Project
from svg_writer import write_svg
from color_analysis import analyse_colors
from colour_normalization import normalize_colours
from diagnostics import diag
from geometry_cleanup import (
    analyse,
    remove_zero_length_lines,
    remove_duplicate_lines,
)
from config import (
    BATCH_ROOT,
    DISPLAY_OFFSET_X_MM,
    DISPLAY_OFFSET_Y_MM,
    LARGE_USABLE_WIDTH_MM,
    LARGE_USABLE_HEIGHT_MM,
    SMALL_USABLE_WIDTH_MM,
    SMALL_USABLE_HEIGHT_MM,
)
from debug_manager import DebugManager
from config import DEBUG

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

def process_project(folder: Path) -> None:
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {folder}")
        return

    project = Project(folder.name)
    debug = DebugManager(DEBUG)
    debug.start_run(project.name)
    diag.begin(project, folder)

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

        stats = drawing.pdf_statistics

        debug.save_text(
            f"{pdf.stem}_01_pdf_analysis.txt",
            "\n".join([
                f"Paths       : {stats['paths']}",
                f"Objects     : {stats['objects']}",
                f"Unsupported : {stats['unsupported']}",
            ])
        )

        diag.export_svg(
            drawing,
            f"{pdf.stem}.geometry_raw.svg",
        )
        debug.save_svg(
            diag.debug_folder / f"{pdf.stem}.geometry_raw.svg",
            "02_geometry.svg"
        )
        import_text(
            drawing,
            pdf,
        )

        build_paths(drawing)

        diag.export_svg(
            drawing,
            f"{pdf.stem}.merged_before_move.svg",
        )

        #drawing.geometry_report = geometry
        geometry = analyse(drawing)

        colors = analyse_colors(drawing)

        # ----------------------------------------------------
        # Choose the best orientation
        # ----------------------------------------------------

        rotated, normal_overflow, rotated_overflow = (
            drawing.choose_best_orientation(
                LARGE_USABLE_WIDTH_MM,
                LARGE_USABLE_HEIGHT_MM,
            )
        )

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
            f"Orientation  : "
            f"{'Rotated' if rotated else 'Original'}"
        )

        print(
            f"Overflow     : "
            f"{min(normal_overflow, rotated_overflow):.2f} mm"
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
        print()

        print("Colours")
        print("-------------------------------------")

        for name, count in colors.official.items():

            if count > 0:

                print(f"{name:<10} : {count}")

        print()

        if colors.near:

            print("Near Official Colours")
            print("-------------------------------------")

            for rgb, info in sorted(colors.near.items()):

                print(
                    f"{rgb} -> {info['target']} : "
                    f"{info['count']}"
                )

            print()

        if colors.unsupported:

            print("Unsupported Colours")
            print("-------------------------------------")

            for rgb, count in sorted(colors.unsupported.items()):

                print(f"{rgb} : {count}")

            print()

        # ----------------------------------------------------
        # Apply modifications after analysis/reporting
        # ----------------------------------------------------

        normalization = normalize_colours(drawing)

        if rotated:
            # already rotated above
            pass

        removed_zero = remove_zero_length_lines(drawing)
        removed_duplicates = remove_duplicate_lines(drawing)
        build_paths(drawing)

        print("Cleanup")
        print("-------------------------------------")
        print(f"Removed zero-length : {removed_zero}")
        print(f"Removed duplicates  : {removed_duplicates}")
        print(f"Colours corrected   : {normalization.corrected}")
        print()

        stats = geometry_statistics(drawing)

        print()
        print("Geometry Statistics")
        print("-------------------------------------")
        print(f"Total lines     : {stats.total_lines}")
        print(f"< 0.01 mm       : {stats.lt_001}")
        print(f"0.01-0.05 mm    : {stats.lt_005}")
        print(f"0.05-0.10 mm    : {stats.lt_010}")
        print(f"0.10-0.50 mm    : {stats.lt_050}")
        print(f"0.50-1.00 mm    : {stats.lt_100}")
        print(f"> 1.00 mm       : {stats.gt_100}")

        chains = analyse_chains(drawing)

        print()
        print("Geometry Chains")
        print("-------------------------------------")
        print(f"Total chains        : {chains.total_chains}")
        print(f"Longest chain       : {chains.longest_chain}")

        if chains.total_chains:

            avg = chains.total_segments / chains.total_chains

        else:

            avg = 0

        print(f"Average chain       : {avg:.1f}")

        print()
        print("Distribution")
        print(f"1 segment           : {chains.one}")
        print(f"2 - 5 segments      : {chains.two_to_five}")
        print(f"6 - 20 segments     : {chains.six_to_twenty}")
        print(f"21 - 100 segments   : {chains.twentyone_to_hundred}")
        print(f"> 100 segments      : {chains.over_hundred}")

    # ========================================================
    # Export SVG
    # ========================================================

    output_file = folder / f"{project.name}.svg"

    print("Writing SVG...")
    write_svg(project, output_file)
    diag.export_file(output_file)
    debug.save_svg(diag.debug_folder / output_file.name, "05_final.svg")

    print()
    print("=" * 60)
    print("Finished")
    print("=" * 60)
    print(f"Output : {output_file}")
    print()

    debug.finish()
    diag.end()
    project.summary()

def main() -> None:

    print("=" * 44)
    print("LaserPrep")
    print("=" * 44)
    print()
    print("1 - Testing Mode")
    print("    Choose one folder and process only PDFs in that folder.")
    print()
    print("2 - Batch Mode")
    print("    Process every project under BATCH_ROOT.")
    print()
    print("Q - Quit")
    print()

    choice = input("Choice: ").strip().lower()

    if choice == "q":
        return

    if choice == "1":
        folder = choose_folder()
        if folder is None:
            print("No folder selected.")
            return
        process_project(folder)
        return

    if choice == "2":
        root = Path(BATCH_ROOT)

        if not root.exists():
            print(f"Batch root does not exist: {root}")
            return

        projects = sorted(
            p for p in root.rglob("*")
            if p.is_dir() and any(p.glob("*.pdf"))
        )

        if not projects:
            print("No projects found.")
            return

        print(f"Found {len(projects)} projects.")

        for i, folder in enumerate(projects, start=1):
            print("=" * 60)
            print(f"Project {i} / {len(projects)}")
            print(folder)
            print("=" * 60)
            process_project(folder)
        return

    print("Invalid choice.")


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()












