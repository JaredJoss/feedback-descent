# Feedback Descent

Open-ended optimization via pairwise comparison feedback. A domain-agnostic framework that iteratively improves text-based artifacts (SVG images, prompts, molecules, etc.) using LLM-driven proposal and evaluation.

Based on the paper [*Feedback Descent: Textual Feedback as a Unified Objective for Open-Ended Optimization*](https://arxiv.org/abs/2511.07919).

## How it works

Feedback Descent maintains a **champion** candidate and repeatedly:

1. **Propose** a challenger — an LLM generates an improved variant using the current champion and accumulated feedback
2. **Evaluate** challenger vs champion — a judge (LLM with optional rendered artifacts) picks the better candidate via pairwise comparison, and provides **actionable feedback** for improving the losing candidate
3. **Update** — if the challenger wins, it becomes the new champion and the feedback history resets; otherwise the actionable feedback is appended to the feedback buffer for the next proposal

This loop requires no scalar reward signal. The evaluator's natural-language feedback *is* the gradient — hence the name. Crucially, the feedback passed to the proposer is **actionable improvement suggestions** (e.g. "make the legs connect to the body", "add shading to convey volume") rather than comparative analysis.

```
            ┌─────────────┐
            │  Proposer    │◄── champion + feedback history
            │  (LLM)       │
            └──────┬──────┘
                   │ challenger
                   ▼
            ┌─────────────┐
            │  Evaluator   │◄── challenger vs champion
            │  (LLM judge) │
            └──────┬──────┘
                   │ preferred? + rationale + feedback
                   ▼
         ┌─── yes ───┐─── no ───┐
         │            │          │
    champion ←   challenger   append feedback
    updated      discarded    to feedback history
    feedback
    reset
```

**Order bias mitigation:** By default, each evaluation runs twice with swapped presentation order (A-B then B-A). Only consistent verdicts are accepted; inconsistent results are discarded and the iteration is skipped.

**Seed initialization:** Two modes from the paper — `--informed` (default) conditions the initial generation on the rubric, while `--scratch` omits the rubric from the seed prompt so the first candidate is generated from the subject description alone.

## Installation

Requires Python 3.12+.

```bash
# Install
uv sync

# For development
uv sync --extra dev
```

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY or OPENAI_API_KEY
```

## Quick start

```bash
# Run SVG optimization (uses Claude Sonnet by default)
feedback-descent run --domain svg --subject unicorn --rubric anatomical_realism --iterations 20

# Use OpenAI models (as in the paper)
feedback-descent run --domain svg --subject unicorn --rubric anatomical_realism \
  --proposer-model openai/gpt-5-mini --evaluator-model openai/gpt-5-mini --iterations 20

# With custom rendering options
feedback-descent run --domain svg --subject unicorn --rubric minimalist \
  --renderer cairosvg --render-width 768 --render-height 768

# Disable order bias mitigation for faster runs
feedback-descent run --domain svg --subject unicorn --rubric anatomical_realism \
  --no-order-bias --iterations 5

# Scratch seed mode (omit rubric from initial generation)
feedback-descent run --domain svg --subject unicorn --rubric anatomical_realism \
  --scratch --iterations 20
```

Models are specified in [LiteLLM format](https://docs.litellm.ai/docs/providers) (e.g. `openai/gpt-5-mini`, `anthropic/claude-sonnet-4-20250514`). Set the corresponding API key in your `.env` file.

## CLI reference

```bash
# List available domains
feedback-descent list-domains

# List subjects and rubrics for a domain
feedback-descent list-subjects --domain svg
feedback-descent list-rubrics --domain svg

# Regenerate trajectory visualization from a completed run
feedback-descent trajectory runs/run_20260217_143000/
```

## Available SVG rubrics

| Rubric | Style |
|---|---|
| `anatomical_realism` | Believable equine anatomy — proportions, joint articulation, volume |
| `minimalist` | Maximum recognition from minimum elements — shape economy, 4-color cap |
| `ink_wash` | Sumi-e brush painting — stroke variation, negative space, monochrome |
| `retro_arcade` | 8-bit pixel art — grid alignment, 16-color palette, dithering |
| `stained_glass` | Leaded glass window — lead-line network, jewel tones, panel discipline |

Rubrics follow a structured format: **intent**, **non-negotiables**, **critical benchmarks** (evaluated first), **what to reward**, **what to penalize**, and **tiebreakers**.

## Run output

Each run creates a timestamped directory under `runs/`:

```
runs/run_20260217_143000/
├── config.json              # Full run configuration
├── candidates/              # Every challenger proposed
├── champions/               # Champion snapshots at each update
├── renders/                 # Rendered artifacts (PNGs for SVG domain)
├── evaluations/             # Judge verdicts with rationales + feedback
├── final/                   # Final champion + rendered artifact
├── summary.json             # Run statistics + feedback log
└── trajectory.html          # Visual progression (champion frontier + feedback timeline)
```

The `summary.json` includes a `feedback_log` array with per-iteration outcomes: which candidate won, the comparative rationale, and the actionable feedback given. The `trajectory.html` visualizes this as a **Champion Frontier** gallery (showing each champion update) and a **Feedback Log** timeline (color-coded by outcome).

## Project structure

```
src/feedback_descent/
├── core/
│   ├── types.py             # Candidate, Evaluation, RunConfig
│   ├── protocols.py         # Proposer, Evaluator, ArtifactRenderer protocols
│   └── loop.py              # The feedback descent algorithm
├── domains/
│   ├── base.py              # DomainPlugin base class
│   ├── __init__.py          # Domain registry
│   └── svg/                 # SVG optimization domain
│       ├── proposer.py      # LLM-based SVG generation
│       ├── evaluator.py     # Vision-based pairwise comparison
│       ├── renderer.py      # SVG → PNG (CairoSVG or Playwright)
│       ├── parser.py        # Extract SVG from LLM responses
│       └── prompts.py       # Prompt templates
├── llm/
│   └── client.py            # LiteLLM wrapper (text + vision)
├── logging/
│   ├── run_tracker.py       # Artifact persistence
│   └── trajectory.py        # HTML trajectory visualization
├── config/
│   └── loader.py            # Domain-aware config loading
└── cli/
    └── main.py              # Click CLI
```

## Adding a new domain

Create a domain plugin without touching core code:

1. Create `src/feedback_descent/domains/yourdom/` with a `__init__.py` containing a `DomainPlugin` subclass
2. Create `configs/yourdom/subjects/` and `configs/yourdom/rubrics/` with YAML configs
3. Register it in `domains/__init__.py._register_builtins()`

Your plugin implements `create_components()` returning a `Proposer`, `Evaluator`, and optional `ArtifactRenderer`. The core loop, logging, CLI, and config loading all work automatically.

```python
# src/feedback_descent/domains/yourdom/__init__.py
from feedback_descent.domains.base import DomainComponents, DomainPlugin

class YourDomain(DomainPlugin):
    name = "yourdom"
    description = "One-line description"

    def create_components(self, config, proposer_llm, evaluator_llm):
        return DomainComponents(
            proposer=YourProposer(proposer_llm, config),
            evaluator=YourEvaluator(evaluator_llm, config),
            artifact_renderer=None,  # or a renderer for visual artifacts
        )

    def list_configs(self, config_type):
        # return list of available config names
        ...

    def load_config(self, config_type, name):
        # return parsed YAML dict
        ...
```

Then run: `feedback-descent run --domain yourdom --subject my_task --rubric my_rubric`

## Roadmap

Items deferred from the paper alignment effort:

- **Show previous candidates to proposer** — The paper's rationale history R stores (candidate, feedback) pairs; our proposer currently only sees the feedback text, not what was tried before. Deferred because SVG content is large (thousands of tokens per candidate) and including multiple failed SVGs in the prompt would balloon context quickly. The paper runs only 5 iterations so R stays small; with our default of 20 iterations this is a real concern. A context-aware approach (e.g. only most recent candidate, or summarized diffs) is needed.

- **Multi-seed initialization** — Generate N seed candidates and tournament-select the best via the evaluator (paper's full "Informed" regime with multiple seeds).

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```
