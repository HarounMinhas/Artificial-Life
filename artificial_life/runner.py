import time

from .config import SimulationConfig
from .world import World


def run_headless(ticks: int = 300, log_every_ticks: int = 30) -> None:
    config = SimulationConfig()
    world = World(config)
    world.seed()
    for _ in range(ticks):
        world.tick()
        if log_every_ticks > 0 and world.state.tick % log_every_ticks == 0:
            print(
                f"Tick {world.state.tick}: agents={len(world.state.agents)} "
                f"food={len(world.state.foods)}"
            )
        time.sleep(1 / config.tick_rate_hz)


if __name__ == "__main__":
    run_headless()
