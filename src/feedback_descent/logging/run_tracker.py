from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from feedback_descent.core.types import Candidate, Evaluation, RunConfig

if TYPE_CHECKING:
    from feedback_descent.core.protocols import ArtifactRenderer


class RunTracker:
    def __init__(
        self, config: RunConfig, artifact_renderer: ArtifactRenderer | None = None
    ) -> None:
        self.config = config
        self.artifact_renderer = artifact_renderer

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = config.output_dir / f"run_{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        subdirs = ["candidates", "evaluations", "champions", "final"]
        if artifact_renderer is not None:
            subdirs.append("renders")
        for subdir in subdirs:
            (self.run_dir / subdir).mkdir(exist_ok=True)

        # Save config
        config_dict = {
            "subject": config.subject,
            "domain": config.domain,
            "domain_config": config.domain_config,
            "rubric_text": config.rubric_text,
            "max_iterations": config.max_iterations,
            "order_bias_mitigation": config.order_bias_mitigation,
            "proposer_model": config.proposer_model,
            "evaluator_model": config.evaluator_model,
        }
        (self.run_dir / "config.json").write_text(json.dumps(config_dict, indent=2))

        self.champion_iterations: list[int] = []
        self.feedback_log: list[dict] = []

    async def _render_and_save(self, candidate: Candidate, path: Path) -> None:
        if self.artifact_renderer is not None:
            data = await self.artifact_renderer.render_artifact(candidate)
            if data is not None:
                path.write_bytes(data)

    async def save_candidate(self, candidate: Candidate, iteration: int) -> None:
        txt_path = self.run_dir / "candidates" / f"iter_{iteration:03d}_challenger.txt"
        txt_path.write_text(candidate.content)

        if self.artifact_renderer is not None:
            ext = self.artifact_renderer.artifact_extension
            render_path = (
                self.run_dir / "renders" / f"iter_{iteration:03d}_challenger.{ext}"
            )
            await self._render_and_save(candidate, render_path)

    async def save_champion(self, champion: Candidate, iteration: int) -> None:
        txt_path = self.run_dir / "champions" / f"champion_iter_{iteration:03d}.txt"
        txt_path.write_text(champion.content)

        if self.artifact_renderer is not None:
            ext = self.artifact_renderer.artifact_extension
            render_path = (
                self.run_dir / "champions" / f"champion_iter_{iteration:03d}.{ext}"
            )
            await self._render_and_save(champion, render_path)

            # Also save render to renders dir
            render_copy = (
                self.run_dir / "renders" / f"iter_{iteration:03d}_champion.{ext}"
            )
            await self._render_and_save(champion, render_copy)

        self.champion_iterations.append(iteration)

    async def save_evaluation(self, evaluation: Evaluation, iteration: int) -> None:
        eval_data = {
            "iteration": iteration,
            "preferred": evaluation.preferred,
            "rationale": evaluation.rationale,
            "feedback": evaluation.feedback,
            "challenger_iteration": evaluation.challenger.iteration,
            "champion_iteration": evaluation.champion.iteration,
            "raw_response": evaluation.raw_response,
        }
        eval_path = self.run_dir / "evaluations" / f"iter_{iteration:03d}.json"
        eval_path.write_text(json.dumps(eval_data, indent=2))

        self.feedback_log.append({
            "iteration": iteration,
            "outcome": "challenger_wins" if evaluation.preferred else "champion_retained",
            "rationale": evaluation.rationale,
            "feedback": evaluation.feedback,
            "champion_iteration": evaluation.champion.iteration,
            "challenger_iteration": evaluation.challenger.iteration,
        })

    def save_discarded(self, iteration: int, reason: str, phase: str) -> None:
        self.feedback_log.append({
            "iteration": iteration,
            "outcome": "discarded",
            "reason": reason,
            "phase": phase,
        })

    async def save_final(self, champion: Candidate) -> None:
        (self.run_dir / "final" / "final.txt").write_text(champion.content)

        if self.artifact_renderer is not None:
            ext = self.artifact_renderer.artifact_extension
            final_render = self.run_dir / "final" / f"final.{ext}"
            await self._render_and_save(champion, final_render)

        summary = {
            "total_iterations": self.config.max_iterations,
            "champion_updates": len(self.champion_iterations),
            "champion_update_iterations": self.champion_iterations,
            "final_champion_iteration": self.champion_iterations[-1]
            if self.champion_iterations
            else 0,
            "feedback_log": self.feedback_log,
        }
        (self.run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
