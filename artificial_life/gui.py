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
        self.root.geometry("1250x820")
        self.root.minsize(980, 680)

        self.global_llm_enabled = tk.BooleanVar(master=self.root, value=self.config.llm_enabled)

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
        self.details_canvas: tk.Canvas | None = None
        self.details_list_frame: tk.Frame | None = None
        self._detail_rows: dict[int, tk.BooleanVar] = {}
        self._detail_cards: dict[int, tk.LabelFrame] = {}
        self._detail_llm_labels: dict[int, tk.Label] = {}
        self._detail_status_labels: dict[int, tk.Label] = {}
        self._detail_llm_prompt_boxes: dict[int, tk.Text] = {}
        self._detail_llm_response_boxes: dict[int, tk.Text] = {}

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

        ttk.Checkbutton(
            self.controls_frame,
            text="LLM globaal",
            variable=self.global_llm_enabled,
            command=self._toggle_global_llm,
        ).grid(row=0, column=6, padx=(0, 12))

        help_text = (
            "D=debug | I=inspectie venster | Spatie=pauze | "
            "LMB=eten | RMB=spawn agent | MMB=select agent"
        )
        tk.Label(
            self.controls_frame,
            text=help_text,
            fg="#B9C4D8",
            bg="#1A1F2B",
            font=("Consolas", 10),
        ).grid(row=0, column=7, sticky="w")

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
            if self.config.llm_enabled and agent.llm.enabled:
                outline = "#7ED6FF" if self.selected_agent_id != agent.entity_id else "#F2F2F2"
            else:
                outline = "#0C0C0C" if self.selected_agent_id != agent.entity_id else "#F2F2F2"
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
        llm_text = "ON" if self.config.llm_enabled else "OFF"
        hud = (
            f"Tick: {self.world.state.tick} | Agents: {len(self.world.state.agents)} | "
            f"Food: {len(self.world.state.foods)} | Dead: {self.world.state.dead_count} | "
            f"Debug: {debug_text} | Inspect: {inspect_text} | Paused: {self.paused} | LLM: {llm_text}"
        )
        self.canvas.create_text(10, 10, anchor="nw", fill="#F2F2F2", text=hud, font=("Consolas", 11))

        llm_stats = (
            f"LLM submitted={self.world.state.llm_submitted} completed={self.world.state.llm_completed} "
            f"failed={self.world.state.llm_failed} used={self.world.state.llm_used}"
        )
        self.canvas.create_text(10, 30, anchor="nw", fill="#9FD0FF", text=llm_stats, font=("Consolas", 10))

        selected = self._selected_agent()
        if selected is not None:
            info = (
                f"Selected {selected.entity_id} | intent={selected.current_intent} | hp={selected.hp:.2f} | "
                f"energy={selected.emotions.energy:.2f} stress={selected.emotions.stress:.2f} fear={selected.emotions.fear:.2f} "
                f"| llm={selected.llm.enabled} ({selected.llm.thinking_state})"
            )
            self.canvas.create_text(10, 50, anchor="nw", fill="#F8D66D", text=info, font=("Consolas", 10))

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
            self.details_canvas = None
            self.details_list_frame = None
            self._detail_rows.clear()
            self._detail_cards.clear()
            self._detail_llm_labels.clear()
            self._detail_status_labels.clear()
            self._detail_llm_prompt_boxes.clear()
            self._detail_llm_response_boxes.clear()
            return

        if self.details_window is None or not self.details_window.winfo_exists():
            self._create_details_window()

        if self.details_list_frame is None or self.details_canvas is None:
            return

        active_ids: set[int] = set()
        for row, agent in enumerate(sorted(self.world.state.agents, key=lambda a: a.entity_id)):
            active_ids.add(agent.entity_id)
            var = self._detail_rows.get(agent.entity_id)
            if var is None:
                var = tk.BooleanVar(value=agent.llm.enabled)
                self._detail_rows[agent.entity_id] = var
            else:
                var.set(agent.llm.enabled)

            card = self._detail_cards.get(agent.entity_id)
            if card is None or not card.winfo_exists():
                card = tk.LabelFrame(
                    self.details_list_frame,
                    text=f"Agent #{agent.entity_id}",
                    bg="#111621",
                    fg="#DCE6F7",
                    padx=6,
                    pady=6,
                    labelanchor="nw",
                )
                card.columnconfigure(0, weight=1)

                ttk.Checkbutton(
                    card,
                    text="LLM aan voor agent",
                    variable=var,
                    command=lambda aid=agent.entity_id, v=var: self.world.set_agent_llm_enabled(aid, v.get()),
                ).grid(row=0, column=0, sticky="w", pady=(0, 4))

                llm_label = tk.Label(card, bg="#111621", fg="#9FD0FF", anchor="w", justify="left")
                llm_label.grid(row=1, column=0, sticky="ew", pady=(0, 4))
                self._detail_llm_labels[agent.entity_id] = llm_label

                status_label = tk.Label(card, bg="#111621", fg="#E4EAF3", anchor="w", justify="left")
                status_label.grid(row=2, column=0, sticky="ew", pady=(0, 4))
                self._detail_status_labels[agent.entity_id] = status_label

                llm_box = tk.LabelFrame(
                    card,
                    text="LLM prompt/response",
                    bg="#101725",
                    fg="#DCE6F7",
                    padx=6,
                    pady=6,
                )
                llm_box.grid(row=3, column=0, sticky="ew")
                llm_box.columnconfigure(0, weight=1)

                tk.Label(llm_box, text="Prompt", bg="#101725", fg="#A8BEDD", anchor="w").grid(row=0, column=0, sticky="w")
                prompt_text = tk.Text(llm_box, height=4, wrap="word", bg="#0A0F19", fg="#E8EEF9", insertbackground="#E8EEF9")
                prompt_text.grid(row=1, column=0, sticky="ew", pady=(0, 4))
                prompt_text.configure(state="disabled")
                self._detail_llm_prompt_boxes[agent.entity_id] = prompt_text

                tk.Label(llm_box, text="Response", bg="#101725", fg="#A8BEDD", anchor="w").grid(row=2, column=0, sticky="w")
                response_text = tk.Text(llm_box, height=4, wrap="word", bg="#0A0F19", fg="#E8EEF9", insertbackground="#E8EEF9")
                response_text.grid(row=3, column=0, sticky="ew")
                response_text.configure(state="disabled")
                self._detail_llm_response_boxes[agent.entity_id] = response_text

                self._detail_cards[agent.entity_id] = card

            card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)

            llm_line = (
                f"llm_state={agent.llm.thinking_state}, pending={agent.llm.pending_request_id}, "
                f"last_error={agent.llm.last_error or '-'}"
            )
            self._detail_llm_labels[agent.entity_id].configure(text=llm_line)

            status_line = (
                f"intent={agent.current_intent} | hp={agent.hp:.2f} | energy={agent.emotions.energy:.2f} | "
                f"stress={agent.emotions.stress:.2f} | fear={agent.emotions.fear:.2f} | aggr={agent.emotions.aggression:.2f}"
            )
            self._detail_status_labels[agent.entity_id].configure(text=status_line)
            self._set_text_widget(self._detail_llm_prompt_boxes[agent.entity_id], agent.llm.last_prompt)
            self._set_text_widget(self._detail_llm_response_boxes[agent.entity_id], agent.llm.last_raw_response)

        stale_ids = [aid for aid in self._detail_cards if aid not in active_ids]
        for agent_id in stale_ids:
            self._detail_cards[agent_id].destroy()
            self._detail_cards.pop(agent_id, None)
            self._detail_rows.pop(agent_id, None)
            self._detail_llm_labels.pop(agent_id, None)
            self._detail_status_labels.pop(agent_id, None)
            self._detail_llm_prompt_boxes.pop(agent_id, None)
            self._detail_llm_response_boxes.pop(agent_id, None)

        self.details_canvas.update_idletasks()
        self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all"))

    def _set_text_widget(self, widget: tk.Text, value: str) -> None:
        next_text = value.strip() if value.strip() else "-"
        current_text = widget.get("1.0", "end-1c")
        if current_text == next_text:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", next_text)
        widget.configure(state="disabled")

    def _create_details_window(self) -> None:
        self.details_window = tk.Toplevel(self.root)
        self.details_window.title("Agent inspectie")
        self.details_window.geometry("700x720")

        container = tk.Frame(self.details_window, bg="#0E1118")
        container.pack(fill="both", expand=True)

        self.details_canvas = tk.Canvas(container, bg="#0E1118", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.details_canvas.yview)
        self.details_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.details_canvas.pack(side="left", fill="both", expand=True)

        self.details_list_frame = tk.Frame(self.details_canvas, bg="#0E1118")
        self.details_canvas.create_window((0, 0), window=self.details_list_frame, anchor="nw")

        self.details_list_frame.bind(
            "<Configure>",
            lambda _e: self.details_canvas.configure(scrollregion=self.details_canvas.bbox("all")),
        )

    def _toggle_global_llm(self) -> None:
        self.world.set_global_llm_enabled(self.global_llm_enabled.get())

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
        self.world.set_global_llm_enabled(self.global_llm_enabled.get())
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
        self.world.set_agent_llm_enabled(agent.entity_id, self.global_llm_enabled.get())
        self.selected_agent_id = agent.entity_id

    def middle_click(self, event) -> None:
        click_pos = self._screen_to_world(event.x, event.y)
        for agent in self.world.state.agents:
            if (agent.position - click_pos).length() <= 10:
                self.selected_agent_id = agent.entity_id
                return
        self.selected_agent_id = None
