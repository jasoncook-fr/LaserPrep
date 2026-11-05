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
from complexity import (
    analyse_complexity,
    analyse_pdf_complexity,
    analyse_pdf_content,
)
from geometry_chains import analyse as analyse_chains
from geometry_statistics import analyse as geometry_statistics
from topology import build_paths
from black_engraving import process_black_engraving
from pathlib import Path
from datetime import datetime, timedelta
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
    remove_near_duplicate_lines,
)
from config import (
    BATCH_ROOT,
    ADMIN_ROOT,
    REPORT_RETENTION_DAYS,
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
from nextcloud_lookup import get_student_emails
from notification_manager import NotificationManager
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


def load_processing_records(folder: Path) -> dict[str, dict]:
    """Load per-PDF hashes and cached report outcomes.

    Legacy state files (a simple filename-to-hash mapping) are accepted.
    They have no cached report outcomes, so those PDFs are reprocessed once
    to establish the richer state format.
    """
    state_file = processing_state_path(folder)

    if not state_file.exists():
        return {}

    try:
        with state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict) and isinstance(data.get("files"), dict):
        return {
            name: record
            for name, record in data["files"].items()
            if isinstance(record, dict) and isinstance(record.get("hash"), str)
        }

    # Backward compatibility: old format stored only successful PDF hashes.
    if isinstance(data, dict):
        return {
            name: {"hash": value, "status": None}
            for name, value in data.items()
            if isinstance(name, str) and isinstance(value, str)
        }

    return {}


def load_processing_state(folder: Path) -> dict[str, str]:
    """Return filename-to-hash state for the batch preview."""
    return {
        name: record["hash"]
        for name, record in load_processing_records(folder).items()
    }


def save_processing_state(folder: Path, records: dict[str, dict]) -> None:
    """Atomically save content hashes and per-PDF report outcomes."""
    state_file = processing_state_path(folder)
    tmp_path = state_file.with_suffix(state_file.suffix + ".tmp")

    payload = {"version": 2, "files": records}
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    tmp_path.replace(state_file)

def load_recent_rejections(retention_days: int) -> dict[str, set[str]]:
    """Return rejected PDFs processed within the rolling activity window.

    The admin activity log is the source of truth. Old rejection entries are
    ignored even if the student-facing base report still contains them.
    """
    activity_path = ADMIN_ROOT / "activity" / "BATCH_ACTIVITY.json"

    if not activity_path.is_file():
        return {}

    try:
        with activity_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    entries = data.get("entries", []) if isinstance(data, dict) else []
    if not isinstance(entries, list):
        return {}

    cutoff = datetime.now().astimezone() - timedelta(
        days=max(1, int(retention_days))
    )
    recent_rejections: dict[str, set[str]] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "REJECTED":
            continue

        project = entry.get("project")
        pdf = entry.get("pdf")
        processed_at = entry.get("processed_at")
        if not all(isinstance(value, str) and value for value in (project, pdf, processed_at)):
            continue

        try:
            timestamp = datetime.fromisoformat(processed_at)
        except ValueError:
            continue

        # Older activity-log entries should normally include a timezone.
        # Treat a legacy naive timestamp as local time rather than discarding it.
        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()

        if timestamp >= cutoff:
            recent_rejections.setdefault(project, set()).add(pdf)

    return recent_rejections


def scan_batch_changes(batch_root: Path) -> list[dict]:
    """Return projects containing new, changed, rejected, or removed PDFs."""
    changes = []

    if not batch_root.is_dir():
        return changes

    # Keep project discovery identical to process_batch(), including the
    # Student / Project display name used by BatchAlerts.
    projects = []
    for student_folder in sorted(batch_root.iterdir()):
        if not student_folder.is_dir():
            continue

        if any(student_folder.glob("*.pdf")):
            projects.append((student_folder, student_folder.name))

        for project_folder in sorted(student_folder.iterdir()):
            if project_folder.is_dir() and any(project_folder.glob("*.pdf")):
                projects.append(
                    (project_folder, f"{student_folder.name} / {project_folder.name}")
                )

    # Rejections are shown in Needs Attention only while they fall within
    # the same rolling window as the administrative activity report.
    recent_rejections = load_recent_rejections(REPORT_RETENTION_DAYS)

    for folder, batch_project_name in projects:
        pdf_files = sorted(folder.glob("*.pdf"))
        current_hashes = {pdf.name: pdf_hash(pdf) for pdf in pdf_files}
        previous_hashes = load_processing_state(folder)
        rejected_names = recent_rejections.get(batch_project_name, set())

        new_files = sorted(
            name for name in current_hashes
            if name not in previous_hashes
            and name not in rejected_names
        )
        # Keep unchanged rejections visible in Needs Attention, but don't
        # treat a rejected PDF whose contents changed as unchanged: it belongs
        # in New / Changed and will be retried.
        rejected_files = sorted(
            name for name in current_hashes
            if name in rejected_names
            and (
                name not in previous_hashes
                or current_hashes[name] == previous_hashes[name]
            )
        )
        changed_files = sorted(
            name
            for name in current_hashes
            if name in previous_hashes
            and current_hashes[name] != previous_hashes[name]
        )
        removed_files = sorted(
            name for name in previous_hashes
            if name not in current_hashes
        )

        if new_files or changed_files or removed_files:
            changes.append({
                "project": batch_project_name,
                "kind": (
                    "new"
                    if not previous_hashes
                    and new_files
                    and not rejected_files
                    and not changed_files
                    and not removed_files
                    else "updated"
                ),
                "new": new_files,
                "rejected": rejected_files,
                "changed": changed_files,
                "removed": removed_files,
            })
        elif rejected_files:
            changes.append({
                "project": batch_project_name,
                "kind": "updated",
                "new": [],
                "rejected": rejected_files,
                "changed": [],
                "removed": [],
            })

    return changes


