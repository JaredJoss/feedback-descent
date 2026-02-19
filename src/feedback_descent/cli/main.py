from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from feedback_descent.config.loader import build_run_config
from feedback_descent.core.loop import feedback_descent
from feedback_descent.domains import get_domain, list_domains
from feedback_descent.llm.client import LLMClient
from feedback_descent.logging.run_tracker import RunTracker
from feedback_descent.logging.trajectory import generate_trajectory_html

console = Console()


@click.group()
def cli() -> None:
    """Feedback Descent: Open-ended optimization via pairwise comparison."""
    load_dotenv()


@cli.command("run")
@click.option("--domain", required=True, help="Domain name (e.g. svg)")
@click.option("--subject", required=True, help="Subject name (e.g. unicorn)")
@click.option("--rubric", required=True, help="Rubric name (e.g. anatomical_realism)")
@click.option("--iterations", default=20, help="Max iterations")
@click.option(
    "--proposer-model",
    default="anthropic/claude-sonnet-4-20250514",
    help="LiteLLM model string for proposer",
)
@click.option(
    "--evaluator-model",
    default="anthropic/claude-sonnet-4-20250514",
    help="LiteLLM model string for evaluator",
)
@click.option("--renderer", default=None, help="SVG renderer (resvg or playwright)")
@click.option("--render-width", default=None, type=int, help="Render width in pixels")
@click.option("--render-height", default=None, type=int, help="Render height in pixels")
@click.option("--order-bias/--no-order-bias", default=True, help="Order bias mitigation")
@click.option("--scratch/--informed", default=False,
              help="Seed mode: --scratch omits rubric from initial generation, --informed (default) includes it")
@click.option("--output-dir", default="./runs", help="Output directory for runs")
@click.option("--verbose", "-v", is_flag=True, help="Log full prompts and responses to debug.log in run dir")
def run_cmd(
    domain: str,
    subject: str,
    rubric: str,
    iterations: int,
    proposer_model: str,
    evaluator_model: str,
    renderer: str | None,
    render_width: int | None,
    render_height: int | None,
    order_bias: bool,
    scratch: bool,
    output_dir: str,
    verbose: bool,
) -> None:
    """Run feedback descent optimization."""
    # Build domain_kwargs from optional flags
    domain_kwargs: dict = {}
    if renderer is not None:
        domain_kwargs["renderer"] = renderer
    if render_width is not None:
        domain_kwargs["render_width"] = render_width
    if render_height is not None:
        domain_kwargs["render_height"] = render_height

    config = build_run_config(
        domain_name=domain,
        subject_name=subject,
        rubric_name=rubric,
        iterations=iterations,
        proposer_model=proposer_model,
        evaluator_model=evaluator_model,
        order_bias=order_bias,
        informed_init=not scratch,
        output_dir=output_dir,
        domain_kwargs=domain_kwargs,
    )

    console.print(f"[bold]Domain:[/bold] {domain}")
    console.print(f"[bold]Subject:[/bold] {config.subject}")
    console.print(f"[bold]Rubric:[/bold] {rubric}")
    console.print(f"[bold]Iterations:[/bold] {config.max_iterations}")
    console.print(f"[bold]Proposer:[/bold] {config.proposer_model}")
    console.print(f"[bold]Evaluator:[/bold] {config.evaluator_model}")
    console.print(f"[bold]Order bias mitigation:[/bold] {config.order_bias_mitigation}")
    console.print(f"[bold]Seed mode:[/bold] {'informed' if config.informed_init else 'scratch'}")

    domain_plugin = get_domain(domain)
    proposer_llm = LLMClient(config.proposer_model)
    evaluator_llm = LLMClient(config.evaluator_model)

    components = domain_plugin.create_components(config, proposer_llm, evaluator_llm)
    tracker = RunTracker(config, components.artifact_renderer)

    if verbose:
        log_path = tracker.run_dir / "debug.log"
        fd_logger = logging.getLogger("feedback_descent")
        fd_logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s]\n%(message)s\n"))
        fd_logger.addHandler(fh)

    console.print(f"\n[dim]Run directory: {tracker.run_dir}[/dim]")

    asyncio.run(
        feedback_descent(components.proposer, components.evaluator, config, tracker)
    )

    # Generate trajectory visualization
    trajectory_path = generate_trajectory_html(tracker.run_dir)
    console.print(f"\n[bold]Trajectory:[/bold] {trajectory_path}")
    if verbose:
        console.print(f"[bold]Debug log:[/bold] {log_path}")


@cli.command("list-domains")
def list_domains_cmd() -> None:
    """List available domains."""
    table = Table(title="Available Domains")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name in list_domains():
        plugin = get_domain(name)
        table.add_row(name, plugin.description)

    console.print(table)


@cli.command("list-subjects")
@click.option("--domain", required=True, help="Domain name (e.g. svg)")
def list_subjects_cmd(domain: str) -> None:
    """List available subjects for a domain."""
    plugin = get_domain(domain)

    table = Table(title=f"Available Subjects ({domain})")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name in plugin.list_configs("subjects"):
        subject = plugin.load_config("subjects", name)
        desc = subject.get("description", "").strip()[:80]
        table.add_row(name, desc)

    console.print(table)


@cli.command("list-rubrics")
@click.option("--domain", required=True, help="Domain name (e.g. svg)")
def list_rubrics_cmd(domain: str) -> None:
    """List available rubrics for a domain."""
    plugin = get_domain(domain)

    table = Table(title=f"Available Rubrics ({domain})")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")

    for name in plugin.list_configs("rubrics"):
        rubric = plugin.load_config("rubrics", name)
        table.add_row(name, rubric.get("display_name", name))

    console.print(table)


@cli.command("trajectory")
@click.argument("run_dir", type=click.Path(exists=True, path_type=Path))
def trajectory_cmd(run_dir: Path) -> None:
    """Regenerate trajectory HTML from a completed run directory."""
    path = generate_trajectory_html(run_dir)
    console.print(f"[green]Trajectory generated:[/green] {path}")


if __name__ == "__main__":
    cli()
