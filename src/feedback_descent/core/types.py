from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Candidate:
    content: str
    iteration: int
    metadata: dict = field(default_factory=dict)


@dataclass
class Evaluation:
    preferred: bool  # True if challenger is preferred over champion
    rationale: str
    feedback: str  # Actionable improvement suggestions for the losing candidate
    challenger: Candidate
    champion: Candidate
    raw_response: str


@dataclass
class FeedbackEntry:
    candidate: Candidate
    feedback: str
    iteration: int


@dataclass
class RunConfig:
    subject: str
    rubric_text: str
    domain: str = "svg"
    domain_config: dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 20
    order_bias_mitigation: bool = True
    proposer_model: str = "anthropic/claude-sonnet-4-20250514"
    evaluator_model: str = "anthropic/claude-sonnet-4-20250514"
    informed_init: bool = True
    output_dir: Path = field(default_factory=lambda: Path("runs"))
