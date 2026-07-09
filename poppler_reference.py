"""
poppler_reference.py

Generate a reference SVG using Poppler (pdftocairo).

This is used only for diagnostics.
"""

from pathlib import Path
import subprocess


def export_reference_svg(pdf_file: Path, output_svg: Path):

    command = [
        "/usr/bin/pdftocairo",
        "-svg",
        str(pdf_file),
        str(output_svg),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            "Poppler failed:\n\n"
            + result.stderr
        )
