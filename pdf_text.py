"""
pdf_text.py

Extract semantic text from a PDF using PyMuPDF.

This module is intentionally generic. It simply exposes every
text span present in the PDF.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


# ------------------------------------------------------------
# Data classes
# ------------------------------------------------------------

@dataclass(slots=True)
class TextSpan:
    text: str

    left: float
    top: float
    right: float
    bottom: float

    font: str
    size: float

    page: int


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def extract_pdf_text(pdf_file: str | Path) -> list[TextSpan]:
    """
    Extract every text span from a PDF.

    Returns
    -------
    list[TextSpan]
    """

    pdf_file = Path(pdf_file)

    document = fitz.open(pdf_file)

    spans: list[TextSpan] = []

    try:

        for page_number, page in enumerate(document):

            data = page.get_text("dict")

            for block in data["blocks"]:

                #
                # Ignore images, drawings, etc.
                #
                if block["type"] != 0:
                    continue

                for line in block["lines"]:

                    for span in line["spans"]:

                        x0, y0, x1, y1 = span["bbox"]

                        text = span["text"].strip()

                        if not text:
                            continue

                        spans.append(

                            TextSpan(
                                text=text,

                                left=x0,
                                top=y0,
                                right=x1,
                                bottom=y1,

                                font=span["font"],
                                size=span["size"],

                                page=page_number,
                            )

                        )

    finally:

        document.close()

    return spans


# ------------------------------------------------------------
# Convenience
# ------------------------------------------------------------

def find_text(
    pdf_file: str | Path,
    text: str,
) -> list[TextSpan]:
    """
    Return every occurrence of the requested text.
    """

    return [

        span

        for span in extract_pdf_text(pdf_file)

        if span.text == text

    ]
