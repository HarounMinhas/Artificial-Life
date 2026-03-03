from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from .config import SimulationConfig


@dataclass
class LLMDecisionResponse:
    request_id: str
    agent_id: int
    decision: dict[str, Any] | None
    prompt: str
    raw_response: str
    error: str | None = None


class OllamaPromptBuilder:
    def build(self, payload: dict[str, Any]) -> str:
        compact_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        return (
            "Je bent een beslis-module voor een artificieel wezen.\n"
            "Geef ALLEEN een geldige JSON object terug, zonder markdown of extra tekst.\n"
            "Toegestane intent: eat, attack, flee, freeze, patrol, rest.\n"
            "Parameter-uitleg: hp=gezondheid (0 dood, hoger is robuuster; NIET aanpassen), "
            "energy=uithouding (laag maakt rust/eet logischer), stress=mentale druk (hoog verhoogt "
            "kans op vlucht/freeze), fear=ervaren dreiging (hoog stimuleert flee/vermijding), "
            "aggr/aggression=aanvalsdrang (hoog stimuleert attack).\n"
            "Gebruik exact dit schema: "
            "{\"intent\":\"...\",\"confidence\":0.0,\"ttl_ticks\":1,\"target\":{\"x\":0.0,\"y\":0.0} of null,\"stress\":0.0,\"fear\":0.0,\"aggr\":0.0,\"reason\":\"kort\"}.\n"
            "Geef altijd intent + stress + fear + aggr/aggression terug op basis van de inputstaat; hp mag niet veranderen.\n"
            "INPUT_JSON=" + compact_payload
        )


class LLMJSONParser:
    def parse(self, raw_text: str) -> dict[str, Any]:
        stripped = raw_text.strip()
        if not stripped:
            raise ValueError("Empty LLM response")

        candidates = [stripped]
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(stripped[start : end + 1])

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        raise ValueError("No valid JSON object found in LLM response")


class OllamaClient:
    def __init__(self, config: SimulationConfig, parser: LLMJSONParser):
        self.config = config
        self.parser = parser

    def request_decision(self, prompt: str) -> tuple[dict[str, Any] | None, str, str | None]:
        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.llm_temperature,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.config.ollama_base_url.rstrip('/')}/api/generate"
        req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with request.urlopen(req, timeout=self.config.llm_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            return None, "", f"ollama_http_error: {exc.code} {exc.reason}"
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                return None, "", f"ollama_timeout: {reason}"
            return None, "", f"ollama_unreachable: {reason}"
        except TimeoutError as exc:
            return None, "", f"ollama_timeout: {exc}"

        try:
            envelope = json.loads(raw)
            model_text = str(envelope.get("response", ""))
            parsed = self.parser.parse(model_text)
            return parsed, model_text, None
        except (json.JSONDecodeError, ValueError) as exc:
            return None, raw, f"invalid_json: {exc}"


class AsyncLLMDecisionBroker:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.prompt_builder = OllamaPromptBuilder()
        self.client = OllamaClient(config, parser=LLMJSONParser())
        self.executor = ThreadPoolExecutor(max_workers=max(1, config.llm_max_inflight))
        self.inflight: dict[str, tuple[int, str, Future[tuple[dict[str, Any] | None, str, str | None]]]] = {}
        self._seq = 0

    def can_submit(self) -> bool:
        return len(self.inflight) < self.config.llm_max_inflight

    def submit(self, agent_id: int, payload: dict[str, Any]) -> str | None:
        if not self.can_submit():
            return None
        request_id = f"a{agent_id}-r{self._seq}-t{int(time.time()*1000)}"
        self._seq += 1
        prompt = self.prompt_builder.build(payload)
        future = self.executor.submit(self.client.request_decision, prompt)
        self.inflight[request_id] = (agent_id, prompt, future)
        return request_id

    def collect_ready(self) -> list[LLMDecisionResponse]:
        ready: list[LLMDecisionResponse] = []
        for request_id, (agent_id, prompt, future) in list(self.inflight.items()):
            if not future.done():
                continue
            self.inflight.pop(request_id, None)
            decision: dict[str, Any] | None = None
            raw = ""
            err: str | None = None
            try:
                decision, raw, err = future.result()
            except Exception as exc:  # pragma: no cover - defensive fallback
                err = f"broker_error: {exc}"
            ready.append(
                LLMDecisionResponse(
                    request_id=request_id,
                    agent_id=agent_id,
                    decision=decision,
                    prompt=prompt,
                    raw_response=raw,
                    error=err,
                )
            )
        return ready

    def cancel_agent(self, agent_id: int) -> None:
        for request_id, (owner_id, _prompt, future) in list(self.inflight.items()):
            if owner_id != agent_id:
                continue
            future.cancel()
            self.inflight.pop(request_id, None)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
