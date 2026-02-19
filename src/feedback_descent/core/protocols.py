from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from feedback_descent.core.types import Candidate, Evaluation, FeedbackEntry


@runtime_checkable
class Proposer(Protocol):
    async def propose(
        self,
        champion: Candidate | None,
        feedback_history: list[FeedbackEntry],
        iteration: int,
    ) -> Candidate: ...


@runtime_checkable
class Evaluator(Protocol):
    async def evaluate(self, challenger: Candidate, champion: Candidate) -> Evaluation: ...


@runtime_checkable
class ArtifactRenderer(Protocol):
    artifact_media_type: str  # e.g. "image/png"
    artifact_extension: str  # e.g. "png"

    async def render_artifact(self, candidate: Candidate) -> bytes | None: ...
