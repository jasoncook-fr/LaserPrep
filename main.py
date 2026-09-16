"""
main.py

LaserPrep application entry point.

Version 0.5
"""
import hashlib
import json
import shutil
import fitz
from batch_alerts import BatchAlerts
from complexity import analyse_complexity
from geometry_chains import analyse as analyse_chains
from geometry_statistics import analyse as geometry_statistics
from topology import build_paths
from black_engraving import process_black_engraving
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from text_import import import_text
from pdf_reader import read_pdf
from project import Project
from svg_writer import write_svg, write_bad_colors_svg
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
    ADMIN_ROOT,
    DISPLAY_OFFSET_X_MM,
    DISPLAY_OFFSET_Y_MM,
    LARGE_USABLE_WIDTH_MM,
    LARGE_USABLE_HEIGHT_MM,
    SMALL_USABLE_WIDTH_MM,
    SMALL_USABLE_HEIGHT_MM,
    SUSPECT_SCALE_MAX_MM,
    SUSPECT_SCALE_MIN_OBJECTS,
)
from debug_manager import DebugManager
from config import DEBUG
from report import Report
from report_dev import DeveloperReport
from collinear_overlap_diagnostic import (
    analyse_collinear_overlap,
    format_report as format_collinear_overlap_report,
    export_debug_svg as export_collinear_overlap_debug_svg,
)

# ============================================================
# Terminal Output Colors
# ============================================================

class TerminalColors:
    """ANSI colors used for readable terminal output."""

    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(f"{TerminalColors.RED}{message}{TerminalColors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(f"{TerminalColors.YELLOW}{message}{TerminalColors.RESET}")


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(f"{TerminalColors.GREEN}{message}{TerminalColors.RESET}")


def print_info(message: str) -> None:
    """Print an informational message in cyan."""
    print(f"{TerminalColors.CYAN}{message}{TerminalColors.RESET}")


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
# GUI Preferences
# ============================================================

UI_STATE_FILE = Path.home() / ".laserprep_ui.json"


def load_last_single_project_directory() -> Path | None:
    """Load the last directory used for Single Project selection."""

    if not UI_STATE_FILE.exists():
        return None

    try:
        with UI_STATE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        directory = data.get("last_single_project_directory")

        if directory:
            path = Path(directory)
            if path.is_dir():
                return path

    except (OSError, json.JSONDecodeError):
        pass

    return None


def save_last_single_project_directory(directory: Path) -> None:
    """Remember the directory containing the last selected project."""

    try:
        with UI_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "last_single_project_directory": str(directory),
                },
                f,
                indent=2,
            )
    except OSError:
        # Failure to save a UI preference should never stop LaserPrep.
        pass


# ============================================================
# Main
# ============================================================
def pdf_hash(path: Path) -> str:
    """Return a SHA-256 hash of a PDF's contents."""

    sha256 = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

def processing_state_path(folder: Path) -> Path:
    """Return the administrator-only state file for a project."""

    state_dir = ADMIN_ROOT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    if folder.parent == BATCH_ROOT:
        filename = f"{folder.name}.json"
    else:
        filename = f"{folder.parent.name}__{folder.name}.json"

    return state_dir / filename


def load_processing_state(folder: Path) -> dict:
    """Load the record of the last successful processing run."""

    state_file = processing_state_path(folder)

    if not state_file.exists():
        return {}

    try:
        with state_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_processing_state(folder: Path, pdf_hashes: dict[str, str]) -> None:
    """Save the hashes of PDFs successfully processed."""

    state_file = processing_state_path(folder)

    with state_file.open("w", encoding="utf-8") as f:
        json.dump(
            pdf_hashes,
            f,
            indent=2,
            sort_keys=True,
        )

