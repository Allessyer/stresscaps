"""
Build a self-contained HTML page to inspect the antibenchmark.

Layout: one wide table where each row is a single (original caption, modified
caption) pair tagged with its transformation type and label. Filter by label,
type, flag, or free-text search. The `n_samples` parameter / `--n-samples`
CLI flag controls how many rows are baked into the HTML — useful for keeping
the file small when you just want a quick spot-check.

Usage:
    python build_viewer.py --input antibenchmark_qwen3omni.jsonl --output qwen3omni_viewer.html --n-samples 500
"""

from __future__ import annotations

import argparse
import html
import json
import random
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from prompts.negative_prompts import NEGATIVE_PROMPTS
from prompts.positive_prompts import POSITIVE_PROMPTS 


POSITIVE_TYPES = list(POSITIVE_PROMPTS.keys())
NEGATIVE_TYPES = list(NEGATIVE_PROMPTS.keys())

ALL_TYPES = POSITIVE_TYPES + NEGATIVE_TYPES
TYPE_TO_LABEL = {
                 **{t: "positive" for t in POSITIVE_TYPES},
                 **{t: "negative" for t in NEGATIVE_TYPES}
                 }


# ---------------------------------------------------------------------------
# Quality flags — same set as before; surfaces the LLM failure modes that
# actually happen with rewritten captions
# ---------------------------------------------------------------------------
def _normalize(s: str) -> str:
    return " ".join(s.lower().split())


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def compute_flags(original: str, modified: str | None, mod_type: str,
                  label: str, error: str | None) -> list[str]:
    flags: list[str] = []

    if error or modified is None:
        flags.append("parse_failed")
        return flags

    mod = modified.strip()
    if not mod:
        flags.append("empty")
        return flags

    if _normalize(mod) == _normalize(original):
        flags.append("identical")

    sim = _similarity(original, mod)
    if "identical" not in flags and sim >= 0.95:
        flags.append("near_duplicate")

    o_words = max(1, len(original.split()))
    m_words = len(mod.split())
    ratio = m_words / o_words
    if mod_type != "shorter" and ratio < 0.3:
        flags.append("too_short")
    if mod_type != "longer" and ratio > 2.5:
        flags.append("too_long")

    if label == "negative":
        # A negative that's still near-identical is suspicious; same_words_wrong_meaning
        # is allowed to share vocabulary, so skip it there.
        if mod_type != "same_words_wrong_meaning" and sim > 0.75 and "identical" not in flags:
            flags.append("negative_too_similar")
    else:
        # Vocab-preserving positives shouldn't drift far from the original.
        vocab_preserving = {
            "synonyms", "grammar", "past_tense", "present_continuous",
            "present_simple", "active_voice", "passive_voice",
        }
        if mod_type in vocab_preserving and sim < 0.4:
            flags.append("positive_low_overlap")

    return flags


