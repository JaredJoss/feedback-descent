from __future__ import annotations

from pathlib import Path
from typing import Any

from feedback_descent.core.types import RunConfig
from feedback_descent.domains import get_domain


def build_run_config(
    domain_name: str,
    subject_name: str,
    rubric_name: str,
    iterations: int = 20,
    proposer_model: str = "anthropic/claude-sonnet-4-20250514",
    evaluator_model: str = "anthropic/claude-sonnet-4-20250514",
    order_bias: bool = True,
    informed_init: bool = True,
    output_dir: str = "./runs",
    domain_kwargs: dict[str, Any] | None = None,
) -> RunConfig:
    plugin = get_domain(domain_name)
    subject = plugin.load_config("subjects", subject_name)
    rubric = plugin.load_config("rubrics", rubric_name)

    # Build domain_config from subject fields (beyond "name") + explicit kwargs
    domain_config: dict[str, Any] = {}
    for key, value in subject.items():
        if key != "name":
            domain_config[key] = value
    if domain_kwargs:
        domain_config.update(domain_kwargs)

    return RunConfig(
        subject=subject["name"],
        rubric_text=rubric["rubric"],
        domain=domain_name,
        domain_config=domain_config,
        max_iterations=iterations,
        order_bias_mitigation=order_bias,
        proposer_model=proposer_model,
        evaluator_model=evaluator_model,
        informed_init=informed_init,
        output_dir=Path(output_dir),
    )
