from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List

from .config import SimulationConfig
from .entities import Agent, AgentLLMState, Entity, EntityType, Food, SocialBond, Territory
from .llm_bridge import AsyncLLMDecisionBroker, LLMDecisionResponse
from .math_utils import Vec2, angle_to_vector
from .perception import Perception, PerceptionType
from .strategies import ALLOWED_INTENTS, BasicEmotionStrategy, BasicPerceptionStrategy, Decision, MovementActionStrategy, ScoreBasedDecisionStrategy


@dataclass
class SmellCloud:
    source_type: str
    position: Vec2
    radius: float
    intensity: float


@dataclass
class SoundEvent:
    signal: str
    position: Vec2
    radius: float
    intensity: float


@dataclass
class WorldState:
    agents: List[Agent] = field(default_factory=list)
    foods: List[Food] = field(default_factory=list)
    smells: List[SmellCloud] = field(default_factory=list)
    sounds: List[SoundEvent] = field(default_factory=list)
    dead_count: int = 0
    tick: int = 0
    llm_submitted: int = 0
    llm_completed: int = 0
    llm_failed: int = 0
    llm_used: int = 0


class World:
    def __init__(self, config: SimulationConfig, rng: random.Random | None = None) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self.state = WorldState()
        self.perception_strategy = BasicPerceptionStrategy(config, self.rng)
        self.emotion_strategy = BasicEmotionStrategy()
        self.decision_strategy = ScoreBasedDecisionStrategy(config, self.rng)
        self.action_strategy = MovementActionStrategy(self.rng)
        self.llm_broker = AsyncLLMDecisionBroker(config)
        self._next_agent_id = 0
        self._next_food_id = 1000

    def seed(self, agent_count: int = 10, food_count: int = 20) -> None:
        self.state = WorldState()
        self._next_agent_id = 0
        self._next_food_id = 1000
        self.state.agents = [self._new_agent(self._random_position()) for _ in range(agent_count)]
        self.state.foods = [
            Food(
                entity_id=self._new_food_id(),
                entity_type=EntityType.FOOD,
                position=self._random_position(),
                energy=self.config.food_energy,
            )
            for _ in range(food_count)
        ]

    def spawn_food(self, position: Vec2 | None = None) -> None:
        self.state.foods.append(
            Food(
                entity_id=self._new_food_id(),
                entity_type=EntityType.FOOD,
                position=position or self._random_position(),
                energy=self.config.food_energy,
            )
        )

    def spawn_agent(self, position: Vec2 | None = None) -> Agent:
        agent = self._new_agent(position or self._random_position())
        self.state.agents.append(agent)
        return agent

    def tick(self) -> None:
        self.state.tick += 1
        entities = self._all_entities()
        perceptions_map: dict[int, List[Perception]] = {}
        decisions: dict[int, Decision] = {}

        self._update_clouds()
        self._perceive(entities, perceptions_map)
        self._update_emotions(perceptions_map)
        self._collect_llm_results()
        self._submit_llm_requests(perceptions_map)
        self._decide(perceptions_map, decisions)
        self._act(decisions)
        self._interact(decisions)
        self._social_update()
        self._decay()

    def _all_entities(self) -> List[Entity]:
        return [*self.state.agents, *self.state.foods]

    def _update_clouds(self) -> None:
        next_smells: list[SmellCloud] = []
        for smell in self.state.smells:
            smell.radius += self.config.smell_growth_per_tick
            smell.intensity = max(smell.intensity - self.config.smell_decay_per_tick, 0.0)
            if smell.intensity > 0.02:
                next_smells.append(smell)
        self.state.smells = next_smells
        self.state.sounds = []

    def _perceive(self, entities: List[Entity], perceptions_map: dict[int, List[Perception]]) -> None:
        for agent in self.state.agents:
            perceptions = self.perception_strategy.perceive(agent, entities)
            perceptions.extend(self._perceive_smells(agent))
            perceptions.extend(self._perceive_sounds(agent))
            perceptions.sort(key=lambda p: (-p.threat, p.estimated_distance, -p.intensity))
            perceptions_map[agent.entity_id] = perceptions[: self.config.perception_limit]

    def _perceive_smells(self, agent: Agent) -> list[Perception]:
        perceptions: list[Perception] = []
        for smell in self.state.smells:
            distance = (smell.position - agent.position).length()
            if distance <= smell.radius:
                intensity = max(smell.intensity * (1 - distance / max(smell.radius, 1.0)), 0.0)
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.OLFACTORY,
                        source_type=smell.source_type,
                        source_id=-1,
                        estimated_position=None,
                        estimated_distance=distance,
                        intensity=intensity,
                        threat=0.9 if smell.source_type == EntityType.AGENT.value else 0.2,
                        signal="death" if smell.source_type == "death" else "",
                    )
                )
        return perceptions

    def _perceive_sounds(self, agent: Agent) -> list[Perception]:
        perceptions: list[Perception] = []
        for sound in self.state.sounds:
            distance = (sound.position - agent.position).length()
            if distance <= sound.radius:
                intensity = max(sound.intensity * (1 - distance / sound.radius), 0.0)
                perceptions.append(
                    Perception(
                        perception_type=PerceptionType.AUDITORY,
                        source_type="signal",
                        source_id=-1,
                        estimated_position=None,
                        estimated_distance=distance,
                        intensity=intensity,
                        threat=0.7 if sound.signal in {"danger", "death"} else 0.1,
                        signal=sound.signal,
                    )
                )
        return perceptions

    def _update_emotions(self, perceptions_map: dict[int, List[Perception]]) -> None:
        for agent in self.state.agents:
            perceptions = perceptions_map.get(agent.entity_id, [])
            self.emotion_strategy.update(agent, perceptions)
            if self._inside_territory(agent):
                agent.emotions.stress = max(agent.emotions.stress - 0.2 * agent.territory.strength, 0.0)
                agent.territory.strength = min(agent.territory.strength + 0.005, 1.0)
            else:
                agent.emotions.stress += 0.05

            for p in perceptions:
                if p.source_id >= 0:
                    agent.memory.entity_emotions[p.source_id] = max(
                        agent.memory.entity_emotions.get(p.source_id, 0.0),
                        agent.emotions.stress,
                    )
            if agent.emotions.stress > self.config.stress_threshold:
                agent.memory.place_emotion = agent.position
                agent.memory.place_intensity = min(agent.memory.place_intensity + 0.1, 1.0)

    def _collect_llm_results(self) -> None:
        for result in self.llm_broker.collect_ready():
            self._apply_llm_result(result)

    def _apply_llm_result(self, result: LLMDecisionResponse) -> None:
        agent = self._agent_by_id(result.agent_id)
        if agent is None:
            return
        agent.llm.pending_request_id = None
        agent.llm.thinking_state = "idle"
        agent.llm.last_raw_response = result.raw_response
        self.state.llm_completed += 1
        if result.error:
            agent.llm.last_error = result.error
            self.state.llm_failed += 1
            return
        agent.llm.last_error = None
        if result.decision is None:
            self.state.llm_failed += 1
            return
        ttl = int(result.decision.get("ttl_ticks", self.config.llm_response_ttl_ticks))
        ttl = max(1, min(ttl, self.config.llm_response_ttl_ticks))
        agent.llm.decision = result.decision
        agent.llm.decision_ready_tick = self.state.tick
        agent.llm.decision_expires_tick = self.state.tick + ttl
        agent.llm.next_allowed_tick = self.state.tick + self.config.llm_cooldown_ticks

    def _submit_llm_requests(self, perceptions_map: dict[int, List[Perception]]) -> None:
        if not self.config.llm_enabled:
            return
        for agent in self.state.agents:
            if not agent.llm.enabled:
                continue
            if agent.llm.pending_request_id is not None:
                continue
            if self.state.tick < agent.llm.next_allowed_tick:
                continue
            if not self.llm_broker.can_submit():
                return
            if not self._should_query_llm(agent):
                continue
            payload = self._build_llm_payload(agent, perceptions_map.get(agent.entity_id, []))
            request_id = self.llm_broker.submit(agent.entity_id, payload)
            if request_id is None:
                return
            agent.llm.pending_request_id = request_id
            agent.llm.thinking_state = "pending"
            agent.llm.last_error = None
            self.state.llm_submitted += 1

    def _should_query_llm(self, agent: Agent) -> bool:
        return (
            agent.emotions.stress >= self.config.llm_trigger_stress
            or agent.emotions.fear >= self.config.llm_trigger_fear
            or agent.emotions.pain >= self.config.llm_trigger_pain
        )

    def _build_llm_payload(self, agent: Agent, perceptions: list[Perception]) -> dict:
        intents = self.decision_strategy.score_intents(agent, perceptions)
        top_perceptions = [
            {
                "type": p.perception_type.value,
                "source_type": p.source_type,
                "distance": round(p.estimated_distance, 2),
                "threat": round(p.threat, 2),
                "intensity": round(p.intensity, 2),
                "signal": p.signal,
            }
            for p in perceptions[:3]
        ]
        return {
            "tick": self.state.tick,
            "agent_id": agent.entity_id,
            "state": {
                "stress": round(agent.emotions.stress, 3),
                "fear": round(agent.emotions.fear, 3),
                "pain": round(agent.emotions.pain, 3),
                "energy": round(agent.emotions.energy, 3),
                "aggression": round(agent.emotions.aggression, 3),
            },
            "base_intents": intents,
            "perceptions": top_perceptions,
            "world": {
                "width": self.config.world_width,
                "height": self.config.world_height,
            },
        }

    def _decide(self, perceptions_map: dict[int, List[Perception]], decisions: dict[int, Decision]) -> None:
        for agent in self.state.agents:
            base_decision = self.decision_strategy.decide(agent, perceptions_map.get(agent.entity_id, []))
            decisions[agent.entity_id] = self._resolve_llm_decision(agent, base_decision)

    def _resolve_llm_decision(self, agent: Agent, base: Decision) -> Decision:
        if not self.config.llm_enabled or not agent.llm.enabled:
            return base
        raw = agent.llm.decision
        if raw is None:
            return base
        if self.state.tick > agent.llm.decision_expires_tick:
            agent.llm.decision = None
            return base
        intent = str(raw.get("intent", "")).strip().lower()
        confidence = float(raw.get("confidence", 0.0))
        if intent not in ALLOWED_INTENTS or confidence < self.config.llm_min_confidence:
            return base
        target = raw.get("target")
        target_position: Vec2 | None = None
        if isinstance(target, dict) and "x" in target and "y" in target:
            try:
                target_position = Vec2(float(target["x"]), float(target["y"])).clamp(
                    0,
                    self.config.world_width,
                    0,
                    self.config.world_height,
                )
            except (TypeError, ValueError):
                target_position = None
        agent.current_intent = intent
        self.state.llm_used += 1
        return Decision(intent=intent, target_position=target_position)

    def set_agent_llm_enabled(self, agent_id: int, enabled: bool) -> None:
        agent = self._agent_by_id(agent_id)
        if agent is None:
            return
        agent.llm.enabled = enabled
        if not enabled:
            if agent.llm.pending_request_id:
                self.llm_broker.cancel_agent(agent.entity_id)
            agent.llm.pending_request_id = None
            agent.llm.thinking_state = "idle"
            agent.llm.decision = None

    def set_global_llm_enabled(self, enabled: bool) -> None:
        self.config = type(self.config)(**{**self.config.__dict__, "llm_enabled": enabled})
        for agent in self.state.agents:
            self.set_agent_llm_enabled(agent.entity_id, enabled)

    def _agent_by_id(self, agent_id: int) -> Agent | None:
        for agent in self.state.agents:
            if agent.entity_id == agent_id:
                return agent
        return None

    def _act(self, decisions: dict[int, Decision]) -> None:
        for agent in self.state.agents:
            decision = decisions[agent.entity_id]
            self.action_strategy.act(agent, decision, self.config)
            movement = angle_to_vector(agent.heading) * agent.speed
            next_position = agent.position + movement
            clamped = next_position.clamp(0, self.config.world_width, 0, self.config.world_height)
            if clamped.x != next_position.x or clamped.y != next_position.y:
                agent.emotions.stress += 0.2
                agent.emotions.pain += 0.05
                agent.heading += math.pi
            agent.position = clamped

    def _interact(self, decisions: dict[int, Decision]) -> None:
        self._consume_food()
        self._handle_attacks(decisions)
        if len(self.state.foods) < self.config.min_food:
            self.spawn_food()
        if self.state.tick % self.config.random_food_spawn_ticks == 0:
            self.spawn_food()

    def _consume_food(self) -> None:
        remaining_food: List[Food] = []
        for food in self.state.foods:
            consumed = False
            for agent in self.state.agents:
                if (food.position - agent.position).length() <= self.config.touch_radius:
                    agent.emotions.energy = min(agent.emotions.energy + food.energy, 8.0)
                    self.state.sounds.append(
                        SoundEvent("food", food.position, self.config.hearing_range * 0.5, 0.8)
                    )
                    self.state.smells.append(
                        SmellCloud(EntityType.FOOD.value, food.position, self.config.smell_initial_radius, 0.6)
                    )
                    consumed = True
                    break
            if not consumed:
                remaining_food.append(food)
        self.state.foods = remaining_food

    def _handle_attacks(self, decisions: dict[int, Decision]) -> None:
        dead_ids: set[int] = set()
        for attacker in self.state.agents:
            decision = decisions.get(attacker.entity_id)
            if not decision or decision.intent != "attack":
                continue
            for defender in self.state.agents:
                if defender.entity_id == attacker.entity_id or defender.entity_id in dead_ids:
                    continue
                distance = (defender.position - attacker.position).length()
                if distance <= self.config.attack_range:
                    damage = (attacker.emotions.aggression + attacker.speed + 1.0) * self.config.attack_damage_factor
                    defender.hp -= damage
                    defender.emotions.pain += damage * 0.25
                    defender.emotions.fear += 0.4
                    attacker.emotions.aggression = min(attacker.emotions.aggression + 0.2, 4.0)
                    self._update_relation(attacker, defender.entity_id, trust_delta=-0.2, fear_delta=0.3)
                    self._update_relation(defender, attacker.entity_id, trust_delta=-0.35, fear_delta=0.6)
                    self.state.sounds.append(
                        SoundEvent("danger", defender.position, self.config.hearing_range, 1.0)
                    )
                    if defender.hp <= 0:
                        dead_ids.add(defender.entity_id)
                        self._on_death(defender)
                    break
        if dead_ids:
            self.state.agents = [a for a in self.state.agents if a.entity_id not in dead_ids]
            self.state.dead_count += len(dead_ids)

    def _on_death(self, agent: Agent) -> None:
        self.state.smells.append(SmellCloud("death", agent.position, self.config.smell_initial_radius, 1.0))
        self.state.sounds.append(SoundEvent("death", agent.position, self.config.hearing_range, 1.0))
        for other in self.state.agents:
            if other.entity_id == agent.entity_id:
                continue
            other.emotions.fear += 0.6
            other.emotions.stress += 0.4
            other.territory.strength = max(other.territory.strength - 0.1, 0.0)

    def _social_update(self) -> None:
        for i, agent_a in enumerate(self.state.agents):
            for agent_b in self.state.agents[i + 1 :]:
                distance = (agent_a.position - agent_b.position).length()
                if distance < 45:
                    self._update_relation(agent_a, agent_b.entity_id, trust_delta=0.01, fear_delta=-0.005)
                    self._update_relation(agent_b, agent_a.entity_id, trust_delta=0.01, fear_delta=-0.005)
                in_a = (agent_b.position - agent_a.territory.center).length() < agent_a.territory.radius
                if in_a:
                    agent_a.emotions.stress += 0.08
                    agent_a.emotions.aggression += 0.05

    def _decay(self) -> None:
        for agent in self.state.agents:
            agent.emotions.energy = max(agent.emotions.energy - self.config.decay_rate, 0.0)
            agent.emotions.fear = max(agent.emotions.fear - self.config.decay_rate, 0.0)
            agent.emotions.pain = max(agent.emotions.pain - self.config.pain_decay_per_tick, 0.0)
            agent.emotions.aggression = max(agent.emotions.aggression - self.config.decay_rate, 0.0)
            agent.emotions.stress = max(agent.emotions.stress - self.config.decay_rate * 0.5, 0.0)
            agent.memory.place_intensity = max(agent.memory.place_intensity - self.config.memory_decay, 0.0)
            for other_id in list(agent.memory.entity_emotions):
                agent.memory.entity_emotions[other_id] = max(
                    agent.memory.entity_emotions[other_id] - self.config.memory_decay,
                    0.0,
                )
                if agent.memory.entity_emotions[other_id] == 0:
                    del agent.memory.entity_emotions[other_id]
            for relation in agent.relationships.values():
                relation.trust *= 1 - self.config.relation_decay
                relation.fear *= 1 - self.config.relation_decay

    def _inside_territory(self, agent: Agent) -> bool:
        distance = (agent.position - agent.territory.center).length()
        return distance <= agent.territory.radius

    def _update_relation(self, agent: Agent, other_id: int, trust_delta: float, fear_delta: float) -> None:
        bond = agent.relationships.setdefault(other_id, SocialBond())
        bond.trust = max(min(bond.trust + trust_delta, 1.0), -1.0)
        bond.fear = max(min(bond.fear + fear_delta, 1.0), 0.0)

    def _random_position(self) -> Vec2:
        return Vec2(
            self.rng.uniform(10.0, self.config.world_width - 10.0),
            self.rng.uniform(10.0, self.config.world_height - 10.0),
        )

    def _new_agent(self, position: Vec2) -> Agent:
        agent = Agent(
            entity_id=self._next_agent_id,
            entity_type=EntityType.AGENT,
            position=position,
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
            llm=AgentLLMState(enabled=self.config.llm_enabled),
        )
        self._next_agent_id += 1
        return agent

    def _new_food_id(self) -> int:
        food_id = self._next_food_id
        self._next_food_id += 1
        return food_id
