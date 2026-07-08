from dataclasses import dataclass, field
from drawing import PathSegment


@dataclass
class VectorPath:
    objects: list[PathSegment] = field(default_factory=list)

    import_order: int = 0

    def add(self, obj: PathSegment):
        self.objects.append(obj)
