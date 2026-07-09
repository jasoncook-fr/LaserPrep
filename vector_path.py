from dataclasses import dataclass, field
from drawing import PathSegment

print("LOADED VECTOR_PATH:", __file__)

@dataclass
class VectorPath:

    objects: list[PathSegment] = field(default_factory=list)

    stroke_color: tuple[int, int, int] | None = None
    fill_color: tuple[int, int, int] | None = None

    stroke_width: float = 0.01

    stroke_enabled: bool = True
    fill_enabled: bool = False

    import_order: int = 0

    filled: bool = False

    # Text imported from Poppler
    is_text: bool = False

    group_id: int = 0

    def add(self, segment: PathSegment):
        self.objects.append(segment)

    def close(self):
        self.closed = True

    @property
    def is_empty(self):
        return len(self.objects) == 0

    @property
    def segment_count(self):
        return len(self.objects)

    @property
    def line_count(self):
        from drawing import Line
        return sum(isinstance(s, Line) for s in self.objects)


    @property
    def bezier_count(self):
        from drawing import Bezier
        return sum(isinstance(s, Bezier) for s in self.objects)

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


