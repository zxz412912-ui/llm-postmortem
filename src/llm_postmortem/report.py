"""Markdown report rendering."""

from __future__ import annotations

import html

from .analysis import Report


def _snippet(example: dict) -> str:
    value = example.get("response") or example.get("error") or example.get("output") or "No response captured"
    return " ".join(str(value).split())[:180]


def render_markdown(report: Report) -> str:
    rate = report.failed_calls / report.total_calls * 100 if report.total_calls else 0
    lines = [
        "# LLM Postmortem",
        "",
        "## Executive summary",
        "",
        f"Analyzed **{report.total_calls}** calls. **{report.failed_calls}** were marked as failures (**{rate:.1f}%**).",
        "",
        "## Failure modes",
        "",
        "| Failure mode | Incidents | Share of failures |",
        "| --- | ---: | ---: |",
    ]
    if report.findings:
        for finding in report.findings:
            lines.append(f"| {finding.kind.replace('_', ' ')} | {finding.count} | {finding.share:.1%} |")
    else:
        lines.append("| No failures detected | 0 | 0.0% |")
    lines.extend(["", "## Recommended next actions", ""])
    for index, finding in enumerate(report.findings, 1):
        lines.extend([f"{index}. **{finding.kind.replace('_', ' ').title()}** — {finding.recommendation}"])
        for example in finding.examples:
            trace_id = example.get("trace_id", example.get("id", "unidentified call"))
            lines.append(f"   - `{trace_id}`: {_snippet(example)}")
    if not report.findings:
        lines.append("No action needed from the supplied failure signals.")
    lines.extend(["", "## Model health", "", "| Model | Calls | Failures | Avg latency | Avg cost |", "| --- | ---: | ---: | ---: | ---: |"])
    for model, stats in report.model_stats.items():
        lines.append(f"| {model} | {stats['calls']} | {stats['failures']} | {stats['avg_latency_ms']} ms | ${stats['avg_cost_usd']:.5f} |")
    if report.input_errors:
        lines.extend(["", "## Input warnings", ""] + [f"- {warning}" for warning in report.input_errors])
    lines.append("")
    return "\n".join(lines)


def render_html(report: Report) -> str:
    """Render a self-contained report suitable for attaching to an issue."""
    rate = report.failed_calls / report.total_calls * 100 if report.total_calls else 0
    finding_rows = "".join(
        f"<tr data-kind='{html.escape(finding.kind)}'><td>{html.escape(finding.kind.replace('_', ' '))}</td>"
        f"<td>{finding.count}</td><td>{finding.share:.1%}</td><td>{html.escape(finding.recommendation)}</td></tr>"
        for finding in report.findings
    ) or "<tr><td colspan='4'>No failures detected.</td></tr>"
    trace_cards = "".join(
        f"<article class='trace' data-kind='{html.escape(finding.kind)}'><span>{html.escape(finding.kind.replace('_', ' '))}</span>"
        f"<h3>{html.escape(str(example.get('trace_id', example.get('id', 'unidentified call'))))}</h3>"
        f"<p>{html.escape(_snippet(example))}</p></article>"
        for finding in report.findings for example in finding.examples
    ) or "<p>No failed traces were supplied.</p>"
    model_rows = "".join(
        f"<tr><td>{html.escape(model)}</td><td>{stats['calls']}</td><td>{stats['failures']}</td>"
        f"<td>{stats['avg_latency_ms']} ms</td><td>${stats['avg_cost_usd']:.5f}</td></tr>"
        for model, stats in report.model_stats.items()
    )
    options = "".join(f"<option value='{html.escape(item.kind)}'>{html.escape(item.kind.replace('_', ' '))}</option>" for item in report.findings)
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>LLM Postmortem</title><style>
:root {{ color-scheme: dark; --ink:#e9edf7; --muted:#aeb8cd; --panel:#151c2c; --line:#29344d; --accent:#8b9cff; --bg:#0c1020; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 ui-sans-serif,system-ui,sans-serif }}
main {{ max-width:1050px; margin:auto; padding:48px 24px 80px }} h1 {{ font-size:clamp(2rem,6vw,4.6rem); letter-spacing:-.06em; margin:0 }}
.eyebrow, .trace span {{ color:var(--accent); text-transform:uppercase; font-size:.73rem; letter-spacing:.12em; font-weight:700 }}
.lead {{ color:var(--muted); max-width:650px; font-size:1.15rem }} .cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:32px 0 48px }}
.card, .trace {{ border:1px solid var(--line); border-radius:14px; padding:20px; background:var(--panel) }} .card b {{ font-size:2rem; display:block }}
section {{ margin-top:42px }} h2 {{ letter-spacing:-.03em }} table {{ width:100%; border-collapse:collapse; overflow:hidden }} th,td {{ border-bottom:1px solid var(--line); padding:14px 10px; text-align:left; vertical-align:top }} th {{ color:var(--muted); font-size:.78rem; text-transform:uppercase }}
.controls {{ display:flex; justify-content:space-between; align-items:center; gap:15px }} select {{ background:var(--panel); color:var(--ink); border:1px solid var(--line); border-radius:8px; padding:9px }} .traces {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px }} .trace h3 {{ margin:7px 0 }} .trace p {{ color:var(--muted); margin:0 }} @media(max-width:650px){{.cards{{grid-template-columns:1fr}} table{{font-size:.85rem}}}}
</style></head><body><main>
<p class='eyebrow'>local-first LLM observability</p><h1>Postmortem.</h1><p class='lead'>Analyzed {report.total_calls} calls and found {report.failed_calls} failure signals. Start with the largest recurring pattern.</p>
<div class='cards'><div class='card'><small>Total calls</small><b>{report.total_calls}</b></div><div class='card'><small>Failure rate</small><b>{rate:.1f}%</b></div><div class='card'><small>Failure modes</small><b>{len(report.findings)}</b></div></div>
<section><h2>What to fix</h2><table><thead><tr><th>Failure mode</th><th>Incidents</th><th>Share</th><th>Recommended action</th></tr></thead><tbody>{finding_rows}</tbody></table></section>
<section><div class='controls'><h2>Representative traces</h2><label>Filter <select id='filter'><option value='all'>All modes</option>{options}</select></label></div><div class='traces'>{trace_cards}</div></section>
<section><h2>Model health</h2><table><thead><tr><th>Model</th><th>Calls</th><th>Failures</th><th>Avg latency</th><th>Avg cost</th></tr></thead><tbody>{model_rows}</tbody></table></section>
</main><script>document.querySelector('#filter').addEventListener('change', e => document.querySelectorAll('.trace').forEach(x => x.hidden = e.target.value !== 'all' && x.dataset.kind !== e.target.value));</script></body></html>"""
