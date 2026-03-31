"""
POST /simulate — launch a background simulation
GET  /simulate/{sim_id}/stream — SSE live feed
"""
import asyncio
import json
import os
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from wargame.dashboard.sim_registry import (
    SimState,
    create_sim,
    get_sim,
    is_sentinel,
    push_done,
    push_event,
)

router = APIRouter()


class SimulateRequest(BaseModel):
    provider: str = "mock"
    scenario: str = "seeds/etp"
    sprints: int = 2


@router.post("/simulate")
async def start_simulation(req: SimulateRequest):
    sim_id = str(uuid.uuid4())
    state = create_sim(
        sim_id=sim_id,
        provider=req.provider,
        scenario=req.scenario,
        total_sprints=req.sprints,
    )
    asyncio.create_task(_run_simulation(state))
    return {"sim_id": sim_id}


@router.get("/simulate/{sim_id}/stream")
async def stream_simulation(sim_id: str):
    state = get_sim(sim_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return EventSourceResponse(_event_generator(state))


# ---------------------------------------------------------------------------
# Background simulation task
# ---------------------------------------------------------------------------

async def _run_simulation(state: SimState) -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()

        from wargame.core.orchestrator import Orchestrator
        from wargame.providers.factory import build_provider

        state.status = "running"
        provider = build_provider(state.provider)
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./output/wargame.db")

        orchestrator = Orchestrator(
            provider=provider,
            scenario_path=state.scenario,
            total_sprints=state.total_sprints,
            db_url=db_url,
        )

        def on_turn_complete(sprint: int, turn: int, responses) -> None:
            state.current_sprint = sprint
            push_event(state, "turn", {
                "sprint": sprint,
                "turn": turn,
                "total_sprints": state.total_sprints,
                "responses": [
                    {
                        "agent_id": r.agent_id,
                        "action": r.action.value,
                        "rationale": r.rationale,
                        "confidence": r.confidence,
                        "tech_debt_added": r.tech_debt_added,
                    }
                    for r in responses
                ],
            })

        def on_sprint_complete(report) -> None:
            report_dict = json.loads(report.model_dump_json())
            state.reports.append(report_dict)
            push_event(state, "sprint_complete", report_dict)

        await orchestrator.run(
            on_turn_complete=on_turn_complete,
            on_sprint_complete=on_sprint_complete,
        )

        state.status = "done"
        push_event(state, "simulation_complete", {
            "sim_id": state.sim_id,
            "total_sprints": state.total_sprints,
        })

    except Exception as exc:
        state.status = "error"
        push_event(state, "error", {"message": str(exc)})

    finally:
        push_done(state)


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------

async def _event_generator(state: SimState):
    while True:
        try:
            item = await asyncio.wait_for(state.queue.get(), timeout=25.0)
        except asyncio.TimeoutError:
            yield {"event": "heartbeat", "data": "{}"}
            continue

        if is_sentinel(item):
            break

        yield {"event": item["event"], "data": json.dumps(item["data"])}
