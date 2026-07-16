"""
text_to_paths.py

LaserPrep

Converts PDF text into SVG paths using Poppler (pdftocairo).

This module does NOT parse the SVG.
It only creates it.

Version 0.1
"""

from pathlib import Path
import shutil
import subprocess


# ============================================================
# Exceptions
# ============================================================

class PopplerNotFoundError(RuntimeError):
    """Raised when pdftocairo cannot be found."""


class PopplerConversionError(RuntimeError):
    """Raised when pdftocairo fails."""


# ============================================================
# Conversion
# ============================================================

def text_to_paths(pdf_file: str | Path,
                  svg_file: str | Path) -> Path:
    """
    Convert a PDF into an SVG using Poppler.

    Parameters
    ----------
    pdf_file : Path
        Input PDF.

    svg_file : Path
        Output SVG.

    Returns
    -------
    Path
        Path to the generated SVG.
    """

    pdf_file = Path(pdf_file)
    svg_file = Path(svg_file)

    if not pdf_file.exists():
        raise FileNotFoundError(pdf_file)

    # --------------------------------------------------------
    # Locate Poppler
    # --------------------------------------------------------

    executable = shutil.which("pdftocairo")

    if executable is None:
        raise PopplerNotFoundError(
            "pdftocairo was not found.\n"
            "Install Poppler:\n"
            "sudo apt install poppler-utils"
        )

    # --------------------------------------------------------
    # Ensure output directory exists
    # --------------------------------------------------------

    svg_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Convert
    # --------------------------------------------------------

    command = [
        executable,
        "-svg",
        str(pdf_file),
        str(svg_file),
    ]
    '''
    print()
    print("=" * 60)
    print("Poppler")
    print("=" * 60)
    print(f"Input  : {pdf_file}")
    print(f"Output : {svg_file}")
    print()
    '''
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise PopplerConversionError(
            result.stderr.strip()
        )

    if not svg_file.exists():

        raise PopplerConversionError(
            "SVG file was not created."
        )

    print("✓ Conversion successful")
    print()

    return svg_file


# ============================================================
# Standalone test
# ============================================================

if __name__ == "__main__":

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    pdf = filedialog.askopenfilename(
        title="Select PDF",
        filetypes=[("PDF", "*.pdf")],
    )

    root.destroy()

    if pdf:

        pdf = Path(pdf)

        svg = pdf.with_suffix(".svg")

        text_to_paths(
            pdf,
            svg,
        )
