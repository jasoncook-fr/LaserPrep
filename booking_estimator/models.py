"""Data models for the experimental booking estimator."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SVGDimensions:
    """Resolved SVG canvas dimensions and user-coordinate scaling."""

    width_mm: Optional[float]
    height_mm: Optional[float]
    viewbox: Optional[tuple[float, float, float, float]]
    scale_x_mm_per_user_unit: Optional[float]
    scale_y_mm_per_user_unit: Optional[float]
    physical_dimensions_known: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def aspect_ratio(self) -> Optional[float]:
        if self.width_mm is None or self.height_mm is None or self.height_mm == 0:
            return None
        return self.width_mm / self.height_mm
