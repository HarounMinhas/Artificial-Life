import time

from .config import SimulationConfig
from .world import World


def run_headless(ticks: int = 300) -> None:
    config = SimulationConfig()
    world = World(config)
    world.seed()
    for _ in range(ticks):
        world.tick()
        time.sleep(1 / config.tick_rate_hz)


if __name__ == "__main__":
    run_headless()
