import json
import threading
import time
import uuid

from lessoncanvas.adapters.model import ModelProviderError, get_model_adapter
from lessoncanvas.db import SessionLocal
from lessoncanvas.models import InteractionMessage, TraceEvent
from lessoncanvas.settings import get_settings


class NarrationState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.tokens: list[str] = []
        self.complete = False
        self.stop_requested = False
        self.error: str | None = None

    def full_text(self) -> str:
        with self.lock:
            return "".join(self.tokens)


_narrations: dict[str, NarrationState] = {}
_registry_lock = threading.Lock()


def get_narration(run_id: str) -> NarrationState | None:
    with _registry_lock:
        return _narrations.get(run_id)


class NarrationQuotaError(Exception):
    pass


def _produce(run_id: str, state: NarrationState, user_payload: dict) -> None:
    started = time.monotonic()
    try:
        adapter = get_model_adapter()
        for token in adapter.stream(
            "You are a requirements discovery specialist. Narrate the next interview step.",
            json.dumps(user_payload, ensure_ascii=False),
        ):
            with state.condition:
                state.tokens.append(token)
                state.condition.notify_all()
    except ModelProviderError as error:
        with state.condition:
            state.error = str(error)
            state.complete = True
            state.condition.notify_all()
        return

    full_text = state.full_text()
    latency = int((time.monotonic() - started) * 1000)
    session = SessionLocal()
    try:
        from lessoncanvas.models import DiscoveryRun

        run = session.get(DiscoveryRun, uuid.UUID(run_id))
        if run is not None:
            run.model_calls += 1
        session.add(
            InteractionMessage(
                run_id=uuid.UUID(run_id),
                role="agent",
                content=full_text,
                round_index=run.round_count if run else 0,
            )
        )
        session.add(
            TraceEvent(
                run_id=uuid.UUID(run_id),
                event_type="model.narration",
                payload_json=json.dumps(
                    {"prompt": user_payload, "response": full_text}, ensure_ascii=False
                ),
                latency_ms=latency,
                cost_usd=0.0,
            )
        )
        session.commit()
    finally:
        session.close()
    with state.condition:
        state.complete = True
        state.condition.notify_all()


def start_narration(run_id: str, narration_text: str) -> NarrationState:
    session = SessionLocal()
    try:
        from lessoncanvas.models import DiscoveryRun

        run = session.get(DiscoveryRun, uuid.UUID(run_id))
        if run is None:
            raise KeyError(run_id)
        if run.model_calls >= get_settings().max_model_calls_per_run:
            raise NarrationQuotaError("model call quota exhausted for this run")
    finally:
        session.close()

    state = NarrationState()
    with _registry_lock:
        _narrations[run_id] = state
    user_payload = {"kind": "narration", "narration": narration_text}
    thread = threading.Thread(target=_produce, args=(run_id, state, user_payload), daemon=True)
    thread.start()
    return state


def request_stop(run_id: str) -> bool:
    state = get_narration(run_id)
    if state is None:
        return False
    with state.condition:
        state.stop_requested = True
        state.condition.notify_all()
    return True