def cleanup_warning_outputs(folder: Path) -> None:
    """Remove stale LaserPrep warning SVGs before processing a project.

    Geometry-overlap warnings and unsupported-colour previews are generated
    fresh for each processing run. Old copies must not remain and be mistaken
    for the current result.

    Bad-colour previews are kept in the project's reports/ folder.
    """
    reports_folder = folder / "reports"
    reports_folder.mkdir(parents=True, exist_ok=True)

    files_to_remove = []

    # Old bad-colour previews may have been written in the project root by
    # earlier versions of LaserPrep. Remove them from there.
    files_to_remove.extend(folder.glob("*_bad_colors.svg"))

    # Current/future bad-colour previews belong in the report dossier.
    files_to_remove.extend(reports_folder.glob("*_bad_colors.svg"))

    # Remove all previous geometry-overlap warning visualizations from the
    # report dossier. Also clean the project root in case an older version
    # placed them there.
    files_to_remove.extend(reports_folder.glob("Geometry_Overlap_Warning*.svg"))
    files_to_remove.extend(folder.glob("Geometry_Overlap_Warning*.svg"))

    seen = set()

    for path in files_to_remove:
        if path in seen:
            continue
        seen.add(path)

        if path.is_file():
            try:
                path.unlink()
                print_info(f"Removed old warning file: {path}")
            except OSError as exc:
                print_warning(f"Could not remove old warning file {path}: {exc}")


