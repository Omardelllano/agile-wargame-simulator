"""
GET /reports         — list all sprint reports on disk
GET /report/{sim_id} — in-memory reports for a running/finished simulation
GET /scenarios       — list available scenarios from seeds/
GET /health          — liveness probe
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from wargame.dashboard.sim_registry import get_sim, list_sims

router = APIRouter()

_SEEDS_DIR = Path("seeds")
_OUTPUT_DIR = Path("output")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/scenarios")
async def list_scenarios():
    if not _SEEDS_DIR.exists():
        return []
    result = []
    for d in sorted(_SEEDS_DIR.iterdir()):
        backlog = d / "backlog.json"
        if d.is_dir() and backlog.exists():
            try:
                data = json.loads(backlog.read_text(encoding="utf-8"))
                result.append({
                    "id": d.name,
                    "path": str(d).replace("\\", "/"),
                    "name": data.get("scenario_name", d.name),
                    "total_sprints": data.get("total_sprints", 8),
                    "story_count": len(data.get("stories", [])),
                })
            except Exception:
                pass
    return result


@router.get("/reports")
async def list_reports():
    """All sprint reports written to output/ on disk."""
    if not _OUTPUT_DIR.exists():
        return []
    reports = []
    for path in sorted(_OUTPUT_DIR.glob("*/sprint_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            reports.append({
                "file": path.name,
                "simulation_id": data.get("simulation_id"),
                "sprint": data.get("sprint"),
                "generated_at": data.get("generated_at"),
                "confidence_score": data.get("confidence_score"),
                "velocity": data.get("velocity"),
                "is_reliable": data.get("is_reliable"),
            })
        except Exception:
            pass
    return reports


@router.get("/report/{sim_id}")
async def get_reports(sim_id: str):
    """In-memory sprint reports accumulated during a simulation."""
    state = get_sim(sim_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {
        "sim_id": sim_id,
        "status": state.status,
        "reports": state.reports,
    }
