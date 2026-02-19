from __future__ import annotations

from feedback_descent.core.types import FeedbackEntry


def build_proposal_prompt(
    subject: str,
    subject_description: str,
    rubric: str,
    champion_svg: str | None,
    feedback_history: list[FeedbackEntry],
    iteration: int,
    informed_init: bool = True,
) -> tuple[str, str]:
    """Build system and user prompts for the SVG proposer."""
    system = (
        "You are an SVG generator. You write raw SVG markup. "
        "Always output valid SVG code wrapped in <svg> tags with explicit width and height attributes."
    )

    if champion_svg is None:
        if informed_init:
            user = (
                f"Create an SVG image of: {subject}\n\n"
                f"Description: {subject_description}\n\n"
                f"Style rubric:\n{rubric}\n\n"
                "Create a detailed, high-quality SVG that follows the rubric closely. "
                "Output ONLY the SVG code, wrapped in ```svg fences."
            )
        else:
            user = (
                f"Create an SVG image of: {subject}\n\n"
                f"Description: {subject_description}\n\n"
                "Create a detailed, high-quality SVG. "
                "Output ONLY the SVG code, wrapped in ```svg fences."
            )
    else:
        user = f"Subject: {subject}\nDescription: {subject_description}\n\n"
        user += f"Style rubric:\n{rubric}\n\n"
        user += f"Current best SVG (iteration {iteration}):\n```svg\n{champion_svg}\n```\n\n"

        if feedback_history:
            user += "Feedback:\n"
            for i, entry in enumerate(reversed(feedback_history), 1):
                user += f"{i}. {entry.feedback}\n"
            user += "\n"

        user += (
            "Create an improved SVG that addresses the feedback above. Use the current best "
            "as reference for what works, but feel free to rethink the structure and composition. "
            "Output ONLY the SVG code, wrapped in ```svg fences."
        )

    return system, user


def build_evaluation_prompt(rubric: str, subject: str) -> tuple[str, str]:
    """Build system and user prompts for the pairwise SVG evaluator."""
    system = (
        "You are an expert art critic evaluating SVG artwork. You will compare two rendered "
        "images (Image A and Image B) of the same subject and determine which better satisfies "
        "the given rubric.\n\n"
        "You MUST respond with valid JSON containing three fields:\n"
        '- "winner": "A" or "B"\n'
        '- "rationale": brief explanation of why the winner is better\n'
        '- "feedback": structured guidance for the next iteration, formatted as:\n'
        "  Preserve: [what the current best version does well that must be kept]\n"
        "  Improve: [2-3 specific, actionable edits to make]\n"
        '  IMPORTANT: Do NOT reference "Image A", "Image B", "the winner", or "the loser" '
        "in the feedback. Write as direct instructions (e.g. \"keep the grounded hooves\", "
        '"connect the legs to the body").'
    )

    user = (
        f"Subject: {subject}\n\n"
        f"Evaluation rubric:\n{rubric}\n\n"
        "Compare Image A and Image B above. Which image better depicts the subject "
        "according to the rubric?\n\n"
        "Respond with JSON only: "
        '{{"winner": "A" or "B", "rationale": "...", "feedback": "..."}}'
    )

    return system, user
