from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import SimulationConfig
from .entities import Agent, Entity, EntityType, Food
from .math_utils import Vec2, angle_to_vector, clamp_angle_rad, vector_to_angle
from .perception import Perception, PerceptionType


@dataclass
class Decision:
    intent: str
    target: Optional[Entity] = None


class PerceptionStrategy(ABC):
    @abstractmethod
    def perceive(self, agent: Agent, entities: List[Entity]) -> List[Perception]:
        raise NotImplementedError


class EmotionStrategy(ABC):
    @abstractmethod
    def update(self, agent: Agent, perceptions: List[Perception]) -> None:
        raise NotImplementedError


class DecisionStrategy(ABC):
    @abstractmethod
    def decide(self, agent: Agent, perceptions: List[Perception]) -> Decision:
        raise NotImplementedError


class ActionStrategy(ABC):
    @abstractmethod
    def act(self, agent: Agent, decision: Decision, config: SimulationConfig) -> None:
        raise NotImplementedError


class BasicPerceptionStrategy(PerceptionStrategy):
    def __init__(self, config: SimulationConfig, rng: random.Random):
        self.config = config
        self.rng = rng

    def perceive(self, agent: Agent, entities: List[Entity]) -> List[Perception]:
        perceptions: List[Perception] = []
        for entity in entities:
            if entity.entity_id == agent.entity_id:
                continue
            offset = entity.position - agent.position
            distance = offset.length()
            if distance <= self.config.vision_range:
                noise = Vec2(
                    self.rng.uniform(-3.0, 3.0),
                    self.rng.uniform(-3.0, 3.0),
                )
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.VISUAL,
                        source_type=entity.entity_type.value,
                        estimated_position=entity.position + noise,
                        estimated_distance=max(distance + self.rng.uniform(-2.0, 2.0), 0.0),
                        intensity=1.0 - distance / self.config.vision_range,
                        threat=1.0 if entity.entity_type == EntityType.AGENT else 0.2,
                    )
                )
            if distance <= self.config.touch_radius:
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.TACTILE,
                        source_type=entity.entity_type.value,
                        estimated_position=entity.position,
                        estimated_distance=distance,
                        intensity=1.0,
                        threat=1.2,
                    )
                )
        return perceptions


class BasicEmotionStrategy(EmotionStrategy):
    def update(self, agent: Agent, perceptions: List[Perception]) -> None:
        threat_sum = sum(perception.threat for perception in perceptions)
        agent.emotions.fear = min(agent.emotions.fear + threat_sum * 0.1, 5.0)
        agent.emotions.stimulus_overload = min(len(perceptions) * 0.2, 3.0)
        agent.emotions.stress = max(
            agent.emotions.fear
            + agent.emotions.pain
            + agent.emotions.stimulus_overload
            - agent.emotions.energy,
            0.0,
        )


class ScoreBasedDecisionStrategy(DecisionStrategy):
    def __init__(self, rng: random.Random):
        self.rng = rng

    def decide(self, agent: Agent, perceptions: List[Perception]) -> Decision:
        intents: Dict[str, float] = {
            "eat": agent.emotions.energy * -0.4 + 2.0,
            "attack": agent.emotions.aggression + agent.emotions.stress * 0.2,
            "flee": agent.emotions.stress * 0.6 + agent.emotions.fear,
            "patrol": 1.0,
            "rest": 1.5 - agent.emotions.stress,
        }
        top_intent = max(intents, key=intents.get)
        agent.current_intent = top_intent
        target = None
        if top_intent == "eat":
            target = self._find_target(perceptions, EntityType.FOOD.value)
        if top_intent == "attack":
            target = self._find_target(perceptions, EntityType.AGENT.value)
        return Decision(intent=top_intent, target=target)

    def _find_target(self, perceptions: List[Perception], source_type: str) -> Optional[Entity]:
        for perception in perceptions:
            if perception.source_type == source_type and perception.estimated_position is not None:
                return Entity(entity_id=-1, entity_type=EntityType(source_type), position=perception.estimated_position)
        return None


class MovementActionStrategy(ActionStrategy):
    def __init__(self, rng: random.Random):
        self.rng = rng

    def act(self, agent: Agent, decision: Decision, config: SimulationConfig) -> None:
        if decision.intent == "rest":
            agent.speed = max(agent.speed - 0.3, 0.0)
            return
        target_direction = angle_to_vector(agent.heading)
        if decision.target is not None:
            target_direction = (decision.target.position - agent.position).normalized()
        if decision.intent == "flee":
            target_direction = target_direction * -1

        target_angle = vector_to_angle(target_direction)
        max_turn = math.radians(agent.turn_rate_deg)
        angle_diff = clamp_angle_rad(target_angle - agent.heading)
        angle_step = max(-max_turn, min(max_turn, angle_diff))
        noise = math.radians(self.rng.uniform(-config.noise_angle_deg, config.noise_angle_deg))
        agent.heading = clamp_angle_rad(agent.heading + angle_step + noise)
        agent.speed = min(agent.speed + 0.2, agent.max_speed)
