from __future__ import annotations

import json
import logging
import re

from feedback_descent.core.types import Candidate, Evaluation, RunConfig
from feedback_descent.domains.svg.prompts import build_evaluation_prompt
from feedback_descent.domains.svg.renderer import SVGRenderer
from feedback_descent.llm.client import ImageInput, LLMClient

logger = logging.getLogger(__name__)


class SVGEvaluator:
    def __init__(self, llm: LLMClient, renderer: SVGRenderer, config: RunConfig) -> None:
        self.llm = llm
        self.renderer = renderer
        self.config = config

    async def evaluate(self, challenger: Candidate, champion: Candidate) -> Evaluation:
        render_width = self.config.domain_config.get("render_width", 512)
        render_height = self.config.domain_config.get("render_height", 512)

        challenger_png = await self.renderer.render(
            challenger.content, render_width, render_height
        )
        champion_png = await self.renderer.render(
            champion.content, render_width, render_height
        )

        if self.config.order_bias_mitigation:
            return await self._evaluate_with_bias_mitigation(
                challenger, champion, challenger_png, champion_png
            )
        else:
            return await self._single_comparison(
                challenger, champion, challenger_png, champion_png
            )

    async def _single_comparison(
        self,
        challenger: Candidate,
        champion: Candidate,
        challenger_png: bytes,
        champion_png: bytes,
        challenger_is_a: bool = True,
    ) -> Evaluation:
        system, user = build_evaluation_prompt(self.config.rubric_text, self.config.subject)

        if challenger_is_a:
            images = [
                ImageInput(data=challenger_png, media_type="image/png"),
                ImageInput(data=champion_png, media_type="image/png"),
            ]
            order_label = "A=challenger, B=champion"
        else:
            images = [
                ImageInput(data=champion_png, media_type="image/png"),
                ImageInput(data=challenger_png, media_type="image/png"),
            ]
            order_label = "A=champion, B=challenger"

        logger.debug(
            "=== EVALUATION (challenger iter %d vs champion iter %d, %s) ===",
            challenger.iteration, champion.iteration, order_label,
        )
        logger.debug("SYSTEM PROMPT:\n%s", system)
        logger.debug("USER PROMPT:\n%s", user)
        logger.debug(
            "IMAGES: Image A (%d bytes), Image B (%d bytes)",
            len(images[0].data), len(images[1].data),
        )

        response = await self.llm.evaluate_with_images(system, user, images)
        logger.debug("RESPONSE:\n%s", response)
        winner, rationale, feedback = _parse_judge_response(response)

        # Map winner back to challenger preference
        if challenger_is_a:
            preferred = winner == "A"
        else:
            preferred = winner == "B"

        return Evaluation(
            preferred=preferred,
            rationale=rationale,
            feedback=feedback,
            challenger=challenger,
            champion=champion,
            raw_response=response,
        )

    async def _evaluate_with_bias_mitigation(
        self,
        challenger: Candidate,
        champion: Candidate,
        challenger_png: bytes,
        champion_png: bytes,
    ) -> Evaluation:
        max_retries = 3

        for _ in range(max_retries):
            # Run A-B (challenger=A) and B-A (challenger=B) comparisons
            eval_ab = await self._single_comparison(
                challenger, champion, challenger_png, champion_png, challenger_is_a=True
            )
            eval_ba = await self._single_comparison(
                challenger, champion, challenger_png, champion_png, challenger_is_a=False
            )

            # Check consistency
            if eval_ab.preferred == eval_ba.preferred:
                combined_rationale = (
                    f"[A-B ordering]: {eval_ab.rationale}\n"
                    f"[B-A ordering]: {eval_ba.rationale}"
                )
                # Use feedback from the first ordering
                return Evaluation(
                    preferred=eval_ab.preferred,
                    rationale=combined_rationale,
                    feedback=eval_ab.feedback,
                    challenger=challenger,
                    champion=champion,
                    raw_response=f"AB: {eval_ab.raw_response}\nBA: {eval_ba.raw_response}",
                )

        raise ValueError(
            "Order bias mitigation: inconsistent results across orderings after 3 attempts"
        )


def _parse_judge_response(response: str) -> tuple[str, str, str]:
    """Parse judge response to extract winner (A/B), rationale, and feedback.

    Tries JSON parsing first, falls back to regex.
    """
    # Try JSON parsing
    try:
        json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            winner = data["winner"].upper().strip()
            rationale = data.get("rationale", "")
            feedback = data.get("feedback", rationale)
            if winner in ("A", "B"):
                return winner, rationale, feedback
    except (json.JSONDecodeError, KeyError, AttributeError):
        pass

    # Regex fallback
    winner_match = re.search(r'"winner"\s*:\s*"([AB])"', response, re.IGNORECASE)
    rationale_match = re.search(r'"rationale"\s*:\s*"(.*?)"', response, re.DOTALL)
    feedback_match = re.search(r'"feedback"\s*:\s*"(.*?)"', response, re.DOTALL)

    if winner_match:
        winner = winner_match.group(1).upper()
        rationale = rationale_match.group(1) if rationale_match else ""
        feedback = feedback_match.group(1) if feedback_match else rationale
        return winner, rationale, feedback

    raise ValueError(f"Could not parse judge response: {response[:200]}")
