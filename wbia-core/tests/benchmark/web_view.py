#!/usr/bin/env python3
"""Bottle web app for viewing parity benchmark results."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import bottle
from bottle import get, redirect, request, run, static_file

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compare import compare_results  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
RESULTS_DIR = PROJECT_ROOT / "test-results"
REFERENCE_DIR = HERE / "reference"


def _discover_runs() -> list[dict[str, Any]]:
    """Scan for test-run directories and reference data."""
    runs = []

    for d in sorted(RESULTS_DIR.glob("test-run-results-*"), reverse=True):
        run_id = d.name
        summary_path = d / "summary.json"
        config_path = d / "config.json"

        summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
        config = json.loads(config_path.read_text()) if config_path.exists() else {}

        runs.append(
            {
                "id": run_id,
                "name": run_id.replace("test-run-results-", ""),
                "path": str(d),
                "date": summary.get("run_id", ""),
                "targets": summary.get("targets", []),
                "config": config,
                "agreement": summary.get("agreement", {}),
                "n_queries": len(summary.get("per_query", [])),
                "n_errors": len(summary.get("errors", [])),
                "has_summary": summary_path.exists(),
            }
        )

    # Add reference directories
    for d in sorted(REFERENCE_DIR.glob("*/"), reverse=True):
        manifest_path = d / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text())
        runs.append(
            {
                "id": f"reference-{d.name}",
                "name": f"[reference] {d.name}",
                "path": str(d),
                "date": manifest.get("started_at", ""),
                "targets": [manifest.get("target", "reference")],
                "config": {"n_annots": manifest.get("n_queries", "?")},
                "manifest": manifest,
                "agreement": {},
                "n_queries": manifest.get("n_queries", 0),
                "n_errors": len(manifest.get("errors", [])),
                "is_reference": True,
                "has_summary": False,
            }
        )

    return runs


def _get_compare_data(run_name: str) -> dict[str, Any] | None:
    """Get comparison data for a run."""
    if run_name.startswith("reference-"):
        ref_name = run_name.replace("reference-", "")
        ref_path = REFERENCE_DIR / ref_name
        if ref_path.exists():
            return _reference_to_summary(ref_path)
        return None

    run_path = RESULTS_DIR / run_name
    if not run_path.exists():
        return None

    summary_path = run_path / "summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text())

    try:
        return compare_results(run_path)
    except Exception as exc:
        return {"error": str(exc)}


def _reference_to_summary(ref_path: Path) -> dict[str, Any]:
    """Build a summary-like dict from reference data for display."""
    manifest = json.loads((ref_path / "manifest.json").read_text())
    target_name = manifest.get("target", "reference")
    n_queries = manifest.get("n_queries", 0)

    per_query = []
    all_scores = {}
    for qi in range(n_queries):
        qdir = ref_path / f"query_{qi:03d}"
        resp_path = qdir / "response.json"
        if not resp_path.exists():
            continue
        resp = json.loads(resp_path.read_text())
        scores = resp.get("response", {}).get("annot_scores", [])
        scores_sorted = sorted(scores, key=lambda x: x.get("score", 0), reverse=True)
        all_scores[qi] = {target_name: scores_sorted}

        entry = {
            "query_index": resp.get("query_index", qi),
            "top1_aids": {
                target_name: scores_sorted[0]["aid"] if scores_sorted else None
            },
            "max_score_delta": 0.0,
            "spearman_pairs": [],
            "top3_overlap": {},
            "score_stats": {},
        }
        if scores_sorted:
            vals = [s["score"] for s in scores_sorted]
            mean = sum(vals) / len(vals)
            entry["score_stats"][target_name] = {
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "mean": round(mean, 4),
                "std": round(
                    (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5, 4
                ),
            }
        per_query.append(entry)

    return {
        "run_id": f"reference-{ref_path.name}",
        "config": {"n_annots": n_queries, "n_queries": n_queries},
        "targets": [target_name],
        "agreement": {
            "top1_identical": True,
            "all_rankings_match": True,
            "max_score_delta": 0.0,
            "spearman_below_pairs": [],
        },
        "per_query": per_query,
        "errors": [],
        "aggregate_spearman": {},
        "top3_overall_overlap": {},
        "score_distributions": {},
        "top_k_aids": {},
    }


def _fmt_timestamp(ts: str) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def _pass_fail(val: bool) -> str:
    return (
        '<span class="badge pass">PASS</span>'
        if val
        else '<span class="badge fail">FAIL</span>'
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@get("/")
def home():
    runs = _discover_runs()
    return bottle.template(_HOME_TPL, runs=runs, pf=_pass_fail)


@get("/run/<run_name>")
def run_detail(run_name: str):
    data = _get_compare_data(run_name)
    if data is None:
        return bottle.template(_ERROR_TPL, message=f"Run '{run_name}' not found.")
    if "error" in data:
        return bottle.template(_ERROR_TPL, message=data["error"])
    return bottle.template(
        _RUN_TPL, run_id=run_name, data=data, fmt_ts=_fmt_timestamp, pf=_pass_fail
    )


@get("/run/<run_name>/data")
def run_data_json(run_name: str):
    data = _get_compare_data(run_name)
    if data is None:
        return {"error": "not found"}
    return data


@get("/static/<filename:path>")
def static(filename):
    return static_file(filename, root=str(HERE / "static"))


@get("/api/runs")
def runs_json():
    runs = _discover_runs()
    return {"runs": runs}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

_HOME_TPL = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Parity Benchmark Dashboard</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }
.container { max-width: 1100px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }
.subtitle { color: #94a3b8; margin-bottom: 2rem; font-size: 0.95rem; }
.run-list { display: flex; flex-direction: column; gap: 0.75rem; }
.run-card { background: #1e293b; border-radius: 10px; padding: 1.25rem 1.5rem; border: 1px solid #334155; transition: border-color 0.15s; cursor: pointer; text-decoration: none; color: inherit; display: block; }
.run-card:hover { border-color: #6366f1; }
.run-card h3 { font-size: 1.05rem; margin-bottom: 0.5rem; }
.run-meta { display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.85rem; color: #94a3b8; }
.run-meta span { display: inline-flex; align-items: center; gap: 0.35rem; }
.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.badge.pass { background: #065f46; color: #6ee7b7; }
.badge.fail { background: #7f1d1d; color: #fca5a5; }
.badge.info { background: #1e3a5f; color: #93c5fd; }
.badge.warn { background: #78350f; color: #fcd34d; }
.empty { text-align: center; padding: 3rem; color: #64748b; }
.empty h2 { font-size: 1.5rem; margin-bottom: 0.5rem; }
</style>
</head>
<body>
<div class="container">
  <h1>&#x1F50D; Parity Benchmark Dashboard</h1>
  <p class="subtitle">Test run results for wbia-core vs WBIA reference</p>
  % if not runs:
  <div class="empty">
    <h2>No results found</h2>
    <p>Run <code>make test-parity</code> to generate results, or check the <code>test-results/</code> directory.</p>
  </div>
  % end
  <div class="run-list">
  % for r in runs:
    <a href="/run/{{r['id']}}" class="run-card">
      <h3>{{r['name']}}</h3>
      <div class="run-meta">
        % if r.get('is_reference'):
          <span class="badge info">reference</span>
        % end
        % if r['targets']:
          <span>targets: {{' + '.join(r['targets'])}}</span>
        % end
        % if r['n_queries']:
          <span>{{r['n_queries']}} queries</span>
        % end
        % if r['n_errors']:
          <span class="badge warn">{{r['n_errors']}} error(s)</span>
        % end
        % if r['agreement'].get('top1_identical') is not None:
          {{!pf(r['agreement']['top1_identical'])}}
        % end
        % if r.get('date'):
          <span>{{r['date']}}</span>
        % end
      </div>
    </a>
  % end
  </div>
</div>
</body>
</html>
"""

