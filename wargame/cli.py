import asyncio
import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from wargame.models.agent_response import ActionType

console = Console()

ACTION_STYLES: dict[ActionType, str] = {
    ActionType.VETO:         "[red]VETO[/red]",
    ActionType.FLAG:         "[yellow]FLAG[/yellow]",
    ActionType.IMPEDIMENT:   "[magenta]IMPEDIMENT[/magenta]",
    ActionType.BLOCK_DONE:   "[red]BLOCK_DONE[/red]",
    ActionType.COMPLETE:     "[green]COMPLETE[/green]",
    ActionType.REPRIORITIZE: "[blue]REPRIORITIZE[/blue]",
    ActionType.ESCALATE:     "[yellow]ESCALATE[/yellow]",
    ActionType.APPROVE:      "[cyan]APPROVE[/cyan]",
    ActionType.IDLE:         "[dim]IDLE[/dim]",
}


@click.group()
def main():
    """Agile Wargame Simulator — predict project friction before it happens."""
    pass


@main.command()
@click.option("--scenario", required=True, help="Path to scenario directory (e.g. seeds/etp/)")
@click.option("--provider", default="mock", show_default=True,
              type=click.Choice(["mock", "gemini-free", "deepseek", "openai"]),
              help="LLM provider to use.")
@click.option("--model", default=None, help="Override model within the provider.")
@click.option("--sprints", default=None, type=int, help="Number of sprints to simulate.")
@click.option("--serve", is_flag=True, default=False, help="Also start web dashboard.")
def run(scenario: str, provider: str, model: str | None, sprints: int | None, serve: bool):
    """Run a wargame simulation."""
    asyncio.run(_run_simulation(scenario, provider, model, sprints, serve))


async def _run_simulation(
    scenario: str,
    provider_name: str,
    model: str | None,
    sprints: int | None,
    serve: bool,
) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    if serve:
        import threading
        import time
        import webbrowser
        import uvicorn
        from wargame.dashboard.app import app as dashboard_app

        def _start_server():
            uvicorn.run(dashboard_app, host="0.0.0.0", port=8000, log_level="warning")

        t = threading.Thread(target=_start_server, daemon=True)
        t.start()
        time.sleep(1.0)  # allow server to bind
        webbrowser.open("http://localhost:8000")
        console.print("[dim]Dashboard: http://localhost:8000[/dim]")

    from wargame.core.orchestrator import Orchestrator
    from wargame.providers.factory import build_provider

    console.print("[bold green]Agile Wargame Simulator[/bold green] v0.1.0")
    console.print(f"Provider: [cyan]{provider_name}[/cyan] | Scenario: [cyan]{scenario}[/cyan]")

    provider = build_provider(provider_name, model)
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./output/wargame.db")
    total_sprints = sprints if sprints is not None else int(os.environ.get("DEFAULT_SPRINTS", "8"))

    orchestrator = Orchestrator(
        provider=provider,
        scenario_path=scenario,
        total_sprints=total_sprints,
        db_url=db_url,
    )

    console.print(
        f"Loaded [bold]{len(orchestrator.state.stories)}[/bold] stories "
        f"for scenario [bold]{orchestrator.state.scenario}[/bold]"
    )
    console.print(f"Simulation ID: [dim]{orchestrator.state.simulation_id}[/dim]")

    # Per-sprint tables, built via callback
    _tables: dict[int, Table] = {}

    def on_turn_complete(sprint: int, turn: int, responses) -> None:
        if sprint not in _tables:
            t = Table(title=f"Sprint {sprint} — Agent Decisions", show_lines=True)
            t.add_column("Turn", style="dim", width=4)
            t.add_column("Agent", style="bold", width=18)
            t.add_column("Action", width=14)
            t.add_column("Conf", justify="right", width=5)
            t.add_column("Rationale")
            _tables[sprint] = t

        table = _tables[sprint]
        for r in responses:
            styled_action = ACTION_STYLES.get(r.action, r.action.value)
            rationale = r.rationale[:80] + "…" if len(r.rationale) > 80 else r.rationale
            table.add_row(str(turn), r.agent_id, styled_action, f"{r.confidence:.2f}", rationale)

    # Sprint-level progress display
    current_sprint_shown = [0]

    def on_turn_complete_with_header(sprint: int, turn: int, responses) -> None:
        if sprint != current_sprint_shown[0]:
            console.rule(f"[bold blue]Sprint {sprint} / {total_sprints}[/bold blue]")
            current_sprint_shown[0] = sprint
        on_turn_complete(sprint, turn, responses)

    reports = await orchestrator.run(on_turn_complete=on_turn_complete_with_header)

    # Print all tables
    for sprint_num, table in sorted(_tables.items()):
        console.print(table)
        report = reports[sprint_num - 1]
        report_path = Path("output") / f"sprint_{sprint_num:02d}.json"
        console.print(
            f"  Sprint report: [dim]{report_path}[/dim] "
            f"(confidence={report.confidence_score:.2f}, reliable={report.is_reliable})"
        )

    console.print(f"\n[bold green]Simulation complete![/bold green]")
    console.print(f"Database: [dim]{db_url}[/dim]")
    console.print(f"Reports:  [dim]output/sprint_XX.json[/dim]")


@main.command()
@click.option("--port", default=8000, show_default=True)
def serve(port: int):
    """Start the web dashboard."""
    import uvicorn
    from wargame.dashboard.app import app
    uvicorn.run(app, host="0.0.0.0", port=port)


@main.command()
def scenarios():
    """List available scenarios."""
    seeds = Path("seeds")
    if not seeds.exists():
        console.print("[yellow]No seeds/ directory found.[/yellow]")
        return
    for d in seeds.iterdir():
        if d.is_dir() and (d / "backlog.json").exists():
            with open(d / "backlog.json") as f:
                data = json.load(f)
            console.print(
                f"[bold]{d.name}[/bold] — {data.get('scenario_name', '')} "
                f"({data.get('total_sprints', '?')} sprints)"
            )


@main.command()
@click.option("--sim-id", required=True, help="Simulation ID")
def report(sim_id: str):
    """Show available sprint reports."""
    output = Path("output")
    reports = sorted(output.glob("sprint_*.json"))
    if not reports:
        console.print("[yellow]No reports found in output/[/yellow]")
        return
    for r in reports:
        console.print(f"[dim]{r}[/dim]")
