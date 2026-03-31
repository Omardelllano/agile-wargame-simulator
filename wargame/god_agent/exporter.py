import csv
import json
from pathlib import Path

from wargame.models.sprint_report import SprintReport


class ReportExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def export(self, report: SprintReport) -> tuple[Path, Path]:
        """Write sprint_{N:02d}.json and sprint_{N:02d}.csv. Returns (json_path, csv_path)."""
        json_path = self._write_json(report)
        csv_path = self._write_csv(report)
        return json_path, csv_path

    # ------------------------------------------------------------------

    def _write_json(self, report: SprintReport) -> Path:
        path = self.output_dir / f"sprint_{report.sprint:02d}.json"
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def _write_csv(self, report: SprintReport) -> Path:
        path = self.output_dir / f"sprint_{report.sprint:02d}.csv"

        # Scalar fields from SprintReport (flattened)
        base_row = {
            "simulation_id": report.simulation_id,
            "sprint": report.sprint,
            "generated_at": report.generated_at.isoformat(),
            "confidence_score": report.confidence_score,
            "is_reliable": report.is_reliable,
            "friction_index": report.friction_index,
            "tech_debt_delta": report.tech_debt_delta,
            "velocity": report.velocity,
            "velocity_decay_pct": report.velocity_decay_pct,
            "friction_hotspot_count": len(report.friction_hotspots),
            "blocked_dependency_count": len(report.blocked_dependencies),
            "recommendations": " | ".join(report.recommendations),
        }

        fieldnames = list(base_row.keys()) + [
            "risk_id", "risk_severity", "risk_sprint_impact",
            "risk_description", "risk_recommendation",
        ]

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            if report.predicted_risks:
                for risk in report.predicted_risks:
                    writer.writerow({
                        **base_row,
                        "risk_id": risk.id,
                        "risk_severity": risk.severity,
                        "risk_sprint_impact": risk.sprint_impact,
                        "risk_description": risk.description,
                        "risk_recommendation": risk.recommendation,
                    })
            else:
                # Always write at least one row
                writer.writerow({
                    **base_row,
                    "risk_id": "",
                    "risk_severity": "",
                    "risk_sprint_impact": "",
                    "risk_description": "No predicted risks this sprint.",
                    "risk_recommendation": "",
                })

        return path