_RUN_TPL = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{data['run_id']}} — Parity Benchmark</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 1.5rem; font-weight: 700; }
h2 { font-size: 1.15rem; font-weight: 600; margin: 1.5rem 0 0.75rem; padding-bottom: 0.35rem; border-bottom: 1px solid #334155; }
h3 { font-size: 1rem; font-weight: 600; margin: 1rem 0 0.5rem; }
a { color: #818cf8; text-decoration: none; }
a:hover { text-decoration: underline; }
.back { display: inline-block; margin-bottom: 1rem; font-size: 0.9rem; color: #94a3b8; }
.back:hover { color: #e2e8f0; }
.card { background: #1e293b; border-radius: 10px; padding: 1.25rem 1.5rem; border: 1px solid #334155; margin-bottom: 1rem; }
.card-title { font-weight: 600; margin-bottom: 0.75rem; font-size: 0.95rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; }
.meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; }
.meta-item { }
.meta-label { font-size: 0.75rem; color: #64748b; margin-bottom: 0.15rem; }
.meta-value { font-size: 1rem; font-weight: 600; }
.badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.badge.pass { background: #065f46; color: #6ee7b7; }
.badge.fail { background: #7f1d1d; color: #fca5a5; }
.badge.info { background: #1e3a5f; color: #93c5fd; }
table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #334155; }
th { color: #94a3b8; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
tr:hover td { background: #24344d; }
.pass-val { color: #6ee7b7; }
.fail-val { color: #fca5a5; }
.warn-val { color: #fcd34d; }
.query-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }
.query-header:hover { color: #818cf8; }
.query-body { display: none; }
.query-body.open { display: block; }
.spearman-grid { display: flex; gap: 1rem; flex-wrap: wrap; }
.spearman-card { background: #24344d; border-radius: 6px; padding: 0.75rem 1rem; min-width: 180px; }
.spearman-label { font-size: 0.8rem; color: #94a3b8; }
.spearman-val { font-size: 1.1rem; font-weight: 700; }
.error-list { list-style: none; }
.error-list li { padding: 0.4rem 0; color: #fca5a5; font-size: 0.875rem; }
.score-chart { display: flex; align-items: flex-end; gap: 2px; height: 60px; margin-top: 0.5rem; }
.score-bar { background: #6366f1; border-radius: 2px 2px 0 0; min-width: 6px; flex: 1; }
.score-bar:hover { opacity: 0.8; }
</style>
</head>
<body>
<div class="container">
  <a href="/" class="back">&larr; Back to runs</a>
  <h1>{{data['run_id']}}</h1>

  <!-- Config card -->
  <div class="card" style="margin-top: 1rem;">
    <div class="card-title">Run Config</div>
    <div class="meta-grid">
      % if data.get('config'):
        % for key in ('n_annots', 'n_queries', 'seed', 'species', 'pipeline_root', 'K', 'Knorm', 'Kpad'):
          % if key in data['config']:
          <div class="meta-item">
            <div class="meta-label">{{key}}</div>
            <div class="meta-value">{{data['config'][key]}}</div>
          </div>
          % end
        % end
      % end
      <div class="meta-item">
        <div class="meta-label">targets</div>
        <div class="meta-value">{{' + '.join(data.get('targets', []))}}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">errors</div>
        <div class="meta-value">{{len(data.get('errors', []))}}</div>
      </div>
    </div>
  </div>

  <!-- Agreement card -->
  <div class="card">
    <div class="card-title">Global Agreement</div>
    <div class="meta-grid">
      <div class="meta-item">
        <div class="meta-label">Top-1 Identical</div>
        <div class="meta-value">{{!pf(data['agreement']['top1_identical']) if data['agreement'].get('top1_identical') is not None else '<span class="badge info">N/A</span>'}}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">All Rankings Match</div>
        <div class="meta-value">{{!pf(data['agreement']['all_rankings_match']) if data['agreement'].get('all_rankings_match') is not None else '<span class="badge info">N/A</span>'}}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Max Score Delta</div>
        <div class="meta-value {{'pass-val' if data['agreement'].get('max_score_delta', 0) < 1 else 'warn-val'}}">{{data['agreement'].get('max_score_delta', 0)}}</div>
      </div>
    </div>

    % if data.get('aggregate_spearman'):
    <h3>Aggregate Spearman</h3>
    <div class="spearman-grid">
      % for key, stats in data['aggregate_spearman'].items():
      <div class="spearman-card">
        <div class="spearman-label">{{key}}</div>
        <div class="spearman-val">{{stats['mean_rho']}}</div>
        <div style="font-size:0.75rem;color:#64748b;">n={{stats['n_queries']}} range=[{{stats['min_rho']}}, {{stats['max_rho']}}]</div>
      </div>
      % end
    </div>
    % end

    % if data.get('top3_overall_overlap'):
    <h3 style="margin-top:1rem;">Mean Top-3 Overlap</h3>
    <div class="spearman-grid">
      % for key, val in data['top3_overall_overlap'].items():
      <div class="spearman-card">
        <div class="spearman-label">{{key}}</div>
        <div class="spearman-val">{{val}}</div>
      </div>
      % end
    </div>
    % end
  </div>

  <!-- Per-query breakdown -->
  <h2>Per-Query Breakdown</h2>
  % for q in data.get('per_query', []):
  <div class="card">
    <div class="query-header" onclick="this.nextElementSibling.classList.toggle('open')">
      <span><strong>Query {{q['query_index']}}</strong> &mdash; Top-1: {{', '.join(f'{k}={v}' for k,v in q.get('top1_aids', {}).items())}}</span>
      <span style="font-size:0.8rem;color:#64748b;">&#x25BC;</span>
    </div>
    <div class="query-body open">

      <!-- Top-5 rankings table -->
      % if data.get('top_k_aids') and q['query_index'] in data['top_k_aids']:
      <h3>Top-5 Rankings</h3>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            % for name in data['targets']:
            <th>{{name}}</th>
            % end
          </tr>
        </thead>
        <tbody>
          % for rank in range(5):
          <tr>
            <td>{{rank + 1}}</td>
            % for name in data['targets']:
              % entry = data['top_k_aids'][q['query_index']].get(name, [{}] * 5)
              <td>
                % if rank < len(data['top_k_aids'][q['query_index']].get(name, [])):
                  {{data['top_k_aids'][q['query_index']][name][rank].get('aid', '')}}
                  <span style="color:#64748b;font-size:0.8rem;">({{data['top_k_aids'][q['query_index']][name][rank].get('score', '')}})</span>
                % end
              </td>
            % end
          </tr>
          % end
        </tbody>
      </table>
      % end

      <!-- Spearman -->
      % if q.get('spearman_pairs'):
      <h3>Spearman Correlation</h3>
      <div class="spearman-grid" style="margin-top:0.5rem;">
        % for pair in q['spearman_pairs']:
        <div class="spearman-card">
          <div class="spearman-label">{{pair['a']}} vs {{pair['b']}}</div>
          <div class="spearman-val {{'pass-val' if pair.get('rho') and pair['rho'] > 0.95 else 'warn-val'}}">{{f'{pair[\"rho\"]:.4f}' if pair.get('rho') is not None else 'N/A'}}</div>
        </div>
        % end
      </div>
      % end

      <!-- Score distribution -->
      % if q.get('score_stats'):
      <h3>Score Distribution</h3>
      <table>
        <thead>
          <tr>
            <th>Target</th>
            <th>Min</th>
            <th>Max</th>
            <th>Mean</th>
            <th>Std</th>
            <th>N</th>
          </tr>
        </thead>
        <tbody>
          % for name, stats in q['score_stats'].items():
          <tr>
            <td><strong>{{name}}</strong></td>
            <td>{{stats.get('min', '')}}</td>
            <td>{{stats.get('max', '')}}</td>
            <td>{{stats.get('mean', '')}}</td>
            <td>{{stats.get('std', '')}}</td>
            <td>{{stats.get('n', stats.get('count', ''))}}</td>
          </tr>
          % end
        </tbody>
      </table>
      % end

      <!-- Score bars -->
      % for name in data['targets']:
      % tk = data.get('top_k_aids', {}).get(q['query_index'], {}).get(name, [])
      % if tk:
      <h3>{{name}} Scores (bar)</h3>
      % max_score = max(s.get('score', 0) for s in tk) or 1
      <div class="score-chart">
        % for s in tk:
        <div class="score-bar" style="height: {{int(50 * s['score'] / max_score) + 5}}px;" title="{{s['aid']}}: {{s['score']}}"></div>
        % end
      </div>
      % end
      % end

      <!-- Top-3 overlap matrix -->
      % if q.get('top3_overlap'):
      <h3>Top-3 Overlap Matrix</h3>
      <table>
        <thead>
          <tr>
            <th>A &#x2192; B</th>
            % for name in data['targets']:
            <th>{{name}}</th>
            % end
          </tr>
        </thead>
        <tbody>
          % for a_name in data['targets']:
          <tr>
            <td><strong>{{a_name}}</strong></td>
            % for b_name in data['targets']:
            <td>{{q['top3_overlap'].get(a_name, {}).get(b_name, '-')}}</td>
            % end
          </tr>
          % end
        </tbody>
      </table>
      % end

    </div>
  </div>
  % end

  <!-- Errors -->
  % if data.get('errors'):
  <h2>Errors</h2>
  <div class="card">
    <ul class="error-list">
      % for e in data['errors']:
      <li>[{{e.get('target', '?')}}] query {{e.get('query_index', '?')}}: {{e.get('message', e)}}</li>
      % end
    </ul>
  </div>
  % end

</div>
<script>
// Collapsible query sections
document.querySelectorAll('.query-header').forEach(h => {
  h.addEventListener('click', () => {
    h.nextElementSibling.classList.toggle('open');
  });
});
</script>
</body>
</html>
"""

_ERROR_TPL = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Error</title>
<style>
body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background: #0f172a; color: #e2e8f0; line-height: 1.6; padding: 2rem; }
a { color: #818cf8; text-decoration: none; }
.error { background: #7f1d1d; border: 1px solid #991b1b; border-radius: 10px; padding: 1.5rem; margin-top: 1rem; }
</style>
</head>
<body>
  <a href="/">&larr; Back</a>
  <div class="error">
    <h2>{{message}}</h2>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parity benchmark web viewer")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"Starting parity benchmark viewer at http://{args.host}:{args.port}/")
    run(host=args.host, port=args.port, debug=args.debug, reloader=args.debug)


if __name__ == "__main__":
    main()
