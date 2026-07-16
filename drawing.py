from dataclasses import dataclass, field
from typing import List, Tuple, Union

DEBUG = False

@dataclass
class Point:
    x: float
    y: float

Color = Tuple[int, int, int]

@dataclass
class Line:
    start: Point
    end: Point
    stroke_color: Color
    stroke_width: float
    import_order: int = 0

@dataclass
class Bezier:
    start: Point
    control1: Point
    control2: Point
    end: Point
    stroke_color: Color
    stroke_width: float
    import_order: int = 0

PathSegment = Union[Line, Bezier]

@dataclass
class Path:

    segments: List[PathSegment] = field(default_factory=list)
    closed: bool = False

    stroke_color: Color | None = None
    fill_color: Color | None = None

    stroke_width: float = 0.01

    stroke_enabled: bool = True
    fill_enabled: bool = False

    # True when this path originates from imported text.
    is_text: bool = False

    import_order: int = 0

    def add(self, segment: PathSegment) -> None:
        self.segments.append(segment)

@dataclass
class Polyline:

    points: list[Point] = field(default_factory=list)

    stroke_color: tuple[int, int, int] = (0, 0, 0)

    stroke_width: float = 0.01

    import_order: int = 0

@dataclass
class Drawing:
    name: str
    width: float
    height: float
    objects: List[PathSegment] = field(default_factory=list)
    paths: List[Path] = field(default_factory=list)

    def add(self, obj: PathSegment) -> None:
        self.objects.append(obj)

    @property
    def line_count(self) -> int:
        return sum(isinstance(o, Line) for o in self.objects)

    @property
    def bezier_count(self) -> int:
        return sum(isinstance(o, Bezier) for o in self.objects)

    @property
    def bounds(self):
        if not self.objects:
            return (0.0, 0.0, 0.0, 0.0)
        xs, ys = [], []
        for obj in self.objects:
            if isinstance(obj, Line):
                xs.extend((obj.start.x, obj.end.x))
                ys.extend((obj.start.y, obj.end.y))
            elif isinstance(obj, Bezier):
                xs.extend((obj.start.x, obj.control1.x, obj.control2.x, obj.end.x))
                ys.extend((obj.start.y, obj.control1.y, obj.control2.y, obj.end.y))
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def center(self) -> Point:
        """
        Returns the geometric centre of the drawing.
        """

        left, top, right, bottom = self.bounds

        return Point(
            (left + right) / 2,
            (top + bottom) / 2,
        )

    @property
    def drawing_width(self) -> float:
        l, t, r, b = self.bounds
        return r - l

    @property
    def drawing_height(self) -> float:
        l, t, r, b = self.bounds
        return b - t

    def translate(self, dx: float, dy: float) -> None:
        def move(p: Point):
            p.x += dx
            p.y += dy
        for obj in self.objects:
            if isinstance(obj, Line):
                move(obj.start); move(obj.end)
            elif isinstance(obj, Bezier):
                move(obj.start); move(obj.control1); move(obj.control2); move(obj.end)


    def move_to(self, x: float, y: float) -> None:
        left, top, _, _ = self.bounds
        self.translate(x - left, y - top)

    def fits(self, usable_width: float, usable_height: float) -> bool:
        """
        Returns True if the drawing geometry fits
        inside the specified usable area.
        """

        return (
            self.drawing_width <= usable_width
            and
            self.drawing_height <= usable_height
        )

    def fits_after_rotation(
        self,
        usable_width: float,
        usable_height: float,
    ) -> bool:
        """
        Returns True if the drawing would fit after
        a 90° rotation.
        """

        return (
            self.drawing_height <= usable_width
            and
            self.drawing_width <= usable_height
        )


    def overflow(self, usable_width: float, usable_height: float) -> tuple[float,float,float]:
        """
        Returns (width_overflow, height_overflow, total_overflow).
        """
        w = max(0.0, self.drawing_width - usable_width)
        h = max(0.0, self.drawing_height - usable_height)
        return w, h, w + h

    def choose_best_orientation(
        self,
        usable_width: float,
        usable_height: float,
    ) -> tuple[bool, float, float]:

        _, _, normal = self.overflow(usable_width, usable_height)

        # rotated dimensions
        rw = self.drawing_height
        rh = self.drawing_width

        rotated = (
            max(0.0, rw - usable_width)
            + max(0.0, rh - usable_height)
        )

        if rotated < normal:
            self.rotate90()
            self.width, self.height = self.height, self.width
            return True, normal, rotated

        return False, normal, rotated

    def _rotate_point_90(self, point: Point, center: Point) -> None:
        """
        Rotate one point 90° clockwise about a fixed centre.
        """

        dx = point.x - center.x
        dy = point.y - center.y

        new_x = center.x + dy
        new_y = center.y - dx

        point.x = new_x
        point.y = new_y

    def rotate90(self) -> None:
        """
        Rotate the entire drawing 90° clockwise.
        """

        center = self.center

        for obj in self.objects:

            if isinstance(obj, Line):

                self._rotate_point_90(obj.start, center)
                self._rotate_point_90(obj.end, center)

            elif isinstance(obj, Bezier):

                self._rotate_point_90(obj.start, center)
                self._rotate_point_90(obj.control1, center)
                self._rotate_point_90(obj.control2, center)
                self._rotate_point_90(obj.end, center)

    def summary(self, enabled: bool = DEBUG) -> None:
        if not enabled:
            return
        print("-------------------------------------")
        print(self.name)
        print("-------------------------------------")
        print(f"Page Size : {self.width:.2f} × {self.height:.2f} mm")
        print(f"Lines     : {self.line_count}")
        print(f"Beziers   : {self.bezier_count}")
        print(f"Objects   : {len(self.objects)}")
        left, top, right, bottom = self.bounds
        print()
        print("Geometry")
        print(f"   Left   : {left:.2f}")
        print(f"   Top    : {top:.2f}")
        print(f"   Right  : {right:.2f}")
        print(f"   Bottom : {bottom:.2f}")
        print(f"   Width  : {self.drawing_width:.2f}")
        print(f"   Height : {self.drawing_height:.2f}")
        print()






