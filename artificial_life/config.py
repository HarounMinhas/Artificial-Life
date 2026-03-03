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
    smell_decay_per_tick: float = 0.02
    touch_radius: float = 8.0
    perception_limit: int = 6

    noise_angle_deg: float = 2.0
    stress_threshold: float = 6.0
    decay_rate: float = 0.02
    food_energy: float = 3.0

    attack_range: float = 10.0
    attack_damage_factor: float = 0.7
    pain_decay_per_tick: float = 0.06
    min_food: int = 8
    random_food_spawn_ticks: int = 90

    relation_decay: float = 0.01
    memory_decay: float = 0.03

    llm_enabled: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"
    llm_timeout_seconds: float = 1.2
    llm_temperature: float = 0.1
    llm_max_inflight: int = 3
    llm_cooldown_ticks: int = 20
    llm_min_confidence: float = 0.35
    llm_trigger_stress: float = 2.8
    llm_trigger_fear: float = 1.4
    llm_trigger_pain: float = 0.8
    llm_response_ttl_ticks: int = 8
