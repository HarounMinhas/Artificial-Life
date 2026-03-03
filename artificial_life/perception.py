from dataclasses import dataclass
from enum import Enum

from .math_utils import Vec2


class PerceptionType(str, Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    OLFACTORY = "olfactory"
    TACTILE = "tactile"


@dataclass
class Perception:
    perception_type: PerceptionType
    source_type: str
    source_id: int
    estimated_position: Vec2 | None
    estimated_distance: float
    intensity: float
    threat: float
    signal: str = ""
