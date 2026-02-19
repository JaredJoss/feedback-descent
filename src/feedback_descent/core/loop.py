from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from feedback_descent.core.types import Candidate, FeedbackEntry, RunConfig

if TYPE_CHECKING:
    from feedback_descent.core.protocols import Evaluator, Proposer
    from feedback_descent.logging.run_tracker import RunTracker

console = Console()


async def feedback_descent(
    proposer: Proposer,
    evaluator: Evaluator,
    config: RunConfig,
    tracker: RunTracker,
) -> Candidate:
    """Algorithm: Feedback Descent.

    Iteratively improves a candidate through pairwise comparisons
    and structured textual feedback.
    """
    # Generate initial candidate (seed)
    console.print("\n[bold blue]Generating initial candidate...[/bold blue]")
    champion = await proposer.propose(
        champion=None, feedback_history=[], iteration=0
    )
    await tracker.save_champion(champion, iteration=0)
    console.print("[green]Initial candidate generated.[/green]\n")

    feedback_history: list[FeedbackEntry] = []

    for t in range(1, config.max_iterations + 1):
        console.print(f"[bold]--- Iteration {t}/{config.max_iterations} ---[/bold]")

        # Propose a challenger
        try:
            challenger = await proposer.propose(champion, feedback_history, t)
        except ValueError as e:
            console.print(f"[red]Proposal failed (skipping iteration): {e}[/red]")
            tracker.save_discarded(t, str(e), phase="proposal")
            continue

        await tracker.save_candidate(challenger, iteration=t)

        # Evaluate challenger vs champion
        try:
            evaluation = await evaluator.evaluate(challenger, champion)
        except ValueError as e:
            console.print(f"[red]Evaluation failed (skipping iteration): {e}[/red]")
            tracker.save_discarded(t, str(e), phase="evaluation")
            continue

        await tracker.save_evaluation(evaluation, iteration=t)

        # Update feedback history with actionable feedback (not comparative rationale)
        feedback_history.append(
            FeedbackEntry(candidate=challenger, feedback=evaluation.feedback, iteration=t)
        )

        if evaluation.preferred:
            # Challenger wins — update champion and reset feedback
            champion = challenger
            feedback_history = []
            await tracker.save_champion(champion, iteration=t)
            console.print(
                f"[green]★ Champion updated![/green] {evaluation.rationale[:120]}"
            )
        else:
            console.print(
                f"[yellow]Champion retained.[/yellow] {evaluation.rationale[:120]}"
            )

    await tracker.save_final(champion)
    console.print(f"\n[bold green]Optimization complete after {config.max_iterations} iterations.[/bold green]")
    return champion
