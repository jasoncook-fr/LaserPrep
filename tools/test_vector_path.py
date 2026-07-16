#!/usr/bin/env python3

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from drawing import Point, Line
from vector_path import VectorPath

vp = VectorPath()

vp.add(
    Line(
        Point(10, 20),
        Point(30, 40),
        (0, 0, 0),
        0.01,
    )
)

print("Bounds :", vp.bounds)
print("Width  :", vp.width)
print("Height :", vp.height)
print("Center :", vp.center)