def cleanup_warning_outputs(
    folder: Path,
    preserve_pdf_stems: set[str] | None = None,
) -> None:
    """Remove stale LaserPrep warning SVGs before processing a project.

    Geometry-overlap warnings and unsupported-colour previews are generated
    fresh for each processing run. Old copies must not remain and be mistaken
    for the current result.

    Bad-colour previews are kept in the project's reports/ folder.
    """
    preserve_pdf_stems = preserve_pdf_stems or set()
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

        if not path.is_file():
            continue

        # Cached PDFs were not reanalysed, so their existing warning previews
        # must remain available. Remove outputs only for PDFs that will be
        # processed again (or for removed/unrelated stale outputs).
        if path.name.endswith("_bad_colors.svg"):
            pdf_stem = path.name.removesuffix("_bad_colors.svg")
            if pdf_stem in preserve_pdf_stems:
                continue

        if path.name.startswith("Geometry_Overlap_Warning - "):
            pdf_stem = (
                path.name
                .removeprefix("Geometry_Overlap_Warning - ")
                .removesuffix(".svg")
            )
            if pdf_stem in preserve_pdf_stems:
                continue

        try:
            path.unlink()
            print_info(f"Removed old warning file: {path}")
        except OSError as exc:
            print_warning(f"Could not remove old warning file {path}: {exc}")