def process_project(
    folder: Path,
    alerts: BatchAlerts | None = None,
    use_state: bool = True,
) -> None:
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print_warning(f"No PDF files found in {folder}")
        return

    current_hashes = None

    if use_state:
        current_hashes = {
            pdf.name: pdf_hash(pdf)
            for pdf in pdf_files
        }

        previous_hashes = load_processing_state(folder)

        if current_hashes == previous_hashes:
            print_info(f"Skipping unchanged project: {folder}")
            return

        # State is tracked per PDF. A successful PDF (including WARNING)
        # keeps its hash; a rejected PDF is deliberately left out so it will
        # be retried on the next batch run.
        successful_hashes = {
            pdf_name: pdf_hash
            for pdf_name, pdf_hash in previous_hashes.items()
            if pdf_name in current_hashes
        }

    # Remove stale student-facing warning previews before generating this run.
    cleanup_warning_outputs(folder)

    reports_folder = folder / "reports"

    project = Project(folder.name)
    report = Report()
    processing_failed = False
    dev_report = DeveloperReport()
    collinear_warning_svgs = []

    def record_batch_result() -> None:
        """Record the final student-facing result for the current PDF."""
        if alerts is not None and report.current is not None:
            alerts.result(
                project.name,
                pdf.name,
                report.current,
            )

    debug = DebugManager(
        DEBUG,
        folder / ".laserprep" / "debug",
    )

    debug.start_run(project.name)
    diag.begin(project, folder)

    print_info("=" * 60)
    print_info(f"Project : {project.name}")
    print_info(f"PDFs    : {len(pdf_files)}")
    print_info("=" * 60)
    print()

    # ========================================================
    # Read every PDF
    # ========================================================

    for pdf in pdf_files:

        if use_state:
            successful_hashes.pop(pdf.name, None)

        # Start exactly one report entry for this PDF.
        report.begin_file(pdf.name)
        dev_report.begin_file(pdf.name)

        # ----------------------------------------------------
        # Validate PDF page count
        # ----------------------------------------------------

        try:
            with fitz.open(pdf) as doc:
                page_count = len(doc)
        except Exception as exc:
            processing_failed = True

            message = (
                "Could not read the PDF to determine its page count."
            )

            print_error(f"ABORT: Could not read {pdf.name}: {exc}")

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        if page_count > 1:
            processing_failed = True

            message = (
                f"PDF contains {page_count} pages. "
                "LaserPrep only accepts single-page PDFs."
            )

            print_error(
                f"ABORT: {pdf.name} contains multiple pages ({page_count})."
            )

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        print_info(f"Reading {pdf.name}...")

        drawing = read_pdf(pdf)

        complexity = analyse_complexity(drawing)

        report.complexity(complexity)
        dev_report.complexity(complexity)

        if complexity.should_abort:

            processing_failed = True

            message = "Drawing complexity exceeds the allowed limit."
            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
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

        # ----------------------------------------------------
        # Diagnostic: collinear redundant geometry
        # ----------------------------------------------------
        #
        # Run immediately after PDF geometry import/path construction.
        # This is diagnostic-only: it never modifies the drawing.
        #
        # This replaces the old O(n²) near-parallel scan as our first
        # production-safe investigation of the Zambala-type problem.
        collinear_result = analyse_collinear_overlap(drawing)
        report.collinear_overlap(collinear_result)

        overlap_debug_svg = (
            folder / ".laserprep" / "debug" /
            f"{pdf.stem}_03_collinear_overlap.svg"
        )
        export_collinear_overlap_debug_svg(
            collinear_result,
            overlap_debug_svg,
        )
        debug.save_text(
            f"{pdf.stem}_03_collinear_overlap.txt",
            format_collinear_overlap_report(collinear_result),
        )

        overlap_groups = collinear_result["non_exact_groups"]

        if overlap_groups:
            collinear_warning_svgs.append(overlap_debug_svg)

        # report.py owns the overlap policy. BatchAlerts records the same
        # final Report result, so the two reports cannot disagree.
        if report.current["status"] == "REJECTED":
            processing_failed = True

            print_error(
                f"ABORT: {pdf.name} exceeds the geometry-overlap rejection threshold."
            )

            record_batch_result()
            continue

        # ----------------------------------------------------
        # Reject PDFs that produced no usable vector geometry
        # ----------------------------------------------------

        if len(drawing.paths) == 0:
            processing_failed = True

            message = (
                "No usable vector geometry was found in this PDF. "
                "LaserPrep could not produce any geometry to process."
            )

            print_error(
                f"ABORT: {pdf.name} contains no usable vector geometry."
            )

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        diag.export_svg(
            drawing,
            f"{pdf.stem}.merged_before_move.svg",
        )

        #drawing.geometry_report = geometry
        geometry = analyse(drawing)

        colors = analyse_colors(drawing)

        if colors.unsupported:
            bad_colors_file = reports_folder / f"{pdf.stem}_bad_colors.svg"

            write_bad_colors_svg(
                drawing,
                bad_colors_file,
                set(colors.unsupported.keys()),
            )

            # Remove unsupported-colour geometry from the official drawing.
            unsupported = set(colors.unsupported.keys())

            drawing.objects = [
                obj
                for obj in drawing.objects
                if obj.stroke_color not in unsupported
            ]

        # ----------------------------------------------------
        # Check for suspiciously small, highly detailed drawings
        # ----------------------------------------------------

        longest_dimension = max(
            drawing.drawing_width,
            drawing.drawing_height,
        )

        suspicious_scale = (
            longest_dimension < SUSPECT_SCALE_MAX_MM
            and complexity.object_count > SUSPECT_SCALE_MIN_OBJECTS
        )

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

            processing_failed = True

            print_error(
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

            record_batch_result()
            continue

        report.geometry(geometry)
        dev_report.geometry(geometry)

        if suspicious_scale:
            report.suspicious_scale(
                drawing,
                complexity.object_count,
            )

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

        process_black_engraving(drawing)

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

        # Record the complete final Report result for the Admin report.
        record_batch_result()

        # PASS and WARNING files are successfully processed and can therefore
        # be skipped on the next run if their PDF hash is unchanged.
        if use_state:
            successful_hashes[pdf.name] = current_hashes[pdf.name]

        project.add(drawing)

    # ========================================================
    # Export SVG
    # ========================================================

    output_file = folder / f"{project.name}.svg"

    # Preserve the student-facing geometry warning visualization in the
    # permanent project reports folder. One file per source PDF avoids
    # collisions in multi-PDF projects.
    for overlap_debug_svg in collinear_warning_svgs:
        pdf_stem = overlap_debug_svg.name.removesuffix("_03_collinear_overlap.svg")
        target_name = (
            "Geometry_Overlap_Warning.svg"
            if len(pdf_files) == 1
            else f"Geometry_Overlap_Warning - {pdf_stem}.svg"
        )
        shutil.copy2(
            overlap_debug_svg,
            reports_folder / target_name,
        )

    # Do not create an empty SVG when no PDF produced usable geometry.
    if not project.drawings:
        report.save(
            reports_folder / f"{project.name}.base_report.txt",
            project.name,
        )

        dev_report.save(
            reports_folder / f"{project.name}.extensive_report.txt",
            project.name,
        )

        print_error(
            "ABORT: No usable vector geometry was found in the project. "
            "No SVG was created."
        )

        debug.finish()
        diag.end()
        return

    print_info("Writing SVG...")

    write_svg(project, output_file)
    diag.export_file(output_file)
    debug.save_svg(diag.debug_folder / output_file.name, "05_final.svg")

    report.save(
        reports_folder / f"{project.name}.base_report.txt",
        project.name,
    )

    dev_report.save(
        reports_folder / f"{project.name}.extensive_report.txt",
        project.name,
    )

    print_success("=" * 60)
    print_success("Finished")
    print_success("=" * 60)
    print_info(f"Output : {output_file}")
    print_info(f"Report : {folder / (project.name + '.report.txt')}")
    print()

    debug.finish()
    diag.end()
    project.summary()

    if use_state:
        if successful_hashes:
            save_processing_state(folder, successful_hashes)
        else:
            state_file = processing_state_path(folder)
            if state_file.exists():
                state_file.unlink()

def process_batch(batch_root: Path) -> None:
    """Process every project found under the selected batch root."""

    if not batch_root.exists():
        print_error(f"Batch root does not exist: {batch_root}")
        return

    projects = []

    # Each student folder is the first level below the batch root.
    for student_folder in sorted(batch_root.iterdir()):

        if not student_folder.is_dir():
            continue

        # Lazy organization:
        # PDFs directly in the student's folder form one project.
        if any(student_folder.glob("*.pdf")):
            projects.append(student_folder)

        # Organized students:
        # Each immediate subfolder containing PDFs is a project.
        projects.extend(
            p
            for p in sorted(student_folder.iterdir())
            if p.is_dir() and any(p.glob("*.pdf"))
        )

    if not projects:
        print("No projects found.")
        return

    print_info(f"Found {len(projects)} projects.")

    alerts = BatchAlerts()

    for i, folder in enumerate(projects, start=1):
        print_info("=" * 60)
        print_info(f"Project {i} / {len(projects)}")
        print_info(str(folder))
        print_info("=" * 60)
        process_project(
            folder,
            alerts,
            use_state=True,
        )

    alerts.save(ADMIN_ROOT)


def launch_gui() -> None:
    """Launch the LaserPrep graphical launcher."""

    # Restrained colors give the two processing modes a clear visual identity.
    WINDOW_BG = "#F4F5F7"
    SINGLE_BG = "#EAF2FF"
    SINGLE_BUTTON = "#3B73C5"
    BATCH_BG = "#EAF7EF"
    BATCH_BUTTON = "#3F8F5B"
    BUTTON_TEXT = "#FFFFFF"
    TEXT = "#252525"
    SECONDARY_TEXT = "#666666"
    NEUTRAL_BUTTON = "#E2E4E7"

    root = tk.Tk()
    root.title("LaserPrep")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # --------------------------------------------------------
    # Appearance
    # --------------------------------------------------------

    root.configure(bg=WINDOW_BG)

    title_font = ("TkDefaultFont", 18, "bold")
    heading_font = ("TkDefaultFont", 11, "bold")
    body_font = ("TkDefaultFont", 9)

    # --------------------------------------------------------
    # Variables
    # --------------------------------------------------------

    batch_root_var = tk.StringVar(value=str(BATCH_ROOT))
    status_var = tk.StringVar(value="Ready")

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------

    def select_single_project() -> None:
        last_directory = load_last_single_project_directory()

        kwargs = {
            "parent": root,
            "title": "Select the folder containing the PDF files",
        }

        if last_directory is not None:
            kwargs["initialdir"] = str(last_directory)

        folder = filedialog.askdirectory(**kwargs)

        if not folder:
            return

        selected_folder = Path(folder)

        # Remember the parent directory so the next dialog opens
        # alongside the other projects.
        save_last_single_project_directory(selected_folder.parent)

        root.destroy()
        process_project(selected_folder, use_state=False)

    def browse_batch_root() -> None:
        folder = filedialog.askdirectory(
            parent=root,
            title="Select the Batch Root folder",
            initialdir=batch_root_var.get(),
        )

        if folder:
            batch_root_var.set(folder)
            status_var.set("Batch root changed for this session.")

    def run_batch() -> None:
        batch_root = Path(batch_root_var.get()).expanduser()

        if not batch_root.is_dir():
            status_var.set("The selected Batch Root does not exist.")
            return

        root.destroy()
        process_batch(batch_root)

    # --------------------------------------------------------
    # Main container
    # --------------------------------------------------------

    outer = tk.Frame(
        root,
        bg=WINDOW_BG,
        padx=28,
        pady=24,
    )
    outer.pack()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    tk.Label(
        outer,
        text="LaserPrep",
        font=title_font,
        bg=WINDOW_BG,
    ).pack()

    tk.Label(
        outer,
        text="PDF → laser preparation",
        font=body_font,
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
    ).pack(pady=(2, 22))

    # --------------------------------------------------------
    # Single Project section
    # --------------------------------------------------------

    single_frame = tk.LabelFrame(
        outer,
        text="  TEST SINGLE PROJECT  ",
        font=heading_font,
        bg=SINGLE_BG,
        padx=18,
        pady=14,
    )
    single_frame.pack(fill="x", pady=(0, 14))

    tk.Label(
        single_frame,
        text="Process one project without state tracking.",
        font=body_font,
        bg=SINGLE_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x")

    tk.Button(
        single_frame,
        text="Select Project",
        width=20,
        height=2,
        command=select_single_project,
        bg=SINGLE_BUTTON,
        fg=BUTTON_TEXT,
        activebackground=SINGLE_BUTTON,
        activeforeground=BUTTON_TEXT,
        relief="flat",
        bd=0,
    ).pack(pady=(12, 0))

    # --------------------------------------------------------
    # Batch section
    # --------------------------------------------------------

    batch_frame = tk.LabelFrame(
        outer,
        text="  BATCH PROCESSING  ",
        font=heading_font,
        bg=BATCH_BG,
        padx=18,
        pady=14,
    )
    batch_frame.pack(fill="x")

    tk.Label(
        batch_frame,
        text="Process all projects found under the Batch Root.",
        font=body_font,
        bg=BATCH_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x")

    tk.Label(
        batch_frame,
        text="Batch Root",
        font=heading_font,
        bg=BATCH_BG,
        fg=TEXT,
        anchor="w",
    ).pack(fill="x", pady=(14, 4))

    root_row = tk.Frame(batch_frame, bg=BATCH_BG)
    root_row.pack(fill="x")

    tk.Entry(
        root_row,
        textvariable=batch_root_var,
        width=43,
        relief="solid",
        bd=1,
    ).pack(side="left", fill="x", expand=True)

    tk.Button(
        root_row,
        text="Browse…",
        command=browse_batch_root,
        bg=NEUTRAL_BUTTON,
        fg=TEXT,
        activebackground=NEUTRAL_BUTTON,
        relief="flat",
        bd=0,
    ).pack(side="left", padx=(8, 0))

    tk.Button(
        batch_frame,
        text="Run Batch",
        width=20,
        height=2,
        command=run_batch,
        bg=BATCH_BUTTON,
        fg=BUTTON_TEXT,
        activebackground=BATCH_BUTTON,
        activeforeground=BUTTON_TEXT,
        relief="flat",
        bd=0,
    ).pack(pady=(14, 0))

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer = tk.Frame(outer, bg=WINDOW_BG)
    footer.pack(fill="x", pady=(16, 0))

    tk.Label(
        footer,
        textvariable=status_var,
        font=body_font,
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
        anchor="w",
    ).pack(side="left")

    # Quietly display the administrator folder location for reference.
    tk.Label(
        outer,
        text=f"Admin folder: {ADMIN_ROOT}",
        font=("TkDefaultFont", 8),
        bg=WINDOW_BG,
        fg=SECONDARY_TEXT,
        anchor="w",
    ).pack(fill="x", pady=(8, 0))

    tk.Button(
        footer,
        text="Quit",
        width=10,
        command=root.destroy,
        bg=NEUTRAL_BUTTON,
        fg=TEXT,
        activebackground=NEUTRAL_BUTTON,
        relief="flat",
        bd=0,
    ).pack(side="right")

    # --------------------------------------------------------
    # Center the launcher on screen
    # --------------------------------------------------------

    root.update_idletasks()

    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2

    root.geometry(f"+{x}+{y}")
    root.mainloop()


def main() -> None:
    launch_gui()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
