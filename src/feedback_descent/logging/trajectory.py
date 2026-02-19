from __future__ import annotations

import base64
import html as html_module
import json
from pathlib import Path

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
_SKIP_EXTENSIONS = {".txt", ".json"}


def _find_artifact_files(champions_dir: Path) -> list[Path]:
    """Find non-text, non-json artifact files (images) in the champions dir."""
    artifacts = []
    for p in sorted(champions_dir.iterdir()):
        if p.suffix.lower() in _IMAGE_EXTENSIONS:
            artifacts.append(p)
    return artifacts


def _media_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }
    return mapping.get(ext, "application/octet-stream")


def generate_trajectory_html(run_dir: Path) -> Path:
    """Generate a self-contained HTML visualization of champion progression and feedback."""
    config = json.loads((run_dir / "config.json").read_text())
    champions_dir = run_dir / "champions"
    evaluations_dir = run_dir / "evaluations"

    # Load summary for feedback log
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    feedback_log = summary.get("feedback_log", [])

    # If no feedback_log in summary, reconstruct from evaluation files
    if not feedback_log:
        for eval_path in sorted(evaluations_dir.glob("iter_*.json")):
            eval_data = json.loads(eval_path.read_text())
            feedback_log.append({
                "iteration": eval_data["iteration"],
                "outcome": "challenger_wins" if eval_data["preferred"] else "champion_retained",
                "rationale": eval_data.get("rationale", ""),
                "champion_iteration": eval_data.get("champion_iteration", "?"),
                "challenger_iteration": eval_data.get("challenger_iteration", "?"),
            })

    # Detect artifact type dynamically
    image_artifacts = _find_artifact_files(champions_dir)

    if image_artifacts:
        cards_html = _build_image_cards(image_artifacts, evaluations_dir)
    else:
        txt_files = sorted(champions_dir.glob("champion_iter_*.txt"))
        cards_html = _build_text_cards(txt_files, evaluations_dir)

    timeline_html = _build_feedback_timeline(feedback_log)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Feedback Descent Trajectory — {config.get('subject', 'unknown')}</title>
<style>
    body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #eee; margin: 2rem; }}
    h1 {{ text-align: center; color: #e94560; }}
    h2 {{ text-align: center; color: #aaa; font-weight: normal; }}
    h3.section {{ color: #e94560; margin-top: 2.5rem; margin-bottom: 1rem; }}
    .grid {{ display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: center; margin-top: 2rem; }}
    .card {{
        background: #16213e; border-radius: 12px; padding: 1rem;
        width: 280px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .card h3 {{ margin: 0 0 0.5rem; color: #e94560; font-size: 0.9rem; }}
    .card img {{ width: 100%; border-radius: 8px; }}
    .card pre {{
        font-size: 0.7rem; color: #ccc; background: #0d1117; padding: 0.5rem;
        border-radius: 6px; max-height: 200px; overflow: auto; white-space: pre-wrap;
        word-break: break-word;
    }}
    .card .rationale {{
        font-size: 0.8rem; color: #aaa; margin-top: 0.5rem;
        max-height: 100px; overflow-y: auto;
    }}
    .timeline {{ max-width: 900px; margin: 1rem auto; }}
    .timeline-entry {{
        background: #16213e; border-radius: 8px; padding: 0.75rem 1rem;
        margin-bottom: 0.5rem; border-left: 4px solid #444;
    }}
    .timeline-entry.win {{ border-left-color: #27ae60; }}
    .timeline-entry.lose {{ border-left-color: #7f8c8d; }}
    .timeline-header {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 0.3rem;
    }}
    .timeline-iter {{ font-weight: bold; font-size: 0.85rem; }}
    .timeline-badge {{
        font-size: 0.75rem; padding: 2px 8px; border-radius: 4px;
        font-weight: bold;
    }}
    .badge-win {{ background: #27ae60; color: #fff; }}
    .badge-lose {{ background: #7f8c8d; color: #fff; }}
    .timeline-rationale {{ font-size: 0.8rem; color: #aaa; line-height: 1.4; }}
</style>
</head>
<body>
<h1>Feedback Descent Trajectory</h1>
<h2>{config.get('subject', '')} — {config.get('rubric_text', '')[:80]}...</h2>

<h3 class="section" style="text-align:center;">Champion Frontier</h3>
<div class="grid">
{cards_html}
</div>

<h3 class="section" style="text-align:center;">Feedback Log</h3>
{timeline_html}
</body>
</html>"""

    out_path = run_dir / "trajectory.html"
    out_path.write_text(html)
    return out_path


def _iter_num_from_path(path: Path) -> int:
    """Extract iteration number from filenames like champion_iter_003.txt or .png."""
    # Stem is e.g. "champion_iter_003"
    return int(path.stem.split("_")[-1])


def _get_rationale(evaluations_dir: Path, iter_num: int) -> str:
    eval_path = evaluations_dir / f"iter_{iter_num:03d}.json"
    if eval_path.exists():
        eval_data = json.loads(eval_path.read_text())
        return eval_data.get("rationale", "")
    return ""


def _build_image_cards(image_files: list[Path], evaluations_dir: Path) -> str:
    cards = ""
    for img_path in image_files:
        iter_num = _iter_num_from_path(img_path)
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        media_type = _media_type_for(img_path)
        rationale = _get_rationale(evaluations_dir, iter_num)
        label = "Seed" if iter_num == 0 else f"Iteration {iter_num}"
        cards += f"""
        <div class="card">
            <h3>{label}</h3>
            <img src="data:{media_type};base64,{b64}" alt="{label}">
            <p class="rationale">{rationale[:300] if rationale else 'Initial generation'}</p>
        </div>
        """
    return cards


def _build_feedback_timeline(feedback_log: list[dict]) -> str:
    if not feedback_log:
        return '<div class="timeline"><p style="text-align:center;color:#aaa;">No evaluations recorded.</p></div>'
    entries = ""
    for entry in feedback_log:
        is_win = entry["outcome"] == "challenger_wins"
        css_class = "win" if is_win else "lose"
        badge_class = "badge-win" if is_win else "badge-lose"
        badge_text = "Challenger wins" if is_win else "Champion retained"
        rationale = html_module.escape(entry.get("rationale", ""))
        entries += f"""
        <div class="timeline-entry {css_class}">
            <div class="timeline-header">
                <span class="timeline-iter">Iteration {entry['iteration']}</span>
                <span class="timeline-badge {badge_class}">{badge_text}</span>
            </div>
            <div class="timeline-rationale">{rationale}</div>
        </div>
        """
    return f'<div class="timeline">{entries}</div>'


def _build_text_cards(txt_files: list[Path], evaluations_dir: Path) -> str:
    cards = ""
    for txt_path in txt_files:
        iter_num = _iter_num_from_path(txt_path)
        content = txt_path.read_text()
        rationale = _get_rationale(evaluations_dir, iter_num)
        label = "Seed" if iter_num == 0 else f"Iteration {iter_num}"
        escaped = html_module.escape(content[:500])
        cards += f"""
        <div class="card">
            <h3>{label}</h3>
            <pre>{escaped}</pre>
            <p class="rationale">{rationale[:300] if rationale else 'Initial generation'}</p>
        </div>
        """
    return cards
