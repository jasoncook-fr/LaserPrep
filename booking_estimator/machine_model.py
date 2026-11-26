"""Machine configuration inputs; defaults are placeholders, not calibration."""
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class MachineConfig:
    machine_id: str
    nominal_power_w: float
    travel_speed_mm_s: float
    curve_speed_mm_s: float | None = None
    acceleration_mm_s2: float | None = None
    corner_penalty_factor: float = 0.0
    setup_time_s: float = 0.0
    source: str = "placeholder; replace with measured values"
    def __post_init__(self):
        if not self.machine_id.strip(): raise ValueError("machine_id must be non-empty")
        if any(v<0 for v in (self.nominal_power_w,self.travel_speed_mm_s,self.setup_time_s,self.corner_penalty_factor)): raise ValueError("parameters must be non-negative")
        if self.travel_speed_mm_s<=0: raise ValueError("travel_speed_mm_s must be positive")
        if self.curve_speed_mm_s is not None and self.curve_speed_mm_s<=0: raise ValueError("curve_speed_mm_s must be positive")
        if self.acceleration_mm_s2 is not None and self.acceleration_mm_s2<=0: raise ValueError("acceleration_mm_s2 must be positive")
    def to_dict(self): return asdict(self)

def default_placeholder_configs():
    return [MachineConfig("CO2-60W-placeholder",60,10,source="placeholder; replace with measured values"),
            MachineConfig("CO2-100W-placeholder",100,10,source="placeholder; replace with measured values")]
