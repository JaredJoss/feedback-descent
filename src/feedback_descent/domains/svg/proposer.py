from __future__ import annotations

import logging

from feedback_descent.core.types import Candidate, FeedbackEntry, RunConfig
from feedback_descent.domains.svg.parser import extract_svg
from feedback_descent.domains.svg.prompts import build_proposal_prompt
from feedback_descent.llm.client import LLMClient

logger = logging.getLogger(__name__)


class SVGProposer:
    def __init__(self, llm: LLMClient, config: RunConfig) -> None:
        self.llm = llm
        self.config = config

    async def propose(
        self,
        champion: Candidate | None,
        feedback_history: list[FeedbackEntry],
        iteration: int,
    ) -> Candidate:
        system, user = build_proposal_prompt(
            subject=self.config.subject,
            subject_description=self.config.domain_config["description"],
            rubric=self.config.rubric_text,
            champion_svg=champion.content if champion else None,
            feedback_history=feedback_history,
            iteration=iteration,
            informed_init=self.config.informed_init,
        )

        logger.debug("=== PROPOSAL (iteration %d) ===", iteration)
        logger.debug("SYSTEM PROMPT:\n%s", system)
        logger.debug("USER PROMPT:\n%s", user)

        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(max_retries):
            response = await self.llm.generate(system, user, temperature=0.7)
            logger.debug("RESPONSE (attempt %d):\n%s", attempt, response)
            try:
                svg_code = extract_svg(response)
                return Candidate(
                    content=svg_code,
                    iteration=iteration,
                    metadata={"attempt": attempt, "raw_response_length": len(response)},
                )
            except ValueError as e:
                last_error = e

        raise ValueError(
            f"Failed to extract SVG after {max_retries} attempts: {last_error}"
        )
