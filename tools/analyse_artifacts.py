#!/usr/bin/env python3

"""
analyse_artifacts.py

Diagnostic tool for LaserPrep.

Imports a PDF, analyses every VectorPath and prints a table of
geometric measurements.

Nothing is modified.
Nothing is filtered.

This tool exists to help develop future artifact detectors.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from poppler import text_to_paths
from svg_text_import import (
    import_svg_paths,
    get_svg_page_size,
)
from artifact_analysis import analyse_paths
from artifact_detector import (
    find_edge_objects,
    find_long_objects,
    find_sparse_objects,
)

PDF = (
    PROJECT_ROOT
    / "TEST_FILES"
    / "quarantine"
    / "cart_C"
    / "Cartouche_B.pdf"
)


def main():

    svg = PDF.with_suffix(".text.svg")

    print("=" * 80)
    print("PDF → SVG")
    print("=" * 80)

    text_to_paths(PDF, svg)

    print("=" * 80)
    print("SVG → VectorPaths")
    print("=" * 80)

    page_width, page_height = get_svg_page_size(svg)

    paths = import_svg_paths(svg)
    print(f"Page size : {page_width:.2f} × {page_height:.2f} mm")
    print(f"\nImported paths : {len(paths)}")

    metrics = analyse_paths(
        paths,
        page_width,
        page_height,
    )


    print()
    print("VERIFY METRICS")
    print("--------------")

    for i in (0, 1, 2, 100, 200, 306):

        p = paths[i]
        m = metrics[i]

        print(
            f"{i:3d}  "
            f"path={p.width:.3f} x {p.height:.3f}   "
            f"metric={m.width:.3f} x {m.height:.3f}"
        )

    largest = max(metrics, key=lambda m: m.area)

    print()
    print("Largest object")
    print("----------------")
    print(f"Left   : {largest.left:.2f}")
    print(f"Right  : {largest.right:.2f}")
    print(f"Top    : {largest.top:.2f}")
    print(f"Bottom : {largest.bottom:.2f}")
    print()

    print(f"Page width  : {page_width:.2f}")
    print(f"Page height : {page_height:.2f}")
    print()

    print(f"Left distance   : {largest.distance_left:.2f}")
    print(f"Right distance  : {largest.distance_right:.2f}")
    print(f"Top distance    : {largest.distance_top:.2f}")
    print(f"Bottom distance : {largest.distance_bottom:.2f}")
    print(f"Nearest edge    : {largest.distance_to_edge:.2f}")

    edge = find_edge_objects(metrics)
    long = find_long_objects(metrics)
    sparse = find_sparse_objects(metrics)

    def show(title, candidates):
        print()
        print(title)
        print("-" * len(title))

        for c in candidates:
            m = c.metrics

            print(
                f"{c.index:3d}  "
                f"Area={m.area:8.2f}  "
                f"Aspect={m.aspect_ratio:6.2f}  "
                f"Density={m.density:6.2f}  "
                f"Bounds=({m.left:.2f}, {m.top:.2f}) "
                f"({m.right:.2f}, {m.bottom:.2f})"
            )

    show("Near page edge", edge)
    show("Long objects", long)
    show("Sparse objects", sparse)

    print()
    print("=" * 80)
    print("Detector summary")
    print("=" * 80)

    print(f"Near page edge : {len(edge)}")
    print(f"Long objects   : {len(long)}")
    print(f"Sparse objects : {len(sparse)}")

    #
    # Pair paths with their metrics.
    #
    rows = list(zip(paths, metrics))

    #
    # Smallest objects first.
    #
    rows.sort(key=lambda item: item[1].area)

    print()
    print("=" * 110)
    print(
        f"{'ID':>4} "
        f"{'Area':>10} "
        f"{'Aspect':>8} "
        f"{'Density':>9} "
        f"{'Objects':>8} "
        f"{'Centre X':>10} "
        f"{'Centre Y':>10}"
    )

    print("=" * 110)

    for i, (_, m) in enumerate(rows):

        print(
            f"{i:4d} "
            f"{m.area:10.2f} "
            f"{m.aspect_ratio:8.2f} "
            f"{m.density:9.2f} "
            f"{m.object_count:8d} "
            f"{m.centre.x:10.2f} "
            f"{m.centre.y:10.2f}"
        )

    print()
    print("Analysis complete.")


if __name__ == "__main__":
    main()


