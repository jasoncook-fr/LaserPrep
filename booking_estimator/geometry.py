"""Geometry primitives and affine transforms for the booking estimator."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in normalized millimetre coordinates."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self):
        if self.max_x < self.min_x or self.max_y < self.min_y:
            raise ValueError("BoundingBox maximum bounds must not be below minimum bounds")

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def area(self) -> float:
        return self.width * self.height

    def union(self, other: "BoundingBox") -> "BoundingBox":
        return BoundingBox(min(self.min_x, other.min_x), min(self.min_y, other.min_y),
                          max(self.max_x, other.max_x), max(self.max_y, other.max_y))


@dataclass(frozen=True)
class Matrix:
    """SVG affine matrix: x'=a*x+c*y+e, y'=b*x+d*y+f."""
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def apply(self, point: Point) -> Point:
        return Point(self.a*point.x + self.c*point.y + self.e,
                     self.b*point.x + self.d*point.y + self.f)

    def compose(self, other: "Matrix") -> "Matrix":
        """Return self composed with other: other is applied, then self."""
        return Matrix(self.a*other.a + self.c*other.b,
                      self.b*other.a + self.d*other.b,
                      self.a*other.c + self.c*other.d,
                      self.b*other.c + self.d*other.d,
                      self.a*other.e + self.c*other.f + self.e,
                      self.b*other.e + self.d*other.f + self.f)


@dataclass(frozen=True)
class GeometryRecord:
    """Source element geometry; measurement and classification are separate."""
    element_type: str
    payload: dict[str, object]
    source_id: Optional[str] = None
    source_element: Optional[str] = None
    transform: Matrix = Matrix()
    style: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
