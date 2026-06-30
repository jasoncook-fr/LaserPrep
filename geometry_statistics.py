"""
geometry_statistics.py

Statistics about imported geometry.

Version 0.8
"""

from drawing import Drawing, Line
import math


class GeometryStatistics:

    def __init__(self):

        self.total_lines = 0

        self.lt_001 = 0      # < 0.01 mm
        self.lt_005 = 0      # 0.01 - 0.05
        self.lt_010 = 0      # 0.05 - 0.10
        self.lt_050 = 0      # 0.10 - 0.50
        self.lt_100 = 0      # 0.50 - 1.00
        self.gt_100 = 0      # > 1.00 mm


def analyse(drawing: Drawing):

    stats = GeometryStatistics()

    for obj in drawing.objects:

        if not isinstance(obj, Line):
            continue

        stats.total_lines += 1

        dx = obj.end.x - obj.start.x
        dy = obj.end.y - obj.start.y

        length = math.hypot(dx, dy)

        if length < 0.01:
            stats.lt_001 += 1

        elif length < 0.05:
            stats.lt_005 += 1

        elif length < 0.10:
            stats.lt_010 += 1

        elif length < 0.50:
            stats.lt_050 += 1

        elif length < 1.00:
            stats.lt_100 += 1

        else:
            stats.gt_100 += 1

    return stats
