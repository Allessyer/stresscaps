"""
Antibenchmark dataset generator for audio captioning metrics.

For each original AudioCaps caption, produces multiple modified versions:
- Positive (semantics preserved): synonyms, shorter, longer, grammar, past, present_continuous,
  present_simple, active_voice, passive_voice
- Negative (semantics changed): missing_info, false_addition, hallucinations,
  same_words_wrong_meaning, contradiction, different_words_different_meaning

Outputs a JSONL file with one record per (caption_idx, modification_type).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from openai import OpenAI

from prompts.negative_prompts import NEGATIVE_PROMPTS
from prompts.positive_prompts import POSITIVE_PROMPTS   



# ---------------------------------------------------------------------------
# VLLM client
# ---------------------------------------------------------------------------
class VLLM_Model:
    def __init__(self, served_model_url: str, model_name: str) -> None:
        self.client = OpenAI(
            api_key="EMPTY",
            base_url=served_model_url,
            timeout=7200.0,
        )
        self.model = model_name

    def run_text_only(
        self,
        system_prompt: str = "",
        user_prompt: str = "",
        max_completion_tokens: int = 2048,
        temperature: float = 0.9,
    ) -> str:
        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            extra_body={
                "skip_special_tokens": False,
                "temperature": temperature,
                "seed": 1024,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            model=self.model,
            max_completion_tokens=max_completion_tokens,
        )
        return chat_completion.choices[0].message.content


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
# Notes:
#   * We force strict JSON output: {"modified_caption": "..."} so parsing is robust.
#   * Each prompt is highly specific: it tells the model exactly ONE transformation to apply.
#   * We give two short few-shot examples per type to anchor behavior.
#   * "Negative" prompts explicitly forbid synonym-only changes so that we get a real
#     semantic shift, not a paraphrase that the metric might still call equivalent.

SYSTEM_PROMPT_BASE = (
    "You are an expert linguistic editor working on an audio captioning benchmark. "
    "You receive a single original caption and a transformation instruction. "
    "You produce exactly one modified caption that follows the instruction. "
    "You must respond with a single JSON object: {\"modified_caption\": \"...\"} "
    "and nothing else. Do not include explanations, markdown, code fences, or thinking."
)

ALL_PROMPTS: dict[str, tuple[str, str]] = {
    # type -> (label, template) where label is "positive" or "negative"
    **{k: ("positive", v) for k, v in POSITIVE_PROMPTS.items()},
    # **{k: ("negative", v) for k, v in NEGATIVE_PROMPTS.items()},
}


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------
_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _to_jsonable(value: Any) -> Any:
    """Coerce numpy/pandas scalars (int64, float64, bool_, NaT, NaN) into native Python.

    Pandas/numpy scalar types are not handled by the stdlib JSON encoder, which is
    where you get errors like 'Object of type int64 is not JSON serializable'.
    """
    if value is None:
        return None
    # pandas NA / NaT / NaN
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        # pd.isna raises on some array-likes / non-scalars — fall through
        pass
    # numpy scalar -> python scalar
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


def parse_response(raw: str) -> str | None:
    """Extract the modified caption from an LLM response.

    Strategy:
      1. Try strict json.loads on the whole response.
      2. Fall back to the first {...} block.
      3. Strip code fences if present.
    """
    if raw is None:
        return None
    text = raw.strip()

    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Try direct parse
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "modified_caption" in obj:
            val = obj["modified_caption"]
            if isinstance(val, str) and val.strip():
                return val.strip()
    except json.JSONDecodeError:
        pass

    # Try first {...} block
    match = _JSON_RE.search(text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict) and "modified_caption" in obj:
                val = obj["modified_caption"]
                if isinstance(val, str) and val.strip():
                    return val.strip()
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
@dataclass
class Sample:
    idx: int               # row index in dataset
    audiocap_id: Any       # original id if available, else None
    # audio: Any             # original audio bytes
    original: str          # original caption
    mod_type: str          # e.g. "synonyms", "contradiction"
    label: str             # "positive" or "negative"


# These are populated per-worker in init_worker so we don't re-create the client
# on every call (which is what would happen if we did it inside send_prompt).
_WORKER_MODEL: VLLM_Model | None = None
_WORKER_TEMPERATURE: float = 0.9
_WORKER_MAX_TOKENS: int = 512
_WORKER_MAX_RETRIES: int = 3


def init_worker(served_model_url: str, model_name: str,
                temperature: float, max_tokens: int, max_retries: int) -> None:
    global _WORKER_MODEL, _WORKER_TEMPERATURE, _WORKER_MAX_TOKENS, _WORKER_MAX_RETRIES
    _WORKER_MODEL = VLLM_Model(served_model_url=served_model_url, model_name=model_name)
    _WORKER_TEMPERATURE = temperature
    _WORKER_MAX_TOKENS = max_tokens
    _WORKER_MAX_RETRIES = max_retries


def send_prompt(sample: Sample) -> dict[str, Any]:
    """Run one (caption, modification_type) request through the LLM."""
    assert _WORKER_MODEL is not None, "Worker not initialized"

    _, template = ALL_PROMPTS[sample.mod_type]
    user_prompt = template.format(caption=sample.original)

    last_error: str | None = None
    modified: str | None = None
    raw: str = ""

    for attempt in range(_WORKER_MAX_RETRIES):
        try:
            raw = _WORKER_MODEL.run_text_only(
                system_prompt=SYSTEM_PROMPT_BASE,
                user_prompt=user_prompt,
                max_completion_tokens=_WORKER_MAX_TOKENS,
                temperature=_WORKER_TEMPERATURE,
            )
            modified = parse_response(raw)
            if modified:
                break
            last_error = f"parse_failed: {raw[:200]!r}"
        except Exception as e:  # network, timeout, rate limit, etc.
            last_error = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)  # exponential backoff

    return {
        "idx": _to_jsonable(sample.idx),
        # "audio": sample.audio,
        "audiocap_id": _to_jsonable(sample.audiocap_id),
        "original_caption": sample.original,
        "modification_type": sample.mod_type,
        "label": sample.label,
        "modified_caption": modified,
        "raw_response": raw if modified is None else None,  # keep raw only on failure
        "error": last_error if modified is None else None,
    }


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------
def load_audiocaps_test(
    dataset_dir: str = "/cache/data/OpenSound-AudioCaps/data",
    split: str = "test",
    n: int | None = None,
    dedupe_by: str | None = None,
) -> pd.DataFrame:
    """Load AudioCaps from a directory of parquet shards.

    Expects files named like `test-00000-of-00001.parquet`, `train-*.parquet`, etc.
    Concatenates all shards for the given split.

    If `dedupe_by` is given (e.g. 'audiocap_id' or 'youtube_id'), keeps only the
    first caption per audio clip before truncating to n. This is useful because
    AudioCaps test has 5 captions per clip; without dedup, n=100 rows often
    means only ~20 unique clips.
    """
    dataset_path = Path(dataset_dir)
    if not dataset_path.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    shard_files = sorted(f for f in os.listdir(dataset_path) if f.startswith(split))
    if not shard_files:
        raise FileNotFoundError(
            f"No parquet shards starting with '{split}' in {dataset_dir}"
        )

    print(f"[load] reading {len(shard_files)} {split} shard(s) from {dataset_dir}")
    parts = [pd.read_parquet(dataset_path / f) for f in shard_files]
    df = pd.concat(parts, axis=0, ignore_index=True)

    if "caption" not in df.columns:
        raise ValueError(
            f"Dataset is missing 'caption' column. Columns: {list(df.columns)}"
        )

    if dedupe_by:
        if dedupe_by not in df.columns:
            print(f"[load] WARNING: dedupe column '{dedupe_by}' not found, "
                  f"available: {list(df.columns)} — skipping dedup")
        else:
            before = len(df)
            df = df.drop_duplicates(subset=[dedupe_by], keep="first").reset_index(drop=True)
            print(f"[load] dedup by '{dedupe_by}': {before} -> {len(df)} rows")

    if n is not None and n > 0:
        df = df.head(n)

    return df.reset_index(drop=True)


def build_samples(df: pd.DataFrame) -> list[Sample]:
    """Cartesian product of (rows, modification types)."""
    # Pick whatever id column the parquet happens to have.
    id_col: str | None = None
    for cand in ("audiocap_id", "audiocaps_id", "youtube_id", "ytid", "id"):
        if cand in df.columns:
            id_col = cand
            break

    samples: list[Sample] = []
    for idx in range(len(df)):
        row = df.iloc[idx]

        original = str(row["caption"]).strip()
        if not original:
            continue
        audiocap_id = row[id_col] if id_col else None
        audio = row["audio"]['bytes'] if "audio" in row else None
        for mod_type, (label, _) in ALL_PROMPTS.items():
            samples.append(Sample(
                idx=idx,
                # audio=audio,
                audiocap_id=audiocap_id,
                original=original,
                mod_type=mod_type,
                label=label,
            ))
    return samples


def load_done_keys(output_path: Path) -> set[tuple[int, str]]:
    """Read existing JSONL output (if any) and return the set of completed (idx, mod_type) keys.

    This makes the script resumable: re-running with the same --output skips work already done.
    """
    if not output_path.exists():
        return set()
    done: set[tuple[int, str]] = set()
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("modified_caption"):  # only count successful rows
                done.add((int(obj["idx"]), str(obj["modification_type"])))
    return done


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--served-model-url", required=True,
                   help="VLLM OpenAI-compatible base URL, e.g. http://localhost:8000/v1")
    p.add_argument("--model-name", required=True,
                   help="Model name registered in the VLLM server")
    p.add_argument("--dataset-dir", default="/cache/data/OpenSound-AudioCaps/data",
                   help="Directory of AudioCaps parquet shards "
                        "(files prefixed with split name, e.g. 'test-00000-of-00001.parquet').")
    p.add_argument("--split", default="test", choices=["test", "valid", "train"],
                   help="Which split's shards to load")
    p.add_argument("--n", type=int, default=100,
                   help="Number of original captions to process (use 0 or negative for all)")
    p.add_argument("--dedupe-by", default=None,
                   help="Optional column to dedupe rows by before truncating to --n "
                        "(e.g. 'audiocap_id' or 'youtube_id'). Useful because AudioCaps "
                        "test has 5 captions per clip.")
    p.add_argument("--processes", type=int, default=32, help="Parallel workers")
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--output", type=str, default="antibenchmark.jsonl")
    args = p.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[load] reading dataset (split={args.split}, n={args.n})...")
    n = args.n if args.n and args.n > 0 else None
    df = load_audiocaps_test(args.dataset_dir, split=args.split, n=n,
                             dedupe_by=args.dedupe_by)
    print(f"[load] got {len(df)} rows")

    all_samples = build_samples(df)
    done = load_done_keys(output_path)
    samples = [s for s in all_samples if (s.idx, s.mod_type) not in done]
    print(f"[plan] total samples={len(all_samples)} | done={len(done)} | to_run={len(samples)}")

    if not samples:
        print("[done] nothing to do")
        return

    t0 = time.time()
    n_ok = 0
    n_fail = 0

    # Open in append mode so we never lose past work.
    with output_path.open("a", encoding="utf-8") as out_f, \
         mp.Pool(
             processes=args.processes,
             initializer=init_worker,
             initargs=(args.served_model_url, args.model_name,
                       args.temperature, args.max_tokens, args.max_retries),
         ) as pool:

        # imap_unordered streams results as they finish — much better than .map for
        # progress reporting and incremental persistence.
        for i, result in enumerate(pool.imap_unordered(send_prompt, samples, chunksize=1), start=1):
            out_f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
            out_f.flush()
            if result["modified_caption"]:
                n_ok += 1
            else:
                n_fail += 1

            if i % 25 == 0 or i == len(samples):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed > 0 else 0.0
                eta = (len(samples) - i) / rate if rate > 0 else float("inf")
                print(f"[progress] {i}/{len(samples)}  ok={n_ok} fail={n_fail}  "
                      f"rate={rate:.2f}/s  eta={eta/60:.1f}min", flush=True)

    print(f"[done] wrote {n_ok} successful and {n_fail} failed records to {output_path}")


if __name__ == "__main__":
    # On Linux the default 'fork' start method works fine; on macOS/Windows 'spawn'
    # is safer because the OpenAI client holds open sockets.
    try:
        mp.set_start_method("spawn", force=False)
    except RuntimeError:
        pass
    main()
