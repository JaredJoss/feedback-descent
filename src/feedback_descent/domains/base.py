from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from feedback_descent.core.protocols import ArtifactRenderer, Evaluator, Proposer

if TYPE_CHECKING:
    from feedback_descent.core.types import RunConfig
    from feedback_descent.llm.client import LLMClient


@dataclass
class DomainComponents:
    proposer: Proposer
    evaluator: Evaluator
    artifact_renderer: ArtifactRenderer | None = None


class DomainPlugin:
    name: str
    description: str

    def create_components(
        self,
        config: RunConfig,
        proposer_llm: LLMClient,
        evaluator_llm: LLMClient,
    ) -> DomainComponents:
        raise NotImplementedError

    def list_configs(self, config_type: str) -> list[str]:
        """List available config names for a given type (e.g. 'subjects', 'rubrics')."""
        raise NotImplementedError

    def load_config(self, config_type: str, name: str) -> dict:
        """Load a config by type and name."""
        raise NotImplementedError
