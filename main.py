"""
main.py

LaserPrep application entry point.

Version 0.5
"""
from pathlib import Path
from batch_alerts import BatchAlerts
from batch_processing import scan_batch_changes, process_batch as _process_batch
from project_processing import process_project as _process_project

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





def process_project(
    folder: Path,
    alerts: BatchAlerts | None = None,
    use_state: bool = True,
    batch_project_name: str | None = None,
    progress_label: str | None = None,
) -> str:
    """Preserve the public processing API while injecting terminal output."""
    return _process_project(
        folder,
        alerts=alerts,
        use_state=use_state,
        batch_project_name=batch_project_name,
        progress_label=progress_label,
        print_error=print_error,
        print_warning=print_warning,
        print_success=print_success,
        print_info=print_info,
    )


def process_batch(
    batch_root: Path,
    send_notifications: bool = True,
) -> None:
    _process_batch(
        batch_root,
        process_project=process_project,
        print_error=print_error,
        print_info=print_info,
        print_warning=print_warning,
        send_notifications=send_notifications,
    )


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
