from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from .config import SimulationConfig
from .math_utils import Vec2
from .world import World


class SimulationGUI:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.world = World(config)
        self.initial_agent_count = 12
        self.initial_food_count = 20

        self.debug = False
        self.inspect_mode = False
        self.paused = False
        self.selected_agent_id: int | None = None

        self.root = tk.Tk()
        self.root.title("Artificial Life V1")
        self.root.geometry("1200x800")
        self.root.minsize(900, 650)

        self.controls_frame = tk.Frame(self.root, bg="#1A1F2B", padx=12, pady=12)
        self.controls_frame.pack(fill="x")

        self.canvas = tk.Canvas(
            self.root,
            width=self.config.world_width,
            height=self.config.world_height,
            bg="#10141C",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.agent_count_var = tk.IntVar(value=self.initial_agent_count)
        self.food_count_var = tk.IntVar(value=self.initial_food_count)

        self.details_window: tk.Toplevel | None = None
        self.details_text: tk.Text | None = None

        self._build_controls()

        self.root.bind("<d>", self.toggle_debug)
        self.root.bind("<D>", self.toggle_debug)
        self.root.bind("<i>", self.toggle_inspect_mode)
        self.root.bind("<I>", self.toggle_inspect_mode)
        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("<r>", self.reset_world)
        self.root.bind("<R>", self.reset_world)
        self.root.bind("<s>", self.single_step)
        self.root.bind("<S>", self.single_step)
        self.canvas.bind("<Button-1>", self.left_click)
        self.canvas.bind("<Button-3>", self.right_click)
        self.canvas.bind("<Button-2>", self.middle_click)

    def _build_controls(self) -> None:
        title = tk.Label(
            self.controls_frame,
            text="Start instellingen",
            fg="#F2F2F2",
            bg="#1A1F2B",
            font=("Consolas", 12, "bold"),
        )
        title.grid(row=0, column=0, padx=(0, 10), pady=4)

        tk.Label(self.controls_frame, text="Agents:", fg="#F2F2F2", bg="#1A1F2B").grid(
            row=0, column=1, padx=(0, 6)
        )
        tk.Spinbox(self.controls_frame, from_=1, to=300, width=6, textvariable=self.agent_count_var).grid(
            row=0, column=2, padx=(0, 12)
        )

        tk.Label(self.controls_frame, text="Food:", fg="#F2F2F2", bg="#1A1F2B").grid(row=0, column=3, padx=(0, 6))
        tk.Spinbox(self.controls_frame, from_=0, to=500, width=6, textvariable=self.food_count_var).grid(
            row=0, column=4, padx=(0, 12)
        )

        ttk.Button(self.controls_frame, text="Start / Reset", command=self.reset_world).grid(
            row=0, column=5, padx=(0, 12)
        )

        help_text = "D=debug | I=inspectie venster | Spatie=pauze | LMB=eten | RMB=spawn agent | MMB=select agent"
        tk.Label(
            self.controls_frame,
            text=help_text,
            fg="#B9C4D8",
            bg="#1A1F2B",
            font=("Consolas", 10),
        ).grid(row=0, column=6, sticky="w")

    def run(self) -> None:
        self.reset_world()
        self._loop()
        self.root.mainloop()

    def _loop(self) -> None:
        if not self.paused:
            self.world.tick()
        self.draw()
        self._refresh_details_window()
        interval_ms = int(1000 / self.config.tick_rate_hz)
        self.root.after(interval_ms, self._loop)

    def _world_to_screen(self, position: Vec2) -> Vec2:
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)
        sx = position.x * canvas_w / self.config.world_width
        sy = position.y * canvas_h / self.config.world_height
        return Vec2(sx, sy)

    def _screen_to_world(self, x: float, y: float) -> Vec2:
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)
        wx = x * self.config.world_width / canvas_w
        wy = y * self.config.world_height / canvas_h
        return Vec2(wx, wy)

    def _scale_radius(self, radius: float) -> float:
        canvas_w = max(self.canvas.winfo_width(), 1)
        canvas_h = max(self.canvas.winfo_height(), 1)
        x_scale = canvas_w / self.config.world_width
        y_scale = canvas_h / self.config.world_height
        return radius * min(x_scale, y_scale)

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
            p = self._world_to_screen(food.position)
            r = self._scale_radius(4)
            self.canvas.create_oval(p.x - r, p.y - r, p.x + r, p.y + r, fill="#43D663", outline="")

    def _draw_agents(self) -> None:
        for agent in self.world.state.agents:
            p = self._world_to_screen(agent.position)
            r = self._scale_radius(7)
            stress = min(agent.emotions.stress / 10.0, 1.0)
            energy = max(min(agent.emotions.energy / 8.0, 1.0), 0.0)
            red = int(60 + 170 * stress)
            blue = int(140 * energy + 50)
            color = f"#{red:02x}4a{blue:02x}"
            width = 2 if self.selected_agent_id == agent.entity_id else 1
            outline = "#F2F2F2" if self.selected_agent_id == agent.entity_id else "#0C0C0C"
            self.canvas.create_oval(p.x - r, p.y - r, p.x + r, p.y + r, fill=color, outline=outline, width=width)

            dx = math.cos(agent.heading) * self._scale_radius(10)
            dy = math.sin(agent.heading) * self._scale_radius(10)
            self.canvas.create_line(p.x, p.y, p.x + dx, p.y + dy, fill="#E6EEF8", width=1)

            if self.inspect_mode:
                self.canvas.create_text(
                    p.x,
                    p.y - self._scale_radius(12),
                    text=str(agent.entity_id),
                    fill="#F7DD72",
                    font=("Consolas", max(int(self._scale_radius(6)), 8), "bold"),
                )

    def _draw_territories(self) -> None:
        for agent in self.world.state.agents:
            c = self._world_to_screen(agent.territory.center)
            r = self._scale_radius(agent.territory.radius)
            self.canvas.create_oval(c.x - r, c.y - r, c.x + r, c.y + r, outline="#356B45", width=1, dash=(4, 3))

    def _draw_vision(self) -> None:
        for agent in self.world.state.agents:
            p = self._world_to_screen(agent.position)
            r = self._scale_radius(self.config.vision_range)
            self.canvas.create_oval(p.x - r, p.y - r, p.x + r, p.y + r, outline="#2A4165", width=1)

    def _draw_smells(self) -> None:
        for smell in self.world.state.smells:
            p = self._world_to_screen(smell.position)
            r = self._scale_radius(smell.radius)
            color = "#6A5ACD" if smell.source_type == "death" else "#2D6A4F"
            self.canvas.create_oval(p.x - r, p.y - r, p.x + r, p.y + r, outline=color, width=1)

    def _draw_hud(self) -> None:
        debug_text = "ON" if self.debug else "OFF"
        inspect_text = "ON" if self.inspect_mode else "OFF"
        hud = (
            f"Tick: {self.world.state.tick} | Agents: {len(self.world.state.agents)} | "
            f"Food: {len(self.world.state.foods)} | Dead: {self.world.state.dead_count} | "
            f"Debug: {debug_text} | Inspect: {inspect_text} | Paused: {self.paused}"
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

    def _refresh_details_window(self) -> None:
        if not self.inspect_mode:
            if self.details_window is not None and self.details_window.winfo_exists():
                self.details_window.destroy()
            self.details_window = None
            self.details_text = None
            return

        if self.details_window is None or not self.details_window.winfo_exists():
            self.details_window = tk.Toplevel(self.root)
            self.details_window.title("Agent inspectie")
            self.details_window.geometry("560x700")
            self.details_text = tk.Text(self.details_window, wrap="word", bg="#0E1118", fg="#E4EAF3")
            self.details_text.pack(fill="both", expand=True)

        if self.details_text is None:
            return

        lines: list[str] = []
        for agent in sorted(self.world.state.agents, key=lambda a: a.entity_id):
            status = "angstig" if agent.emotions.fear > 1.2 else "kalm"
            if agent.current_intent == "eat":
                status = "zoeken naar eten"
            elif agent.current_intent == "attack":
                status = "aanvallen"
            elif agent.current_intent == "flee":
                status = "vluchten"
            elif agent.current_intent == "freeze":
                status = "bevroren"

            lines.append(
                f"Agent #{agent.entity_id} | status={status} | intent={agent.current_intent} | hp={agent.hp:.2f}"
            )
            lines.append(
                "  emoties: "
                f"energy={agent.emotions.energy:.2f}, stress={agent.emotions.stress:.2f}, fear={agent.emotions.fear:.2f}, "
                f"pain={agent.emotions.pain:.2f}, aggression={agent.emotions.aggression:.2f}, overload={agent.emotions.stimulus_overload:.2f}"
            )
            lines.append(
                "  beweging: "
                f"pos=({agent.position.x:.1f}, {agent.position.y:.1f}), heading={agent.heading:.2f}, "
                f"speed={agent.speed:.2f}/{agent.max_speed:.2f}, frozen_ticks={agent.frozen_ticks}"
            )
            lines.append(
                "  parameters: "
                f"fight_bias={agent.bias_fight:.2f}, flight_bias={agent.bias_flight:.2f}, freeze_bias={agent.bias_freeze:.2f}"
            )
            lines.append(
                "  territory: "
                f"center=({agent.territory.center.x:.1f}, {agent.territory.center.y:.1f}), "
                f"radius={agent.territory.radius:.1f}, strength={agent.territory.strength:.2f}"
            )
            lines.append(
                "  geheugen/social: "
                f"place_intensity={agent.memory.place_intensity:.2f}, relations={len(agent.relationships)}, "
                f"entity_memories={len(agent.memory.entity_emotions)}"
            )
            lines.append("-" * 88)

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", "\n".join(lines) if lines else "Geen actieve agents")
        self.details_text.config(state="disabled")

    def toggle_debug(self, _event=None) -> None:
        self.debug = not self.debug

    def toggle_inspect_mode(self, _event=None) -> None:
        self.inspect_mode = not self.inspect_mode

    def toggle_pause(self, _event=None) -> None:
        self.paused = not self.paused

    def reset_world(self, _event=None) -> None:
        self.initial_agent_count = max(self.agent_count_var.get(), 1)
        self.initial_food_count = max(self.food_count_var.get(), 0)
        self.world.seed(agent_count=self.initial_agent_count, food_count=self.initial_food_count)
        self.selected_agent_id = None

    def single_step(self, _event=None) -> None:
        if self.paused:
            self.world.tick()
            self.draw()
            self._refresh_details_window()

    def left_click(self, event) -> None:
        click_pos = self._screen_to_world(event.x, event.y)
        self.world.spawn_food(click_pos)

    def right_click(self, event) -> None:
        click_pos = self._screen_to_world(event.x, event.y)
        agent = self.world.spawn_agent(click_pos)
        self.selected_agent_id = agent.entity_id

    def middle_click(self, event) -> None:
        click_pos = self._screen_to_world(event.x, event.y)
        for agent in self.world.state.agents:
            if (agent.position - click_pos).length() <= 10:
                self.selected_agent_id = agent.entity_id
                return
        self.selected_agent_id = None