# ---------------------------------------------------------------------------
# Word-level diff (used by the "show diff" toggle)
# ---------------------------------------------------------------------------
def make_diff_html(original: str, modified: str) -> str:
    a = original.split()
    b = modified.split()
    sm = SequenceMatcher(None, a, b)
    out: list[str] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(html.escape(" ".join(b[j1:j2])))
        elif tag == "replace":
            if a[i1:i2]:
                out.append(f'<span class="diff-del">{html.escape(" ".join(a[i1:i2]))}</span>')
            if b[j1:j2]:
                out.append(f'<span class="diff-add">{html.escape(" ".join(b[j1:j2]))}</span>')
        elif tag == "delete":
            out.append(f'<span class="diff-del">{html.escape(" ".join(a[i1:i2]))}</span>')
        elif tag == "insert":
            out.append(f'<span class="diff-add">{html.escape(" ".join(b[j1:j2]))}</span>')
    return " ".join(p for p in out if p)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_records(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def select_rows(records: list[dict[str, Any]], n_samples: int | None,
                sample_strategy: str, seed: int) -> list[dict[str, Any]]:
    """Pick which (caption, modification) rows go into the viewer.

    * "stratified" — keep roughly equal counts per modification type. Best for
      auditing: you see each transformation a balanced number of times.
    * "random" — uniform random sample across all rows.
    * "first" — take the first n_samples in file order (cheap, deterministic).
    """
    if n_samples is None or n_samples <= 0 or n_samples >= len(records):
        return list(records)

    if sample_strategy == "first":
        return records[:n_samples]

    rng = random.Random(seed)

    if sample_strategy == "random":
        return rng.sample(records, n_samples)

    # stratified: split per modification_type, then round-robin
    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_type.setdefault(r["modification_type"], []).append(r)
    for v in by_type.values():
        rng.shuffle(v)

    # Round-robin pull: ensures the first 15 rows touch each type once,
    # so even very small n_samples gives full coverage.
    types_in_order = [t for t in ALL_TYPES if t in by_type]
    out: list[dict[str, Any]] = []
    cursor = {t: 0 for t in types_in_order}
    while len(out) < n_samples:
        progressed = False
        for t in types_in_order:
            if cursor[t] < len(by_type[t]):
                out.append(by_type[t][cursor[t]])
                cursor[t] += 1
                progressed = True
                if len(out) >= n_samples:
                    break
        if not progressed:
            break
    return out


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------
CSS = """
:root {
    --bg: #fafafa;
    --card: #ffffff;
    --border: #e2e2e2;
    --text: #1a1a1a;
    --muted: #6b7280;
    --pos: #10b981;
    --pos-bg: #ecfdf5;
    --neg: #ef4444;
    --neg-bg: #fef2f2;
    --flag-bg: #fef3c7;
    --flag-border: #f59e0b;
    --flag-text: #92400e;
    --diff-add-bg: #d1fae5;
    --diff-add-text: #065f46;
    --diff-del-bg: #fee2e2;
    --diff-del-text: #991b1b;
    --row-hover: #f9fafb;
}
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 24px;
    line-height: 1.5;
}
header { max-width: 1400px; margin: 0 auto 16px; }
h1 { margin: 0 0 4px; font-size: 22px; }
.subtitle { color: var(--muted); font-size: 13px; margin-bottom: 16px; }
.controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
    position: sticky;
    top: 0;
    z-index: 10;
}
.controls label {
    font-size: 13px;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 6px;
}
.controls select, .controls input {
    font-size: 13px;
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: white;
    color: var(--text);
}
.controls input[type="text"] { min-width: 220px; }
.controls button {
    font-size: 12px;
    padding: 4px 10px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: white;
    cursor: pointer;
    color: var(--text);
}
.controls button:hover { background: var(--row-hover); }
.controls button.active { background: var(--text); color: white; border-color: var(--text); }
.stats { margin-left: auto; font-size: 13px; color: var(--muted); }

main { max-width: 1400px; margin: 0 auto; }

table {
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}
thead { background: #f3f4f6; }
th {
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    padding: 10px 14px;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
}
td {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
    font-size: 14px;
}
tr.row:hover td { background: var(--row-hover); }
tr.hidden { display: none; }

.col-num     { width: 56px;  color: var(--muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 12px; }
.col-label   { width: 84px; }
.col-type    { width: 180px; }
.col-flags   { width: 160px; }
.col-orig, .col-mod { width: 38%; }

.badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 10px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.badge-positive { background: var(--pos-bg); color: var(--pos); border: 1px solid var(--pos); }
.badge-negative { background: var(--neg-bg); color: var(--neg); border: 1px solid var(--neg); }
.type-tag {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 12px;
    color: var(--text);
}

.flag {
    display: inline-block;
    background: var(--flag-bg);
    border: 1px solid var(--flag-border);
    color: var(--flag-text);
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 600;
    margin: 1px 2px 1px 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.mod-failed { color: var(--muted); font-style: italic; }
.raw-preview { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; color: var(--muted); }

.diff-add { background: var(--diff-add-bg); color: var(--diff-add-text); padding: 1px 2px; border-radius: 2px; }
.diff-del { background: var(--diff-del-bg); color: var(--diff-del-text); padding: 1px 2px; border-radius: 2px; text-decoration: line-through; }

/* Diff toggle: by default show plain, hide diff. When body has .show-diff, swap. */
.mod-plain { display: inline; }
.mod-diff  { display: none; }
body.show-diff .mod-plain { display: none; }
body.show-diff .mod-diff  { display: inline; }

.empty-state {
    text-align: center;
    color: var(--muted);
    padding: 60px 20px;
    font-size: 14px;
}
.hidden { display: none !important; }
"""


JS = """
const rows = document.querySelectorAll('tr.row');
const filterLabel = document.getElementById('filter-label');
const filterType = document.getElementById('filter-type');
const filterFlag = document.getElementById('filter-flag');
const searchBox = document.getElementById('search');
const statsEl = document.getElementById('stats');
const emptyState = document.getElementById('empty-state');
const diffToggle = document.getElementById('toggle-diff');

function applyFilters() {
    const label = filterLabel.value;
    const type = filterType.value;
    const flag = filterFlag.value;
    const q = searchBox.value.trim().toLowerCase();

    let visible = 0;
    rows.forEach(row => {
        const rLabel = row.dataset.label;
        const rType  = row.dataset.type;
        const rFlags = (row.dataset.flags || '').split(',').filter(Boolean);
        const rSearch = row.dataset.search || '';

        let show = true;
        if (label !== 'all' && rLabel !== label) show = false;
        if (type !== 'all' && rType !== type) show = false;
        if (flag === 'any' && rFlags.length === 0) show = false;
        else if (flag !== 'all' && flag !== 'any' && !rFlags.includes(flag)) show = false;
        if (q && !rSearch.includes(q)) show = false;

        row.classList.toggle('hidden', !show);
        if (show) visible++;
    });

    statsEl.textContent = `${visible} / ${rows.length} rows visible`;
    emptyState.classList.toggle('hidden', visible > 0);
}

[filterLabel, filterType, filterFlag].forEach(el => el.addEventListener('change', applyFilters));
searchBox.addEventListener('input', applyFilters);

diffToggle.addEventListener('click', () => {
    document.body.classList.toggle('show-diff');
    diffToggle.classList.toggle('active');
    diffToggle.textContent = document.body.classList.contains('show-diff') ? 'plain text' : 'show diff';
});

// Keyboard shortcut: '/' focuses the search box.
document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        searchBox.focus();
    }
});

applyFilters();
"""


def render_row(i: int, record: dict[str, Any]) -> str:
    """Render one table row for a single (original, modified) pair."""
    original = record.get("original_caption", "")
    modified = record.get("modified_caption")
    mod_type = record.get("modification_type", "")
    label = record.get("label") or TYPE_TO_LABEL.get(mod_type, "")
    error = record.get("error")
    raw = record.get("raw_response") or ""

    flags = compute_flags(original, modified, mod_type, label, error)

    if modified:
        mod_plain = html.escape(modified)
        mod_diff = make_diff_html(original, modified)
        mod_cell = (
            f'<span class="mod-plain">{mod_plain}</span>'
            f'<span class="mod-diff">{mod_diff}</span>'
        )
        search_text = (original + " " + modified).lower()
    else:
        # Failure case: show the truncated raw response if we have it, otherwise
        # the error string. Either way the user can see *why* this row is empty.
        if raw:
            preview = raw[:240].replace("\n", " ")
            mod_cell = (
                f'<span class="mod-failed">(parse failed) '
                f'<span class="raw-preview">{html.escape(preview)}'
                f'{"..." if len(raw) > 240 else ""}</span></span>'
            )
        else:
            mod_cell = f'<span class="mod-failed">{html.escape(error or "(empty)")}</span>'
        search_text = original.lower()

    flags_html = "".join(f'<span class="flag">{html.escape(f)}</span>' for f in flags)
    badge_class = "badge-positive" if label == "positive" else "badge-negative"

    return (
        f'<tr class="row" data-label="{label}" data-type="{html.escape(mod_type)}" '
        f'data-flags="{html.escape(",".join(flags))}" '
        f'data-search="{html.escape(search_text)}">'
        f'<td class="col-num">{i}</td>'
        f'<td class="col-label"><span class="badge {badge_class}">{label}</span></td>'
        f'<td class="col-type"><span class="type-tag">{html.escape(mod_type)}</span></td>'
        f'<td class="col-orig">{html.escape(original)}</td>'
        f'<td class="col-mod">{mod_cell}</td>'
        f'<td class="col-flags">{flags_html}</td>'
        f'</tr>'
    )


def build_html(records: list[dict[str, Any]]) -> str:
    # Filter dropdown contents derived from what's actually in the data
    types_present = [t for t in ALL_TYPES if any(r["modification_type"] == t for r in records)]
    all_flags: set[str] = set()
    n_pos = n_neg = n_flagged = 0
    for r in records:
        mod_type = r["modification_type"]
        label = r.get("label") or TYPE_TO_LABEL.get(mod_type, "")
        if label == "positive":
            n_pos += 1
        elif label == "negative":
            n_neg += 1
        f = compute_flags(r["original_caption"], r.get("modified_caption"),
                          mod_type, label, r.get("error"))
        if f:
            n_flagged += 1
        all_flags.update(f)

    type_options = ['<option value="all">all types</option>']
    if any(t in POSITIVE_TYPES for t in types_present):
        type_options.append('<optgroup label="positive">')
        for t in POSITIVE_TYPES:
            if t in types_present:
                type_options.append(f'<option value="{t}">{t}</option>')
        type_options.append('</optgroup>')
    if any(t in NEGATIVE_TYPES for t in types_present):
        type_options.append('<optgroup label="negative">')
        for t in NEGATIVE_TYPES:
            if t in types_present:
                type_options.append(f'<option value="{t}">{t}</option>')
        type_options.append('</optgroup>')

    flag_options = [
        '<option value="all">all (no filter)</option>',
        '<option value="any">any flag</option>',
    ]
    flag_options += [f'<option value="{f}">{f}</option>' for f in sorted(all_flags)]

    rows_html = "\n".join(render_row(i + 1, r) for i, r in enumerate(records))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Antibenchmark viewer</title>
<style>{CSS}</style>
</head>
<body>
<header>
    <h1>Antibenchmark viewer</h1>
    <div class="subtitle">
        {len(records)} rows · {n_pos} positive · {n_neg} negative · {n_flagged} flagged
    </div>
    <div class="controls">
        <label>label
            <select id="filter-label">
                <option value="all">all</option>
                <option value="positive">positive</option>
                <option value="negative">negative</option>
            </select>
        </label>
        <label>type
            <select id="filter-type">{"".join(type_options)}</select>
        </label>
        <label>flag
            <select id="filter-flag">{"".join(flag_options)}</select>
        </label>
        <label>search
            <input type="text" id="search" placeholder="filter text...  (press /)">
        </label>
        <button id="toggle-diff" title="Highlight word-level changes">show diff</button>
        <span class="stats" id="stats"></span>
    </div>
</header>
<main>
<table>
<thead>
<tr>
<th class="col-num">#</th>
<th class="col-label">Label</th>
<th class="col-type">Type</th>
<th class="col-orig">Original Caption</th>
<th class="col-mod">Modified Caption</th>
<th class="col-flags">Flags</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
<div id="empty-state" class="empty-state hidden">No rows match the current filters.</div>
</main>
<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def build_viewer(input_path: str | Path,
                 output_path: str | Path,
                 n_samples: int | None = None,
                 sample_strategy: str = "stratified",
                 seed: int = 0) -> Path:
    """Build the HTML viewer from a JSONL of antibenchmark records.

    Args:
        input_path: Path to the JSONL produced by generate_antibenchmark.py.
        output_path: Where to write the single-file HTML viewer.
        n_samples: How many rows to include. None or <=0 means "all". Smaller
            values keep the HTML file lean for quick spot-checks.
        sample_strategy: One of "stratified" (balanced per modification type),
            "random" (uniform), or "first" (file order).
        seed: RNG seed for reproducible sampling.

    Returns:
        The output path as a Path object.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    all_records = load_records(input_path)
    if not all_records:
        raise ValueError(f"No records read from {input_path}")

    selected = select_rows(all_records, n_samples, sample_strategy, seed)
    print(f"[select] {len(all_records)} total rows -> {len(selected)} selected "
          f"({sample_strategy})")

    html_text = build_html(selected)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    print(f"[ok] wrote {output_path}")
    return output_path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="antibenchmark.jsonl",
                   help="JSONL produced by generate_antibenchmark.py")
    p.add_argument("--output", default="viewer.html",
                   help="HTML file to write")
    p.add_argument("--n-samples", type=int, default=0,
                   help="Number of rows to include in the viewer. 0 = all.")
    p.add_argument("--sample-strategy", default="stratified",
                   choices=["stratified", "random", "first"],
                   help="How to pick rows when --n-samples < total. "
                        "stratified = balanced per modification type.")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    n = args.n_samples if args.n_samples > 0 else None
    build_viewer(args.input, args.output,
                 n_samples=n, sample_strategy=args.sample_strategy,
                 seed=args.seed)


if __name__ == "__main__":
    main()
