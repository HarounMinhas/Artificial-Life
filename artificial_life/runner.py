import argparse
import time

from .config import SimulationConfig
from .gui import SimulationGUI
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
                f"food={len(world.state.foods)} dead={world.state.dead_count}"
            )
        time.sleep(1 / config.tick_rate_hz)


def run_gui() -> None:
    config = SimulationConfig()
    app = SimulationGUI(config)
    app.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Artificial Life V1")
    parser.add_argument("--mode", choices=["headless", "gui"], default="headless")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--log-every", type=int, default=30)
    args = parser.parse_args()

    if args.mode == "gui":
        run_gui()
    else:
        run_headless(ticks=args.ticks, log_every_ticks=args.log_every)


if __name__ == "__main__":
    main()
