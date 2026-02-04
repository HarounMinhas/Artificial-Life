from dataclasses import dataclass
from enum import Enum
from typing import Optional

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
    estimated_position: Optional[Vec2]
    estimated_distance: float
    intensity: float
    threat: float
