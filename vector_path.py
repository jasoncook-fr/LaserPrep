from dataclasses import dataclass, field
from drawing import PathSegment, Line, Bezier, Point

@dataclass
class VectorPath:
    is_direct_text = False
    objects: list[PathSegment] = field(default_factory=list)

    stroke_color: tuple[int, int, int] | None = None
    fill_color: tuple[int, int, int] | None = None

    stroke_width: float = 0.01

    stroke_enabled: bool = True
    fill_enabled: bool = False

    import_order: int = 0

    filled: bool = False

    is_text: bool = False

    group_id: int = 0

    closed: bool = False

    transform: str | None = None

    source_drawing: int | None = None
    source_bbox = None
    source_items: int = 0

    def add(self, segment: PathSegment):
        self.objects.append(segment)

    def close(self):
        self.closed = True

    @property
    def is_empty(self):
        return len(self.objects) == 0

    @property
    def object_count(self):
        return len(self.objects)

    @property
    def segment_count(self):
        return len(self.objects)

    @property
    def line_count(self):
        return sum(isinstance(s, Line) for s in self.objects)

    @property
    def bezier_count(self):
        return sum(isinstance(s, Bezier) for s in self.objects)

    @property
    def bounds(self):

        if not self.objects:
            return (0.0, 0.0, 0.0, 0.0)

        xs = []
        ys = []

        for obj in self.objects:

            if isinstance(obj, Line):

                xs.extend((obj.start.x, obj.end.x))
                ys.extend((obj.start.y, obj.end.y))

            elif isinstance(obj, Bezier):

                xs.extend((
                    obj.start.x,
                    obj.control1.x,
                    obj.control2.x,
                    obj.end.x,
                ))

                ys.extend((
                    obj.start.y,
                    obj.control1.y,
                    obj.control2.y,
                    obj.end.y,
                ))

        return (
            min(xs),
            min(ys),
            max(xs),
            max(ys),
        )

    @property
    def width(self):
        l, t, r, b = self.bounds
        return r - l

    @property
    def height(self):
        l, t, r, b = self.bounds
        return b - t

    @property
    def center(self):
        l, t, r, b = self.bounds
        return Point(
            (l + r) / 2,
            (t + b) / 2,
        )

    def __iter__(self):
        return iter(self.objects)

    def __len__(self):
        return len(self.objects)

    def __repr__(self):
        return (
            f"VectorPath("
            f"objects={len(self.objects)}, "
            f"closed={self.closed})"
        )