def process_project(
    folder: Path,
    alerts: BatchAlerts | None = None,
    use_state: bool = True,
    batch_project_name: str | None = None,
    progress_label: str | None = None,
) -> str:

    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print_warning(f"No PDF files found in {folder}")
        return "no_output"

    current_hashes = None
    preserve_cached_stems: set[str] = set()
    missing_cached_warning_stems: set[str] = set()
    reports_folder = folder / "reports"

    if use_state:
        current_hashes = {
            pdf.name: pdf_hash(pdf)
            for pdf in pdf_files
        }

        previous_records = load_processing_records(folder)
        previous_hashes = {
            name: record["hash"]
            for name, record in previous_records.items()
        }

        cached_records_complete = all(
            previous_records.get(pdf.name, {}).get("status") is not None
            and isinstance(previous_records.get(pdf.name, {}).get("entry"), dict)
            for pdf in pdf_files
        )

        # A valid processing-state cache is not enough on its own: earlier
        # versions could save the PDF outcomes while exiting before writing
        # the project SVG or student-facing reports. Verify those artifacts
        # before treating an unchanged project as fully processed.
        has_exportable_drawing = any(
            previous_records.get(pdf.name, {}).get("status") in {"PASS", "WARNING"}
            for pdf in pdf_files
        )

        cached_outputs_complete = (
            (reports_folder / f"{folder.name}.base_report.txt").is_file()
            and (reports_folder / f"{folder.name}.extensive_report.txt").is_file()
            and (
                not has_exportable_drawing
                or (folder / f"{folder.name}.svg").is_file()
            )
        )

        for pdf in pdf_files:
            entry = previous_records.get(pdf.name, {}).get("entry", {})
            messages = entry.get("warnings", []) + entry.get("alerts", [])
            has_overlap_warning = any(
                "geometry overlap" in str(message).lower()
                for message in messages
            )
            if not has_overlap_warning:
                continue

            warning_name = (
                "Geometry_Overlap_Warning.svg"
                if len(pdf_files) == 1
                else f"Geometry_Overlap_Warning - {pdf.stem}.svg"
            )
            if not (reports_folder / warning_name).is_file():
                missing_cached_warning_stems.add(pdf.stem)
                cached_outputs_complete = False

        if (
            current_hashes == previous_hashes
            and cached_records_complete
            and cached_outputs_complete
        ):
            return "skipped"

        # Keep cached results for PDFs whose contents have not changed.
        # New/changed PDFs will overwrite their previous records when processed.
        processing_records = {
            name: record
            for name, record in previous_records.items()
            if name in current_hashes
        }
        preserve_cached_stems = {
            Path(name).stem
            for name, record in previous_records.items()
            if name in current_hashes
            and record.get("hash") == current_hashes[name]
            and record.get("status") == "REJECTED"
            and isinstance(record.get("entry"), dict)
        }

    # Clear stale outputs only for files that will be reprocessed.
    cleanup_warning_outputs(folder, preserve_cached_stems)

    project = Project(folder.name)
    report = Report()
    processing_failed = False
    dev_report = DeveloperReport()
    collinear_warning_svgs = []
    current_dev_start = 0

    def record_batch_result() -> None:
        """Record the final result and cache it for unchanged future runs."""
        if report.current is None:
            return

        if alerts is not None:
            alerts.result(
                batch_project_name or project.name,
                pdf.name,
                report.current,
            )

        if use_state:
            processing_records[pdf.name] = {
                "hash": current_hashes[pdf.name],
                "status": report.current.get("status", "PASS"),
                "entry": report.current.copy(),
                "dev_lines": list(dev_report.lines[current_dev_start:]),
            }

    debug = DebugManager(
        DEBUG,
        folder / ".laserprep" / "debug",
    )

    debug.start_run(project.name)
    diag.begin(project, folder)

    if progress_label:
        print_info(f"{progress_label} — {project.name}")

    print_info("=" * 60)
    print_info(f"Project : {project.name}")
    print_info(f"PDFs    : {len(pdf_files)}")
    print_info("=" * 60)
    print()

    # ========================================================
    # Read every PDF
    # ========================================================

    for pdf in pdf_files:

        cached = previous_records.get(pdf.name) if use_state else None
        unchanged_cached = (
            use_state
            and cached is not None
            and cached.get("hash") == current_hashes[pdf.name]
            and cached.get("status") == "REJECTED"
            and isinstance(cached.get("entry"), dict)
            and pdf.stem not in missing_cached_warning_stems
        )

        if unchanged_cached:
            print_info(f"Skipping unchanged PDF: {pdf.name}")

            # Finalize any preceding reprocessed PDF before inserting this
            # cached result; Report.save() must not append it a second time.
            if report.current is not None:
                report.files.append(report.current)
                report.current = None

            report.files.append(cached["entry"].copy())
            dev_report.lines.extend(cached.get("dev_lines", []))

            if cached.get("status") == "REJECTED":
                processing_failed = True

            continue

        # Start exactly one report entry for this PDF.
        report.begin_file(pdf.name)
        current_dev_start = len(dev_report.lines)
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

        # ----------------------------------------------------
        # Preflight: source PDF complexity
        # ----------------------------------------------------

        print_info(f"Checking {pdf.name}...")

        try:
            with fitz.open(pdf) as doc:
                page = doc[0]
                pdf_complexity = analyse_pdf_complexity(page)
                pdf_content = analyse_pdf_content(page)

        except Exception as exc:
            processing_failed = True

            message = (
                "Could not analyse the PDF's vector complexity "
                "before processing."
            )

            print_error(
                f"ABORT: Could not analyse {pdf.name}: {exc}"
            )

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        if pdf_complexity.should_abort:

            processing_failed = True

            message = (
                "This PDF contains an excessive amount of vector "
                "geometry and is too complex for LaserPrep to process "
                "reliably. Please simplify the vector artwork before "
                "submitting it."
            )

            print_error(
                f"ABORT: {pdf.name} contains more than "
                f"{pdf_complexity.point_count:,} vector points."
            )

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        if pdf_content.is_non_vector:

            processing_failed = True

            message = (
                "This PDF contains no usable vector artwork. "
                "The submitted artwork appears to be raster/image-based. "
                "Please submit a vector PDF suitable for laser cutting."
            )

            print_error(
                f"REJECT: {pdf.name} contains no usable vector artwork."
            )

            report.current["status"] = "REJECTED"
            report.current["alerts"].append(message)

            record_batch_result()
            continue

        print_info(
            f"Vector complexity: {pdf_complexity.rating}"
        )

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

        warning_svg_name = (
            "Geometry_Overlap_Warning.svg"
            if len(pdf_files) == 1
            else f"Geometry_Overlap_Warning - {pdf.stem}.svg"
        )
        report.collinear_overlap(
            collinear_result,
            visualization_filename=warning_svg_name,
        )

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
        report.geometry(geometry)
        dev_report.geometry(geometry)

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
        removed_near_duplicates = remove_near_duplicate_lines(drawing)

        build_paths(drawing)

        process_black_engraving(drawing)

        report.cleanup(
            removed_zero,
            removed_duplicates,
            removed_near_duplicates,
            normalization.corrected,
        )

        dev_report.cleanup(
            removed_zero,
            removed_duplicates,
            removed_near_duplicates,
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

        # The result and its hash are cached by record_batch_result().
        project.add(drawing)

    # ========================================================
    # Preserve geometry warning visualizations
    # ========================================================

    # These diagnostics must be copied even when another PDF in the
    # project was rejected. A per-file rejection must not suppress
    # reports or SVG output for otherwise eligible drawings.
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

    # ========================================================
    # Export SVG
    # ========================================================

    output_file = folder / f"{project.name}.svg"

    # Do not create an empty SVG when no PDF produced usable geometry.
    # Reports and processing state are still saved for rejected projects.
    if not project.drawings:
        report.save(
            reports_folder / f"{project.name}.base_report.txt",
            project.name,
        )

        dev_report.save(
            reports_folder / f"{project.name}.extensive_report.txt",
            project.name,
        )

        if not processing_failed:
            print_error(
                "ABORT: No usable vector geometry was found in the project. "
                "No SVG was created."
            )

        if use_state:
            save_processing_state(folder, processing_records)

        debug.finish()
        diag.end()
        return "completed"

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
        save_processing_state(folder, processing_records)

    return "completed"

def process_batch(
    batch_root: Path,
    send_notifications: bool = True,
) -> None:
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
            projects.append((student_folder, student_folder.name))

        # Organized students:
        # Each immediate subfolder containing PDFs is a project.
        for p in sorted(student_folder.iterdir()):
            if p.is_dir() and any(p.glob("*.pdf")):
                projects.append((p, f"{student_folder.name} / {p.name}"))

    if not projects:
        print("No projects found.")
        return

    print_info(f"Found {len(projects)} projects.")

    # Retrieve the current student shares once per batch. If Nextcloud is
    # unavailable, processing continues and pending notifications can retry
    # during a later batch.
    notifications = None

    if send_notifications:
        # Retrieve student shares once per batch.
        try:
            student_emails = get_student_emails()
            print_info(
                f"Retrieved {len(student_emails)} student email mappings "
                "from Nextcloud."
            )
        except Exception as exc:
            student_emails = {}
            print_warning(
                f"Could not retrieve student shares from Nextcloud: {exc}. "
                "Email notifications will be deferred."
            )

        try:
            notifications = NotificationManager(
                ADMIN_ROOT,
                batch_root,
                student_emails,
            )
        except Exception as exc:
            print_warning(
                f"Could not initialize notification history: {exc}. "
                "Email notifications are disabled for this batch."
            )
    else:
        print_info("Email notifications are disabled for this batch.")

    alerts = BatchAlerts()
    skipped_projects = 0
    processed_projects = 0

    for i, (folder, batch_project_name) in enumerate(projects, start=1):
        result = process_project(
            folder,
            alerts,
            use_state=True,
            batch_project_name=batch_project_name,
            progress_label=f"Project {i} / {len(projects)}",
        )

        if result == "skipped":
            skipped_projects += 1
        else:
            processed_projects += 1

        # A project folder is either the student folder itself (PDFs directly
        # inside it) or one level below the student folder.
        student_folder_name = (
            folder.name if folder.parent == batch_root else folder.parent.name
        )

        if notifications is not None:
            try:
                if result == "completed":
                    notifications.queue(folder, batch_project_name)
                    notifications.attempt(folder, student_folder_name)
                elif result == "skipped":
                    # Retry a previously queued email if the project was
                    # previously completed, but email delivery/share lookup failed.
                    notifications.attempt(folder, student_folder_name)
                else:
                    # No PDF was available to process.
                    notifications.clear(folder)
            except Exception as exc:
                # Notification bookkeeping must never interrupt batch processing.
                print_warning(
                    f"Notification handling failed for {batch_project_name}: {exc}"
                )

    alerts.save(ADMIN_ROOT, retention_days=REPORT_RETENTION_DAYS)

    print_info("=" * 60)
    print_info("Batch summary")
    print_info("=" * 60)
    print_info(f"Projects found     : {len(projects)}")
    print_info(f"Projects processed : {processed_projects}")
    print_info(f"Projects skipped   : {skipped_projects}")
    print_info("=" * 60)


def main() -> None:
    # Import the GUI only when launching the application. The GUI receives
    # processing functions explicitly, so it does not import main.py.
    from gui import launch_gui

    launch_gui(
        process_project=process_project,
        process_batch=process_batch,
        scan_batch_changes=scan_batch_changes,
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
