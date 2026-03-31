"""
REDUCE phase: takes MAP results + WorldState → SprintReport.
Makes one LLM call (if provider is not mock) for predicted_risks/recommendations.
Falls back to heuristics when mock or LLM call fails.
"""
import json
from datetime import datetime

from wargame.exceptions import SchemaValidationError
from wargame.models.sprint_report import (
    BlockedDependency,
    FrictionHotspot,
    PredictedRisk,
    SprintReport,
)
from wargame.models.world_state import WorldState
from wargame.providers.base import BaseLLMProvider


class GodAgentReducer:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    async def reduce(
        self,
        map_results: tuple[dict, dict, dict, dict],
        world_state: WorldState,
    ) -> SprintReport:
        """
        map_results order: (friction, dependencies, tech_debt, velocity)
        """
        friction_map, deps_map, debt_map, vel_map = map_results

        # --- Build structured objects from MAP data ---
        friction_hotspots = [
            FrictionHotspot(
                agent_pair=tuple(h["agent_pair"]),
                conflict_count=h["conflict_count"],
                root_cause=h["root_cause"],
            )
            for h in friction_map.get("friction_hotspots", [])
        ]

        blocked_deps = [
            BlockedDependency(
                story_id=d["story_id"],
                blocked_by_agent=d["blocked_by_agent"],
                blocking_reason=d["blocking_reason"],
                days_blocked=d["days_blocked"],
                impact=d["impact"],
            )
            for d in deps_map.get("blocked_dependencies", [])
        ]

        tech_debt_delta = debt_map.get("tech_debt_delta", 0)
        velocity = vel_map.get("velocity", 0)
        velocity_decay_pct = vel_map.get("velocity_decay_pct", 0.0)

        # friction_index from hotspot data
        total_friction = friction_map.get("total_friction_events", 0)
        # Approximation: friction_index = capped ratio of friction events
        friction_index = min(total_friction / max(total_friction + 4, 1), 1.0)

        # --- Confidence score (data completeness, no LLM) ---
        confidence = self._calc_confidence(
            friction_map, deps_map, debt_map, vel_map, world_state
        )

        # --- Predicted risks + recommendations ---
        predicted_risks, recommendations = await self._generate_insights(
            friction_map, deps_map, debt_map, vel_map, world_state
        )

        return SprintReport(
            simulation_id=world_state.simulation_id,
            sprint=world_state.current_sprint,
            generated_at=datetime.utcnow(),
            confidence_score=round(confidence, 3),
            is_reliable=confidence >= SprintReport.reliability_threshold(),
            friction_index=round(friction_index, 4),
            friction_hotspots=friction_hotspots,
            blocked_dependencies=blocked_deps,
            tech_debt_delta=tech_debt_delta,
            velocity=velocity,
            velocity_decay_pct=velocity_decay_pct,
            predicted_risks=predicted_risks,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    def _calc_confidence(
        self,
        friction_map: dict,
        deps_map: dict,
        debt_map: dict,
        vel_map: dict,
        world_state: WorldState,
    ) -> float:
        score = 0.60  # base

        # More turns = more data = more confident
        turns = world_state.current_turn
        score += min(turns / 5.0, 1.0) * 0.15  # up to +0.15

        # Has friction signal
        if friction_map.get("total_friction_events", 0) > 0:
            score += 0.10

        # Has blocking data
        if deps_map.get("total_blocked", 0) > 0:
            score += 0.05

        # Has velocity data (someone completed stories)
        if vel_map.get("total_completed", 0) > 0:
            score += 0.10

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Insight generation (LLM or heuristic)
    # ------------------------------------------------------------------

    async def _generate_insights(
        self,
        friction_map: dict,
        deps_map: dict,
        debt_map: dict,
        vel_map: dict,
        world_state: WorldState,
    ) -> tuple[list[PredictedRisk], list[str]]:
        if self.provider.provider_name != "mock":
            try:
                return await self._llm_insights(
                    friction_map, deps_map, debt_map, vel_map, world_state
                )
            except Exception:
                pass  # fall through to heuristics

        return self._heuristic_insights(friction_map, deps_map, debt_map, vel_map)

    async def _llm_insights(
        self,
        friction_map: dict,
        deps_map: dict,
        debt_map: dict,
        vel_map: dict,
        world_state: WorldState,
    ) -> tuple[list[PredictedRisk], list[str]]:
        system_prompt = (
            "You are the God Agent — a read-only simulation observer.\n"
            "Analyze the sprint data below and return a valid JSON with keys:\n"
            '  "predicted_risks": [{"id": "R-01", "severity": "HIGH", '
            '"sprint_impact": 2, "description": "...", "recommendation": "..."}],\n'
            '  "recommendations": ["...", "..."]\n'
            "Be concise. Max 3 risks. Max 5 recommendations."
        )
        map_summary = {
            "sprint": world_state.current_sprint,
            "total_sprints": world_state.total_sprints,
            "friction_hotspots": friction_map.get("friction_hotspots", []),
            "blocked_stories": [d["story_id"] for d in deps_map.get("blocked_dependencies", [])],
            "tech_debt_delta": debt_map.get("tech_debt_delta", 0),
            "velocity": vel_map.get("velocity", 0),
            "velocity_decay_pct": vel_map.get("velocity_decay_pct", 0),
        }
        user_prompt = f"Sprint MAP data:\n{json.dumps(map_summary, indent=2)}"

        response = await self.provider.complete(system_prompt, user_prompt)
        # provider returns AgentResponse; we need to re-parse for insights
        # Try extracting from rationale field if it's JSON
        raw = response.rationale
        try:
            data = json.loads(raw)
            risks = [PredictedRisk(**r) for r in data.get("predicted_risks", [])]
            recs = data.get("recommendations", [])
            return risks, recs
        except Exception:
            raise SchemaValidationError("LLM did not return valid insights JSON")

    def _heuristic_insights(
        self,
        friction_map: dict,
        deps_map: dict,
        debt_map: dict,
        vel_map: dict,
    ) -> tuple[list[PredictedRisk], list[str]]:
        risks: list[PredictedRisk] = []
        recs: list[str] = []
        risk_id = 1

        hotspots = friction_map.get("friction_hotspots", [])
        blocked = deps_map.get("blocked_dependencies", [])
        debt = debt_map.get("tech_debt_delta", 0)
        decay = vel_map.get("velocity_decay_pct", 0.0)
        total_completed = vel_map.get("total_completed", 0)

        if hotspots:
            top = max(hotspots, key=lambda h: h["conflict_count"])
            pair_str = " vs ".join(top["agent_pair"])
            risks.append(PredictedRisk(
                id=f"R-{risk_id:02d}",
                severity="HIGH" if top["conflict_count"] >= 3 else "MEDIUM",
                sprint_impact=1,
                description=f"Recurring friction between {pair_str}: {top['root_cause']}",
                recommendation=f"Facilitate alignment session between {pair_str} to resolve chronic conflict.",
            ))
            risk_id += 1
            recs.append(
                f"Schedule conflict resolution between {pair_str} — {top['conflict_count']} friction events recorded."
            )

        if blocked:
            blockers = {d["blocked_by_agent"] for d in blocked}
            risks.append(PredictedRisk(
                id=f"R-{risk_id:02d}",
                severity="HIGH" if len(blocked) >= 3 else "MEDIUM",
                sprint_impact=1,
                description=f"{len(blocked)} story/stories blocked by: {', '.join(blockers)}",
                recommendation="Prioritize unblocking sessions; assign dedicated review time for blocking agents.",
            ))
            risk_id += 1
            recs.append(
                f"Unblock {len(blocked)} dependent stories — blocker(s): {', '.join(blockers)}."
            )

        if debt > 10:
            risks.append(PredictedRisk(
                id=f"R-{risk_id:02d}",
                severity="HIGH" if debt > 20 else "MEDIUM",
                sprint_impact=2,
                description=f"Tech debt accumulating: +{debt} points this sprint",
                recommendation="Allocate at least 20% of next sprint capacity to debt reduction tasks.",
            ))
            risk_id += 1
            recs.append(f"Schedule debt-reduction sprint — {debt} pts added this sprint.")

        if decay < -20:
            risks.append(PredictedRisk(
                id=f"R-{risk_id:02d}",
                severity="MEDIUM",
                sprint_impact=1,
                description=f"Velocity decay: {decay:+.1f}% vs previous sprint",
                recommendation="Investigate blockers and friction sources causing velocity drop.",
            ))
            risk_id += 1
            recs.append(f"Velocity dropped {decay:+.1f}% — review impediments from previous sprint retrospective.")

        if total_completed == 0:
            recs.append("No stories completed this sprint — review commitment vs. capacity alignment.")

        if not recs:
            recs.append("Sprint on track. Maintain current pace and monitor friction index.")

        return risks, recs
