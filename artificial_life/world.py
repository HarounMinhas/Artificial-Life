from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List

from .config import SimulationConfig
from .entities import Agent, Entity, EntityType, Food, Territory
from .math_utils import Vec2, angle_to_vector
from .perception import Perception
from .strategies import (
    BasicEmotionStrategy,
    BasicPerceptionStrategy,
    Decision,
    MovementActionStrategy,
    ScoreBasedDecisionStrategy,
)


@dataclass
class WorldState:
    agents: List[Agent] = field(default_factory=list)
    foods: List[Food] = field(default_factory=list)
    tick: int = 0


class World:
    def __init__(self, config: SimulationConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self.state = WorldState()
        self.perception_strategy = BasicPerceptionStrategy(config, self.rng)
        self.emotion_strategy = BasicEmotionStrategy()
        self.decision_strategy = ScoreBasedDecisionStrategy(self.rng)
        self.action_strategy = MovementActionStrategy(self.rng)

    def seed(self, agent_count: int = 10, food_count: int = 20) -> None:
        self.state.agents = [
            Agent(
                entity_id=i,
                entity_type=EntityType.AGENT,
                position=self._random_position(),
                heading=self.rng.uniform(-math.pi, math.pi),
                speed=self.rng.uniform(0.2, 1.0),
                max_speed=self.config.max_speed,
                turn_rate_deg=self.config.max_turn_deg,
                territory=Territory(
                    center=self._random_position(),
                    radius=self.rng.uniform(60.0, 120.0),
                    strength=self.rng.uniform(0.3, 0.7),
                ),
                bias_fight=self.rng.uniform(0.2, 0.4),
                bias_flight=self.rng.uniform(0.2, 0.4),
                bias_freeze=self.rng.uniform(0.2, 0.4),
            )
            for i in range(agent_count)
        ]
        self.state.foods = [
            Food(
                entity_id=1000 + i,
                entity_type=EntityType.FOOD,
                position=self._random_position(),
                energy=self.config.food_energy,
            )
            for i in range(food_count)
        ]

    def tick(self) -> None:
        self.state.tick += 1
        entities = self._all_entities()
        perceptions_map: dict[int, List[Perception]] = {}
        decisions: dict[int, Decision] = {}
        self._perceive(entities, perceptions_map)
        self._update_emotions(perceptions_map)
        self._decide(perceptions_map, decisions)
        self._act(decisions)
        self._interact()
        self._decay()

    def _all_entities(self) -> List[Entity]:
        return [*self.state.agents, *self.state.foods]

    def _perceive(self, entities: List[Entity], perceptions_map: dict[int, List[Perception]]) -> None:
        for agent in self.state.agents:
            perceptions = self.perception_strategy.perceive(agent, entities)
            perceptions.sort(key=lambda p: (-p.threat, p.estimated_distance, -p.intensity))
            perceptions_map[agent.entity_id] = perceptions[: self.config.perception_limit]

    def _update_emotions(self, perceptions_map: dict[int, List[Perception]]) -> None:
        for agent in self.state.agents:
            self.emotion_strategy.update(agent, perceptions_map.get(agent.entity_id, []))
            if self._inside_territory(agent):
                agent.emotions.stress = max(agent.emotions.stress - 0.1, 0.0)

    def _decide(self, perceptions_map: dict[int, List[Perception]], decisions: dict[int, Decision]) -> None:
        for agent in self.state.agents:
            decisions[agent.entity_id] = self.decision_strategy.decide(
                agent, perceptions_map.get(agent.entity_id, [])
            )

    def _act(self, decisions: dict[int, Decision]) -> None:
        for agent in self.state.agents:
            decision = decisions[agent.entity_id]
            self.action_strategy.act(agent, decision, self.config)
            movement = angle_to_vector(agent.heading) * agent.speed
            agent.position = (agent.position + movement).clamp(
                0, self.config.world_width, 0, self.config.world_height
            )

    def _interact(self) -> None:
        remaining_food: List[Food] = []
        for food in self.state.foods:
            consumed = False
            for agent in self.state.agents:
                if (food.position - agent.position).length() <= self.config.touch_radius:
                    agent.emotions.energy += food.energy
                    consumed = True
                    break
            if not consumed:
                remaining_food.append(food)
        self.state.foods = remaining_food
        if len(self.state.foods) < 8:
            self.state.foods.append(
                Food(
                    entity_id=1000 + self.state.tick,
                    entity_type=EntityType.FOOD,
                    position=self._random_position(),
                    energy=self.config.food_energy,
                )
            )

    def _decay(self) -> None:
        for agent in self.state.agents:
            agent.emotions.energy = max(agent.emotions.energy - self.config.decay_rate, 0.0)
            agent.emotions.fear = max(agent.emotions.fear - self.config.decay_rate, 0.0)
            agent.emotions.pain = max(agent.emotions.pain - self.config.decay_rate, 0.0)
            agent.emotions.aggression = max(agent.emotions.aggression - self.config.decay_rate, 0.0)

    def _inside_territory(self, agent: Agent) -> bool:
        distance = (agent.position - agent.territory.center).length()
        return distance <= agent.territory.radius

    def _random_position(self) -> Vec2:
        return Vec2(
            self.rng.uniform(10.0, self.config.world_width - 10.0),
            self.rng.uniform(10.0, self.config.world_height - 10.0),
        )
