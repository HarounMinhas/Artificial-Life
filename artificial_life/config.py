from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    tick_rate_hz: int = 30
    world_width: int = 800
    world_height: int = 600
    max_turn_deg: float = 12.0
    max_speed: float = 3.5
    vision_range: float = 140.0
    hearing_range: float = 180.0
    smell_initial_radius: float = 20.0
    smell_growth_per_tick: float = 1.5
    smell_decay_per_tick: float = 0.01
    touch_radius: float = 8.0
    perception_limit: int = 5
    noise_angle_deg: float = 2.0
    stress_threshold: float = 6.0
    decay_rate: float = 0.02
    food_energy: float = 3.0
