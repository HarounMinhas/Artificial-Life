from __future__ import annotations

import math
import tkinter as tk

from .config import SimulationConfig
from .math_utils import Vec2
from .world import World


class SimulationGUI:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.world = World(config)
        self.world.seed(agent_count=12, food_count=20)
        self.debug = False
        self.paused = False
        self.selected_agent_id: int | None = None

        self.root = tk.Tk()
        self.root.title("Artificial Life V1")
        self.canvas = tk.Canvas(
            self.root,
            width=self.config.world_width,
            height=self.config.world_height,
            bg="#10141C",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.root.bind("<d>", self.toggle_debug)
        self.root.bind("<D>", self.toggle_debug)
        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("<r>", self.reset_world)
        self.root.bind("<R>", self.reset_world)
        self.root.bind("<s>", self.single_step)
        self.root.bind("<S>", self.single_step)
        self.canvas.bind("<Button-1>", self.left_click)

    def run(self) -> None:
        self._loop()
        self.root.mainloop()

    def _loop(self) -> None:
        if not self.paused:
            self.world.tick()
        self.draw()
        interval_ms = int(1000 / self.config.tick_rate_hz)
        self.root.after(interval_ms, self._loop)

    def draw(self) -> None:
        self.canvas.delete("all")
        if self.debug:
            self._draw_smells()
            self._draw_territories()
            self._draw_vision()
        self._draw_foods()
        self._draw_agents()
        self._draw_hud()

    def _draw_foods(self) -> None:
        for food in self.world.state.foods:
            r = 4
            self.canvas.create_oval(
                food.position.x - r,
                food.position.y - r,
                food.position.x + r,
                food.position.y + r,
                fill="#43D663",
                outline="",
            )

    def _draw_agents(self) -> None:
        for agent in self.world.state.agents:
            r = 7
            stress = min(agent.emotions.stress / 10.0, 1.0)
            energy = max(min(agent.emotions.energy / 8.0, 1.0), 0.0)
            red = int(60 + 170 * stress)
            blue = int(140 * energy + 50)
            color = f"#{red:02x}4a{blue:02x}"
            width = 2 if self.selected_agent_id == agent.entity_id else 1
            outline = "#F2F2F2" if self.selected_agent_id == agent.entity_id else "#0C0C0C"
            self.canvas.create_oval(
                agent.position.x - r,
                agent.position.y - r,
                agent.position.x + r,
                agent.position.y + r,
                fill=color,
                outline=outline,
                width=width,
            )
            dx = math.cos(agent.heading) * 10
            dy = math.sin(agent.heading) * 10
            self.canvas.create_line(
                agent.position.x,
                agent.position.y,
                agent.position.x + dx,
                agent.position.y + dy,
                fill="#E6EEF8",
                width=1,
            )

    def _draw_territories(self) -> None:
        for agent in self.world.state.agents:
            self.canvas.create_oval(
                agent.territory.center.x - agent.territory.radius,
                agent.territory.center.y - agent.territory.radius,
                agent.territory.center.x + agent.territory.radius,
                agent.territory.center.y + agent.territory.radius,
                outline="#356B45",
                width=1,
                dash=(4, 3),
            )

    def _draw_vision(self) -> None:
        for agent in self.world.state.agents:
            self.canvas.create_oval(
                agent.position.x - self.config.vision_range,
                agent.position.y - self.config.vision_range,
                agent.position.x + self.config.vision_range,
                agent.position.y + self.config.vision_range,
                outline="#2A4165",
                width=1,
            )

    def _draw_smells(self) -> None:
        for smell in self.world.state.smells:
            color = "#6A5ACD" if smell.source_type == "death" else "#2D6A4F"
            self.canvas.create_oval(
                smell.position.x - smell.radius,
                smell.position.y - smell.radius,
                smell.position.x + smell.radius,
                smell.position.y + smell.radius,
                outline=color,
                width=1,
            )

    def _draw_hud(self) -> None:
        debug_text = "ON" if self.debug else "OFF"
        hud = (
            f"Tick: {self.world.state.tick} | Agents: {len(self.world.state.agents)} | "
            f"Food: {len(self.world.state.foods)} | Dead: {self.world.state.dead_count} | "
            f"Debug: {debug_text} | Paused: {self.paused}"
        )
        self.canvas.create_text(10, 10, anchor="nw", fill="#F2F2F2", text=hud, font=("Consolas", 11))

        selected = self._selected_agent()
        if selected is not None:
            info = (
                f"Selected {selected.entity_id} | intent={selected.current_intent} | "
                f"energy={selected.emotions.energy:.2f} stress={selected.emotions.stress:.2f} "
                f"fear={selected.emotions.fear:.2f} aggr={selected.emotions.aggression:.2f} hp={selected.hp:.2f}"
            )
            self.canvas.create_text(10, 30, anchor="nw", fill="#F8D66D", text=info, font=("Consolas", 10))

    def _selected_agent(self):
        if self.selected_agent_id is None:
            return None
        for agent in self.world.state.agents:
            if agent.entity_id == self.selected_agent_id:
                return agent
        self.selected_agent_id = None
        return None

    def toggle_debug(self, _event=None) -> None:
        self.debug = not self.debug

    def toggle_pause(self, _event=None) -> None:
        self.paused = not self.paused

    def reset_world(self, _event=None) -> None:
        self.world.seed(agent_count=12, food_count=20)

    def single_step(self, _event=None) -> None:
        if self.paused:
            self.world.tick()
            self.draw()

    def left_click(self, event) -> None:
        click_pos = Vec2(event.x, event.y)
        for agent in self.world.state.agents:
            if (agent.position - click_pos).length() <= 10:
                self.selected_agent_id = agent.entity_id
                return
        self.selected_agent_id = None
        self.world.spawn_food(click_pos)
