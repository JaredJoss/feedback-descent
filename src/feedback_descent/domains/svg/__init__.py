from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from feedback_descent.domains.base import DomainComponents, DomainPlugin
from feedback_descent.domains.svg.evaluator import SVGEvaluator
from feedback_descent.domains.svg.proposer import SVGProposer
from feedback_descent.domains.svg.renderer import create_renderer

if TYPE_CHECKING:
    from feedback_descent.core.types import RunConfig
    from feedback_descent.llm.client import LLMClient

CONFIGS_DIR = Path(__file__).parent.parent.parent.parent.parent / "configs" / "svg"


class SVGArtifactRenderer:
    artifact_media_type = "image/png"
    artifact_extension = "png"

    def __init__(self, renderer, width: int, height: int) -> None:
        self._renderer = renderer
        self._width = width
        self._height = height

    async def render_artifact(self, candidate) -> bytes | None:
        return await self._renderer.render(candidate.content, self._width, self._height)


class SVGDomain(DomainPlugin):
    name = "svg"
    description = "SVG artwork optimization via LLM-generated markup and rendered image comparison"

    def create_components(
        self,
        config: RunConfig,
        proposer_llm: LLMClient,
        evaluator_llm: LLMClient,
    ) -> DomainComponents:
        renderer_name = config.domain_config.get("renderer", "resvg")
        render_width = config.domain_config.get("render_width", 512)
        render_height = config.domain_config.get("render_height", 512)

        svg_renderer = create_renderer(renderer_name)
        proposer = SVGProposer(proposer_llm, config)
        evaluator = SVGEvaluator(evaluator_llm, svg_renderer, config)
        artifact_renderer = SVGArtifactRenderer(svg_renderer, render_width, render_height)

        return DomainComponents(
            proposer=proposer,
            evaluator=evaluator,
            artifact_renderer=artifact_renderer,
        )

    def list_configs(self, config_type: str) -> list[str]:
        config_dir = CONFIGS_DIR / config_type
        if not config_dir.exists():
            return []
        return sorted(p.stem for p in config_dir.glob("*.yaml"))

    def load_config(self, config_type: str, name: str) -> dict:
        path = CONFIGS_DIR / config_type / f"{name}.yaml"
        if not path.exists():
            available = self.list_configs(config_type)
            raise FileNotFoundError(
                f"{config_type[:-1].title()} {name!r} not found. Available: {available}"
            )
        return yaml.safe_load(path.read_text())
