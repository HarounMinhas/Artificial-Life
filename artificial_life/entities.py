from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .math_utils import Vec2


class EntityType(str, Enum):
    AGENT = "agent"
    FOOD = "food"
    OBSTACLE = "obstacle"


@dataclass
class Entity:
    entity_id: int
    entity_type: EntityType
    position: Vec2


@dataclass
class Food(Entity):
    energy: float = 3.0


@dataclass
class Territory:
    center: Vec2
    radius: float
    strength: float


@dataclass
class EmotionState:
    stress: float = 0.0
    fear: float = 0.0
    pain: float = 0.0
    stimulus_overload: float = 0.0
    energy: float = 5.0
    aggression: float = 0.0


@dataclass
class MemoryAssociation:
    place_emotion: Optional[Vec2] = None
    intensity: float = 0.0


@dataclass
class Agent(Entity):
    heading: float
    speed: float
    max_speed: float
    turn_rate_deg: float
    emotions: EmotionState = field(default_factory=EmotionState)
    territory: Territory = field(default_factory=lambda: Territory(Vec2(0, 0), 80.0, 0.5))
    bias_fight: float = 0.33
    bias_flight: float = 0.33
    bias_freeze: float = 0.34
    memory: MemoryAssociation = field(default_factory=MemoryAssociation)
    current_intent: Optional[str] = None
