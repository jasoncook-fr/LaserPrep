from dataclasses import dataclass, field
from typing import List

from drawing import Drawing


# ============================================================
# PROJECT
# ============================================================

@dataclass
class Project:

    name: str

    drawings: List[Drawing] = field(default_factory=list)

    def add(self, drawing: Drawing):
        self.drawings.append(drawing)

    @property
    def drawing_count(self):
        return len(self.drawings)

    @property
    def object_count(self):
        return sum(len(d.objects) for d in self.drawings)

    @property
    def line_count(self):
        return sum(d.line_count for d in self.drawings)

    @property
    def bezier_count(self):
        return sum(d.bezier_count for d in self.drawings)

    def summary(self):

        print()
        print("========================================")
        print(self.name)
        print("========================================")

        print(f"Drawings : {self.drawing_count}")
        print(f"Lines    : {self.line_count}")
        print(f"Beziers  : {self.bezier_count}")
        print(f"Objects  : {self.object_count}")
        print()

        for drawing in self.drawings:
            drawing.summary()
