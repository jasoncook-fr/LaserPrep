"""
main.py

LaserPrep application entry point.

Version 0.5
"""
from batch_alerts import BatchAlerts
from complexity import analyse_complexity
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
from report import Report
from report_dev import DeveloperReport

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

def process_project(
    folder: Path,
    alerts: BatchAlerts | None = None,
) -> None:
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {folder}")
        return

    project = Project(folder.name)
    report = Report()
    dev_report = DeveloperReport()
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

        report.begin_file(pdf.name)
        dev_report.begin_file(pdf.name)

        print(f"Reading {pdf.name}...")

        drawing = read_pdf(pdf)

        complexity = analyse_complexity(drawing)

        report.complexity(complexity)
        dev_report.complexity(complexity)

        if complexity.should_abort:

            if alerts is not None:
                alerts.abort(
                    project.name,
                    pdf.name,
                    "Drawing complexity exceeds the allowed limit."
                )

            continue

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
        # Validation report
        # ----------------------------------------------------

        fits_large = drawing.fits(
            LARGE_USABLE_WIDTH_MM,
            LARGE_USABLE_HEIGHT_MM,
        )

        fits_small = drawing.fits(
            SMALL_USABLE_WIDTH_MM,
            SMALL_USABLE_HEIGHT_MM,
        )

        report.validation(
            drawing,
            rotated,
            min(normal_overflow, rotated_overflow),
            fits_large,
            fits_small,
        )

        dev_report.validation(
            drawing,
            rotated,
            min(normal_overflow, rotated_overflow),
            fits_large,
            fits_small,
        )

        if not fits_large:

            print(
                f"ABORT: {pdf.name} exceeds the maximum machine size."
            )

            message = (
                f"Drawing size : "
                f"{drawing.drawing_width:.2f} × "
                f"{drawing.drawing_height:.2f} mm\n"
                f"Maximum size : "
                f"{LARGE_USABLE_WIDTH_MM:.2f} × "
                f"{LARGE_USABLE_HEIGHT_MM:.2f} mm"
            )

            alerts.abort(
                project.name,
                pdf.name,
                message,
            )

            continue

        report.geometry(geometry)
        dev_report.geometry(geometry)
        report.colours(colors)
        dev_report.colours(colors)
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

        report.cleanup(
            removed_zero,
            removed_duplicates,
            normalization.corrected,
        )

        dev_report.cleanup(
            removed_zero,
            removed_duplicates,
            normalization.corrected,
        )

        stats = geometry_statistics(drawing)

        report.statistics(stats)
        dev_report.statistics(stats)

        chains = analyse_chains(drawing)

        report.chains(chains)
        dev_report.chains(chains)

        # ----------------------------------------------------
        # Drawing accepted
        # ----------------------------------------------------

        project.add(drawing)

    # ========================================================
    # Export SVG
    # ========================================================

    output_file = folder / f"{project.name}.svg"

    print("Writing SVG...")
    write_svg(project, output_file)
    diag.export_file(output_file)
    debug.save_svg(diag.debug_folder / output_file.name, "05_final.svg")

    reports_folder = folder / "reports"
    reports_folder.mkdir(exist_ok=True)

    report.save(
        reports_folder / f"{project.name}.base_report.txt",
        project.name,
    )

    dev_report.save(
        reports_folder / f"{project.name}.extensive_report.txt",
        project.name,
    )

    print("=" * 60)
    print("Finished")
    print("=" * 60)
    print(f"Output : {output_file}")
    print(f"Report : {folder / (project.name + '.report.txt')}")
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

        alerts = BatchAlerts()

        for i, folder in enumerate(projects, start=1):
            print("=" * 60)
            print(f"Project {i} / {len(projects)}")
            print(folder)
            print("=" * 60)
            process_project(
                folder,
                alerts,
            )

        alerts.save(root)
        return

    print("Invalid choice.")


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
























