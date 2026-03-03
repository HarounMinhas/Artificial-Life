from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from .config import SimulationConfig
from .entities import Agent, Entity, EntityType
from .math_utils import Vec2, angle_to_vector, clamp_angle_rad, vector_to_angle
from .perception import Perception, PerceptionType


@dataclass
class Decision:
    intent: str
    target_position: Vec2 | None = None
    target_id: int | None = None


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
                noise = Vec2(self.rng.uniform(-3.0, 3.0), self.rng.uniform(-3.0, 3.0))
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.VISUAL,
                        source_type=entity.entity_type.value,
                        source_id=entity.entity_id,
                        estimated_position=entity.position + noise,
                        estimated_distance=max(distance + self.rng.uniform(-2.0, 2.0), 0.0),
                        intensity=max(0.0, 1.0 - distance / self.config.vision_range),
                        threat=1.0 if entity.entity_type == EntityType.AGENT else 0.1,
                    )
                )
            if distance <= self.config.touch_radius:
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.TACTILE,
                        source_type=entity.entity_type.value,
                        source_id=entity.entity_id,
                        estimated_position=entity.position,
                        estimated_distance=distance,
                        intensity=1.0,
                        threat=1.4,
                    )
                )
        return perceptions


class BasicEmotionStrategy(EmotionStrategy):
    def update(self, agent: Agent, perceptions: List[Perception]) -> None:
        threat_sum = sum(perception.threat for perception in perceptions)
        audio_stress = sum(
            p.intensity * 0.7 for p in perceptions if p.perception_type == PerceptionType.AUDITORY
        )
        smell_stress = sum(
            p.intensity * 0.5 for p in perceptions if p.perception_type == PerceptionType.OLFACTORY
        )
        agent.emotions.fear = min(agent.emotions.fear + threat_sum * 0.08 + audio_stress * 0.1, 6.0)
        agent.emotions.stimulus_overload = min(len(perceptions) * 0.2 + audio_stress + smell_stress, 4.0)
        agent.emotions.stress = max(
            agent.emotions.fear
            + agent.emotions.pain
            + agent.emotions.stimulus_overload
            - agent.emotions.energy * 0.8,
            0.0,
        )
        if any(p.signal == "food" for p in perceptions):
            agent.emotions.fear = max(agent.emotions.fear - 0.1, 0.0)


class ScoreBasedDecisionStrategy(DecisionStrategy):
    def __init__(self, config: SimulationConfig, rng: random.Random):
        self.config = config
        self.rng = rng

    def decide(self, agent: Agent, perceptions: List[Perception]) -> Decision:
        food = self._closest(perceptions, EntityType.FOOD.value)
        threat = self._closest(perceptions, EntityType.AGENT.value)
        intents: Dict[str, float] = {
            "eat": (5.0 - agent.emotions.energy) + (1.5 if food else -1.0),
            "attack": agent.bias_fight * agent.emotions.stress + agent.emotions.aggression + (1.0 if threat else -0.5),
            "flee": agent.bias_flight * agent.emotions.stress + agent.emotions.fear + (1.0 if threat else 0.0),
            "freeze": agent.bias_freeze * agent.emotions.stress + agent.emotions.pain * 0.5,
            "patrol": 1.0,
            "rest": 1.5 - agent.emotions.stress,
        }
        if agent.emotions.stress > self.config.stress_threshold:
            intents["freeze"] += 0.8
            intents["flee"] += 0.5

        top_intent = max(intents, key=intents.get)
        agent.current_intent = top_intent

        if top_intent == "eat" and food:
            return Decision(top_intent, food.estimated_position, food.source_id)
        if top_intent in {"attack", "flee"} and threat:
            return Decision(top_intent, threat.estimated_position, threat.source_id)
        return Decision(top_intent)

    def _closest(self, perceptions: List[Perception], source_type: str) -> Perception | None:
        options = [p for p in perceptions if p.source_type == source_type and p.estimated_position is not None]
        if not options:
            return None
        return sorted(options, key=lambda p: p.estimated_distance)[0]


class MovementActionStrategy(ActionStrategy):
    def __init__(self, rng: random.Random):
        self.rng = rng

    def act(self, agent: Agent, decision: Decision, config: SimulationConfig) -> None:
        if decision.intent == "rest":
            agent.speed = max(agent.speed - 0.3, 0.0)
            return
        if decision.intent == "freeze":
            agent.speed = 0.0
            agent.frozen_ticks = 3
            return
        if agent.frozen_ticks > 0:
            agent.frozen_ticks -= 1
            agent.speed = 0.0
            return

        target_direction = angle_to_vector(agent.heading)
        if decision.target_position is not None:
            target_direction = (decision.target_position - agent.position).normalized()
        if decision.intent == "flee":
            target_direction = target_direction * -1

        target_angle = vector_to_angle(target_direction)
        max_turn = math.radians(agent.turn_rate_deg)
        angle_diff = clamp_angle_rad(target_angle - agent.heading)
        angle_step = max(-max_turn, min(max_turn, angle_diff))
        noise = math.radians(self.rng.uniform(-config.noise_angle_deg, config.noise_angle_deg))
        agent.heading = clamp_angle_rad(agent.heading + angle_step + noise)
        speed_boost = 0.3 if decision.intent in {"flee", "attack"} else 0.15
        agent.speed = min(agent.speed + speed_boost, agent.max_speed)
