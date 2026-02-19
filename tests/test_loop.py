from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from feedback_descent.core.loop import feedback_descent
from feedback_descent.core.types import Candidate, Evaluation, RunConfig


def make_config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        subject="test",
        rubric_text="Test rubric",
        domain="test",
        domain_config={"subject_description": "A test subject"},
        max_iterations=3,
        order_bias_mitigation=False,
        output_dir=tmp_path,
    )


@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.save_champion = AsyncMock()
    tracker.save_candidate = AsyncMock()
    tracker.save_evaluation = AsyncMock()
    tracker.save_final = AsyncMock()
    return tracker


@pytest.mark.asyncio
async def test_champion_updates_on_preferred(tmp_path, mock_tracker):
    """When evaluator prefers challenger, champion should update."""
    config = make_config(tmp_path)

    seed = Candidate(content="<svg>seed</svg>", iteration=0)
    challenger1 = Candidate(content="<svg>better</svg>", iteration=1)

    proposer = MagicMock()
    proposer.propose = AsyncMock(side_effect=[seed, challenger1,
        Candidate(content="<svg>c2</svg>", iteration=2),
        Candidate(content="<svg>c3</svg>", iteration=3),
    ])

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=[
        Evaluation(preferred=True, rationale="Better!", feedback="Better!", challenger=challenger1, champion=seed, raw_response=""),
        Evaluation(preferred=False, rationale="Nope", feedback="Fix legs", challenger=Candidate("", 2), champion=challenger1, raw_response=""),
        Evaluation(preferred=False, rationale="Nope", feedback="Fix legs", challenger=Candidate("", 3), champion=challenger1, raw_response=""),
    ])

    result = await feedback_descent(proposer, evaluator, config, mock_tracker)

    # Champion should be the first challenger that won
    assert result.content == "<svg>better</svg>"
    # save_champion called for seed + one update
    assert mock_tracker.save_champion.call_count == 2


@pytest.mark.asyncio
async def test_champion_retained_when_not_preferred(tmp_path, mock_tracker):
    """When evaluator prefers champion, it should be retained."""
    config = make_config(tmp_path)

    seed = Candidate(content="<svg>seed</svg>", iteration=0)

    proposer = MagicMock()
    proposer.propose = AsyncMock(side_effect=[
        seed,
        Candidate(content="<svg>c1</svg>", iteration=1),
        Candidate(content="<svg>c2</svg>", iteration=2),
        Candidate(content="<svg>c3</svg>", iteration=3),
    ])

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=[
        Evaluation(preferred=False, rationale="Keep champion", feedback="Fix proportions", challenger=Candidate("", 1), champion=seed, raw_response=""),
        Evaluation(preferred=False, rationale="Keep champion", feedback="Fix proportions", challenger=Candidate("", 2), champion=seed, raw_response=""),
        Evaluation(preferred=False, rationale="Keep champion", feedback="Fix proportions", challenger=Candidate("", 3), champion=seed, raw_response=""),
    ])

    result = await feedback_descent(proposer, evaluator, config, mock_tracker)

    assert result.content == "<svg>seed</svg>"
    # save_champion called only for seed
    assert mock_tracker.save_champion.call_count == 1


@pytest.mark.asyncio
async def test_proposal_failure_skips_iteration(tmp_path, mock_tracker):
    """If proposer fails, that iteration is skipped."""
    config = make_config(tmp_path)

    seed = Candidate(content="<svg>seed</svg>", iteration=0)

    proposer = MagicMock()
    proposer.propose = AsyncMock(side_effect=[
        seed,
        ValueError("Parse failed"),
        Candidate(content="<svg>c2</svg>", iteration=2),
        Candidate(content="<svg>c3</svg>", iteration=3),
    ])

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=[
        Evaluation(preferred=True, rationale="Win", feedback="Win", challenger=Candidate("", 2), champion=seed, raw_response=""),
        Evaluation(preferred=False, rationale="No", feedback="Fix neck", challenger=Candidate("", 3), champion=seed, raw_response=""),
    ])

    result = await feedback_descent(proposer, evaluator, config, mock_tracker)

    # Evaluator called only twice (iteration 1 was skipped)
    assert evaluator.evaluate.call_count == 2


@pytest.mark.asyncio
async def test_evaluation_failure_does_not_append_feedback(tmp_path, mock_tracker):
    """When evaluator raises ValueError, feedback_history should not grow."""
    config = make_config(tmp_path)

    seed = Candidate(content="<svg>seed</svg>", iteration=0)

    # Track feedback_history length at each propose call
    feedback_history_sizes: list[int] = []

    async def propose_side_effect(champion, feedback_history, iteration):
        feedback_history_sizes.append(len(feedback_history))
        candidates = [
            seed,
            Candidate(content="<svg>c1</svg>", iteration=1),
            Candidate(content="<svg>c2</svg>", iteration=2),
            Candidate(content="<svg>c3</svg>", iteration=3),
        ]
        return candidates[len(feedback_history_sizes) - 1]

    proposer = MagicMock()
    proposer.propose = AsyncMock(side_effect=propose_side_effect)

    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=[
        ValueError("Could not parse judge response"),
        Evaluation(preferred=False, rationale="Keep", feedback="Fix legs",
                   challenger=Candidate("", 2), champion=seed, raw_response=""),
        Evaluation(preferred=False, rationale="Keep", feedback="Fix neck",
                   challenger=Candidate("", 3), champion=seed, raw_response=""),
    ])

    result = await feedback_descent(proposer, evaluator, config, mock_tracker)

    assert result.content == "<svg>seed</svg>"
    # feedback_history_sizes: [seed_call, iter1, iter2, iter3]
    # After eval error in iter1, feedback_history should still be empty for iter2
    assert feedback_history_sizes[0] == 0  # seed call
    assert feedback_history_sizes[1] == 0  # iter1: no feedback yet
    assert feedback_history_sizes[2] == 0  # iter2: eval error did NOT append
    assert feedback_history_sizes[3] == 1  # iter3: iter2's feedback was appended


@pytest.mark.asyncio
async def test_inconsistent_eval_raises_valueerror(tmp_path, mock_tracker):
    """Inconsistent bias-mitigated evals should raise ValueError and skip iteration."""
    config = make_config(tmp_path)
    config.order_bias_mitigation = True

    seed = Candidate(content="<svg>seed</svg>", iteration=0)

    proposer = MagicMock()
    proposer.propose = AsyncMock(side_effect=[
        seed,
        Candidate(content="<svg>c1</svg>", iteration=1),
    ])

    # The evaluator will raise ValueError (simulating what our fixed
    # _evaluate_with_bias_mitigation now does on inconsistency)
    evaluator = MagicMock()
    evaluator.evaluate = AsyncMock(side_effect=[
        ValueError("Order bias mitigation: inconsistent results across orderings after 3 attempts"),
    ])

    config.max_iterations = 1
    result = await feedback_descent(proposer, evaluator, config, mock_tracker)

    # Champion should be the seed (no update happened)
    assert result.content == "<svg>seed</svg>"
    assert mock_tracker.save_champion.call_count == 1
