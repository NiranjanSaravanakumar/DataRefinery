"""
DataRefinery — Report Generation Service
==========================================
Generates a self-contained, styled HTML report from the web_summary dict
produced by CleaningService. The output is a single HTML file that can be
opened in any browser without any external dependencies.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any


class ReportService:
    """Generates downloadable HTML reports from pipeline summary data."""

    @staticmethod
    def generate_html(summary: dict[str, Any]) -> str:
        """
        Render a complete, self-contained HTML report.

        Args:
            summary: The web_summary dict from CleaningService.process().

        Returns:
            A string containing the full HTML document.
        """
        score = summary.get("pipeline_score", 0)
        score_color = (
            "#22c55e"
            if score >= 90
            else "#f59e0b" if score >= 70 else "#ef4444" if score >= 50 else "#dc2626"
        )
        score_grade = (
            "Excellent"
            if score >= 90
            else "Good" if score >= 70 else "Fair" if score >= 50 else "Poor"
        )

        # Build issues table rows
        issues_html = ""
        for field, entries in summary.get("issues_by_field", {}).items():
            for e in entries:
                badge = (
                    '<span class="badge badge-high">HIGH</span>'
                    if e["severity"] == "high"
                    else '<span class="badge badge-medium">MEDIUM</span>'
                )
                issues_html += f"""
                <tr>
                    <td>{html.escape(str(e['row_number']))}</td>
                    <td>{html.escape(str(e['order_id']))}</td>
                    <td><code>{html.escape(str(field))}</code></td>
                    <td>{badge}</td>
                    <td>{html.escape(str(e['message']))}</td>
                </tr>"""

        # Status counts rows
        status_rows = ""
        for status, count in summary.get("status_counts", {}).items():
            status_rows += f"<tr><td>{html.escape(str(status))}</td><td>{html.escape(str(count))}</td></tr>"

        timestamp = html.escape(
            str(summary.get("timestamp", datetime.now(timezone.utc).isoformat()))
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DataRefinery Pipeline Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f172a; color: #e2e8f0; padding: 2rem;
      line-height: 1.6;
    }}
    .container {{ max-width: 960px; margin: 0 auto; }}
    header {{ margin-bottom: 2rem; border-bottom: 1px solid #334155; padding-bottom: 1rem; }}
    h1 {{ font-size: 2rem; color: #a78bfa; }}
    h2 {{ font-size: 1.25rem; color: #c4b5fd; margin: 1.5rem 0 0.75rem; }}
    .meta {{ color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin: 1rem 0; }}
    .card {{
      background: #1e293b; border: 1px solid #334155; border-radius: 12px;
      padding: 1.25rem; text-align: center;
    }}
    .card .value {{ font-size: 2rem; font-weight: 700; color: #a78bfa; }}
    .card .label {{ font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }}
    .score-block {{
      background: #1e293b; border: 2px solid {score_color};
      border-radius: 16px; padding: 1.5rem; text-align: center; margin: 1rem 0;
    }}
    .score-num {{ font-size: 4rem; font-weight: 800; color: {score_color}; }}
    .score-grade {{ font-size: 1.1rem; color: {score_color}; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.875rem; }}
    th {{ background: #1e293b; color: #a78bfa; text-align: left; padding: 0.6rem 0.75rem; border-bottom: 2px solid #334155; }}
    td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #1e293b; }}
    tr:nth-child(even) td {{ background: #0f172a; }}
    code {{ background: #334155; padding: 0.1em 0.4em; border-radius: 4px; font-family: monospace; }}
    .badge {{ display: inline-block; padding: 0.2em 0.6em; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }}
    .badge-high {{ background: #fee2e2; color: #dc2626; }}
    .badge-medium {{ background: #fef3c7; color: #d97706; }}
    footer {{ margin-top: 3rem; color: #475569; font-size: 0.8rem; border-top: 1px solid #1e293b; padding-top: 1rem; }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>🔧 DataRefinery — Pipeline Report</h1>
    <p class="meta">File: <strong>{summary.get('filename', 'N/A')}</strong> &nbsp;|&nbsp; Generated: {timestamp}</p>
  </header>

  <h2>Pipeline Quality Score</h2>
  <div class="score-block">
    <div class="score-num">{score}<span style="font-size:1.5rem; color:#94a3b8">/100</span></div>
    <div class="score-grade">{score_grade}</div>
  </div>

  <h2>Before &amp; After Summary</h2>
  <div class="grid">
    <div class="card"><div class="value">{summary.get('rows_before', 0)}</div><div class="label">Rows (Input)</div></div>
    <div class="card"><div class="value">{summary.get('rows_after', 0)}</div><div class="label">Rows (Clean)</div></div>
    <div class="card"><div class="value">{summary.get('rejected_records', 0)}</div><div class="label">Rows Rejected</div></div>
    <div class="card"><div class="value">{summary.get('cols_before', 0)}</div><div class="label">Cols (Input)</div></div>
    <div class="card"><div class="value">{summary.get('cols_after', 0)}</div><div class="label">Cols (Output)</div></div>
    <div class="card"><div class="value">{summary.get('total_issues', 0)}</div><div class="label">Total Issues</div></div>
    <div class="card"><div class="value">{summary.get('duplicate_rows_removed', 0)}</div><div class="label">Duplicates</div></div>
  </div>

  <h2>Orders by Status</h2>
  <table>
    <tr><th>Status</th><th>Count</th></tr>
    {status_rows if status_rows else '<tr><td colspan="2">No data</td></tr>'}
  </table>

  <h2>Validation Issues Log</h2>
  <table>
    <tr><th>Row</th><th>Order ID</th><th>Field</th><th>Severity</th><th>Message</th></tr>
    {issues_html if issues_html else '<tr><td colspan="5">No issues found — perfect data!</td></tr>'}
  </table>

  <footer>
    <p>Generated by DataRefinery v{summary.get('version', '2.0.0')} &nbsp;·&nbsp; {timestamp}</p>
  </footer>
</div>
</body>
</html>"""
