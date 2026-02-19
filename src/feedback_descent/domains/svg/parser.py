from __future__ import annotations

import re


def extract_svg(llm_response: str) -> str:
    """Extract SVG code from an LLM response.

    Handles ```svg, ```xml fenced blocks, and raw <svg>...</svg>.
    Raises ValueError if no valid SVG is found.
    """
    # Try fenced code blocks first
    fence_pattern = re.compile(r"```(?:svg|xml)\s*\n(.*?)```", re.DOTALL)
    match = fence_pattern.search(llm_response)
    if match:
        svg = match.group(1).strip()
        if "<svg" in svg:
            return svg

    # Try generic fenced block
    generic_fence = re.compile(r"```\s*\n(.*?)```", re.DOTALL)
    match = generic_fence.search(llm_response)
    if match:
        svg = match.group(1).strip()
        if "<svg" in svg:
            return svg

    # Try raw <svg>...</svg>
    svg_pattern = re.compile(r"(<svg[\s\S]*?</svg>)", re.DOTALL)
    match = svg_pattern.search(llm_response)
    if match:
        return match.group(1).strip()

    raise ValueError("No valid SVG found in LLM response")
