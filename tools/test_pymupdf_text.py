#!/usr/bin/env python3

"""
test_pymupdf_text.py

Inspect all text contained in a PDF using PyMuPDF.

The purpose is to determine whether software-generated
stamps (e.g. ARCHICAD VERSION EDUCATION) still exist as
real text in the PDF.
"""

from pathlib import Path
import fitz  # PyMuPDF


PDF = Path(
    "TEST_FILES/quarantine/cart_C/BAMBU.pdf"
)


def main():

    print("=" * 80)
    print("PYMUPDF TEXT ANALYSIS")
    print("=" * 80)

    doc = fitz.open(PDF)

    total_spans = 0

    for page_number, page in enumerate(doc):

        print()
        print("=" * 80)
        print(f"PAGE {page_number + 1}")
        print("=" * 80)

        text = page.get_text("dict")

        for block in text["blocks"]:

            if block["type"] != 0:
                continue

            for line in block["lines"]:

                for span in line["spans"]:

                    total_spans += 1

                    x0, y0, x1, y1 = span["bbox"]

                    print()
                    print("-" * 60)
                    print(f"Text : {repr(span['text'])}")
                    print(f"Font : {span['font']}")
                    print(f"Size : {span['size']:.2f}")
                    print(f"BBox : ({x0:.2f}, {y0:.2f}) "
                          f"({x1:.2f}, {y1:.2f})")

                    # Dump every available field once.
                    print("Attributes:")

                    for key in sorted(span.keys()):

                        if key in (
                            "text",
                            "font",
                            "size",
                            "bbox",
                        ):
                            continue

                        print(f"    {key} = {span[key]}")

    print()
    print("=" * 80)
    print(f"Total text spans : {total_spans}")
    print("=" * 80)


if __name__ == "__main__":
    main()
