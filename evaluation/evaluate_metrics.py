#!/usr/bin/env python
"""
evaluate_antibench.py
=====================

Run every audio-captioning metric over your antibench dataset and report:
  1. per-item scores  (saved to JSONL + CSV)
  2. corpus-level scores
  3. per-(label, modification_type) failure rates, where:
        - "positive" item fails if metric score < threshold  (metric missed a true match)
        - "negative" item fails if metric score > threshold  (metric got fooled)

Input JSONL fields used:
    original_caption  -> reference
    modified_caption  -> candidate
    label             -> "positive" | "negative"
    modification_type -> bucket (e.g. "paraphrase", ...)
    audiocap_id       -> used as a cache key for audio
    audio             -> (optional) raw audio for this row, in any of these shapes:
                            * a string that is repr() of bytes, e.g. "b'RIFF\\x24\\x08...'"
                              (parsed via ast.literal_eval — this is the shape produced by
                              `str(audio_bytes)` and consumed by
                              `audio_bytes = ast.literal_eval(row['audio'])`)
                            * base64-encoded string (optionally with a "data:audio/...;base64," prefix)
                            * hex string
                            * list[int] of byte values
                            * dict with one of {"bytes": ..., "b64": ..., "data": ..., "path": ...}
                          aac-metrics' CLAP-sim / MACE expect file PATHS, so audio bytes
                          are decoded once per row to a temp file and reused across metrics.
                          Alternatively, --audio-dir <dir> + --audio-ext can be used to
                          resolve audio files by audiocap_id.

Usage
-----
    # text-only metrics
    python evaluate_antibench.py --input antibench.jsonl --output-dir results/

    # with audio bytes embedded in the JSONL (auto-detected)
    python evaluate_antibench.py --input antibench.jsonl --output-dir results/

    # with audio files on disk
    python evaluate_antibench.py --input antibench.jsonl --output-dir results/ \
        --audio-dir /path/to/audiocaps_wavs --audio-ext .wav

Notes
-----
* BLEU/ROUGE/METEOR/CIDEr/SPICE/SPIDEr/BERTScore work text-only.
* FENSE / FER / SBERT-sim / SPIDEr-FL work text-only and use a pretrained SBERT.
* CLAP-sim and MACE require audio waveforms.
* All metrics here are PER-PAIR: 1 reference, 1 candidate. That's the right setup
  for antibench probing — you want to see how each metric reacts to a controlled
  perturbation between two strings.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from tqdm import tqdm


# --------------------------------------------------------------------------- #
# 1. Metric registry
# --------------------------------------------------------------------------- #
# Map metric name -> (loader_fn, needs_audio)
# Loader returns an *instance* with .__call__(cands, mult_refs) -> (corpus, sents)
#
# Note on what's *not* here:
#   - SPICE, SPIDEr, SPIDEr-FL  — require Stanford CoreNLP via Java; not ARM-friendly.
#   - BERTScore                 — present in earlier versions; drop here since not in
#                                 the target metric list.
#   - METEOR                    — needs Java (the METEOR jar). Kept in registry; if the
#                                 jar fails on this host, the try/except will skip it
#                                 without affecting the others.
def build_metric_registry(
    device: str,
    *,
    java_max_memory: str = "2G",
    java_path: str | None = None,
) -> dict[str, tuple[Any, bool]]:
    from aac_metrics.classes.bleu import BLEU
    from aac_metrics.classes.rouge_l import ROUGEL
    from aac_metrics.classes.meteor import METEOR
    from aac_metrics.classes.cider_d import CIDErD
    from aac_metrics.classes.fense import FENSE
    from aac_metrics.classes.fer import FER
    from aac_metrics.classes.sbert_sim import SBERTSim
    from aac_metrics.classes.vocab import Vocab

    java_kw = {"java_max_memory": java_max_memory}
    if java_path:
        java_kw["java_path"] = java_path

    # Single BLEU loader shared by 5 logical names (bleu, bleu_1..4). The
    # grouping in run() identifies physical runs by `is`-identity of this
    # loader object, so the same loader => one BLEU call.
    _bleu_loader = lambda: BLEU(return_all_scores=True, n=4, return_1_to_n=True)

    registry: dict[str, tuple[Any, bool]] = {
        # BLEU-1..4 + the standard "bleu" geometric-mean number all from one BLEU run.
        # The score_key column in PRIMARY_SENT_KEY routes each metric name to the right
        # output key. return_1_to_n=True is what makes BLEU expose bleu_1..bleu_n.
        "bleu":       (_bleu_loader, False),
        "bleu_1":     (_bleu_loader, False),
        "bleu_2":     (_bleu_loader, False),
        "bleu_3":     (_bleu_loader, False),
        "bleu_4":     (_bleu_loader, False),
        "rouge_l":    (lambda: ROUGEL(return_all_scores=True), False),
        "meteor":     (lambda: METEOR(return_all_scores=True, **java_kw), False),
        "cider_d":    (lambda: CIDErD(return_all_scores=True), False),
        "sbert_sim":  (lambda: SBERTSim(return_all_scores=True, device=device), False),
        "fer":        (lambda: FER(return_all_scores=True, device=device), False),
        "fense":      (lambda: FENSE(return_all_scores=True, device=device), False),
        "vocab":      (lambda: Vocab(return_all_scores=True), False),
    }

    # Optional audio-dependent metrics
    try:
        from aac_metrics.classes.clap_sim import CLAPSim
        from aac_metrics.classes.mace import MACE
        registry["clap_sim"] = (lambda: CLAPSim(return_all_scores=True, device=device), True)
        registry["mace"]     = (lambda: MACE(return_all_scores=True, device=device), True)
    except Exception as e:
        print(f"[info] CLAP-sim / MACE unavailable: {e}", file=sys.stderr)

    return registry


# Where a "good" positive should score HIGH and a "good" negative should score LOW.
# Used to decide a sensible default threshold per metric (mid of expected range).
# You can override per metric on the CLI.
DEFAULT_THRESHOLDS = {
    "bleu":       0.30,   # corpus-style geometric mean — tends low for single-ref
    "bleu_1":     0.50,
    "bleu_2":     0.40,
    "bleu_3":     0.35,
    "bleu_4":     0.30,
    "rouge_l":    0.50,
    "meteor":     0.30,
    "cider_d":    1.00,   # CIDEr-D range is [0, 10]
    "sbert_sim":  0.70,
    "fer":        0.50,   # higher = more fluency errors (note: opposite direction)
    "fense":      0.50,
    "vocab":      None,   # corpus-level only
    "clap_sim":   0.50,
    "mace":       0.50,
    # extra CLAP columns (computed by compute_extra_clap_similarities)
    "clap_a2c_mine": 0.50,  # cos(audio, text(candidate))
    "clap_a2r":      0.50,  # cos(audio, text(reference))   — sanity baseline
    "clap_text":     0.70,  # cos(text(ref), text(cand))    — text-only via CLAP
}

# Metrics where "lower is better" semantically (rare). FER measures *error* rate.
HIGHER_IS_WORSE = {"fer"}


# --------------------------------------------------------------------------- #
# 2. Score-key normalization
# --------------------------------------------------------------------------- #
# Different metric classes return different dict keys for per-sentence scores.
# We map metric_name -> the score key we care about.
PRIMARY_SENT_KEY = {
    "bleu":       "bleu",
    "bleu_1":     "bleu_1",
    "bleu_2":     "bleu_2",
    "bleu_3":     "bleu_3",
    "bleu_4":     "bleu_4",
    "rouge_l":    "rouge_l",
    "meteor":     "meteor",
    "cider_d":    "cider_d",
    "sbert_sim":  "sbert_sim",
    "fer":        "fer",
    "fense":      "fense",
    "clap_sim":   "clap_sim",
    "mace":       "mace",
}


def _to_float_list(x) -> list[float]:
    """Coerce torch.Tensor / np.ndarray / list to a Python list[float]."""
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().flatten().tolist()
    try:
        return [float(v) for v in x]
    except TypeError:
        return [float(x)]


def extract_per_sentence(sents_scores: dict, metric_name: str) -> list[float]:
    """Pull out the per-sentence scores for a metric, handling key variations."""
    key = PRIMARY_SENT_KEY.get(metric_name, metric_name)
    if key in sents_scores:
        return _to_float_list(sents_scores[key])
    # fallback: any key starting with the metric name
    for k, v in sents_scores.items():
        if k.startswith(metric_name):
            return _to_float_list(v)
    return []


# --------------------------------------------------------------------------- #
# 2b. Extra CLAP similarities (audio↔candidate, audio↔reference, text↔text)
# --------------------------------------------------------------------------- #
# These are computed in addition to aac-metrics' clap_sim, NOT in place of it.
# We load CLAP once and reuse the embeddings, so this adds ~one CLAP forward pass
# per modality plus three cosine ops — cheap compared to loading the weights.
#
# Why we don't overwrite score__clap_sim:
#   aac-metrics' clap_sim has its own preprocessing / normalization choices that
#   may differ subtly from a direct msclap call. Keeping it untouched preserves
#   comparability with published CLAP-sim numbers. The three columns we add here
#   are mutually comparable because they all come from the same forward passes.
def compute_extra_clap_similarities(
    candidates: list[str],
    references: list[str],          # one reference per row
    audio_paths: list[str | None],  # None for rows without resolvable audio
    *,
    device: str,
    version: str = "2023",
    batch_size: int = 16,
) -> dict[str, list[float | None]]:
    """
    Returns three parallel lists, one entry per input row:
        clap_a2c_mine : cos(audio_emb, text_emb(candidate))      [audio-grounded]
        clap_a2r      : cos(audio_emb, text_emb(reference))      [sanity baseline]
        clap_text     : cos(text_emb(reference), text_emb(candidate))  [text-only]
    Entries for rows without resolvable audio are None for the two audio columns;
    clap_text is computed for every row since it doesn't need audio.
    """
    import numpy as np
    try:
        from msclap import CLAP
    except ImportError:
        print("[skip] extra-clap: msclap not installed (pip install msclap)",
              file=sys.stderr)
        n = len(candidates)
        return {"clap_a2c_mine": [None]*n, "clap_a2r": [None]*n,
                "clap_text": [None]*n}

    n = len(candidates)
    print(f"\n[extra-clap] loading CLAP version={version!r} on {device} ...",
          file=sys.stderr)
    clap = CLAP(version=version, use_cuda=(device == "cuda"))

    def _cos(a, b) -> float:
        # both are torch tensors of shape (1, d) (or numpy); normalize and dot
        a = a if isinstance(a, torch.Tensor) else torch.tensor(a)
        b = b if isinstance(b, torch.Tensor) else torch.tensor(b)
        a = a.float().flatten()
        b = b.float().flatten()
        return float(torch.nn.functional.cosine_similarity(
            a.unsqueeze(0), b.unsqueeze(0)).item())

    # --- text embeddings: candidates & references in batches ---------------
    def _embed_text(texts: list[str]) -> list:
        embs = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            e = clap.get_text_embeddings(chunk)
            # msclap returns torch.Tensor of shape (B, D)
            embs.extend([e[j] for j in range(len(chunk))])
        return embs

    print(f"[extra-clap] embedding {n} candidates + {n} references ...",
          file=sys.stderr)
    cand_embs = _embed_text(candidates)
    ref_embs  = _embed_text(references)

    # --- text↔text: always available -------------------------------------
    clap_text = [_cos(cand_embs[i], ref_embs[i]) for i in range(n)]

    # --- audio embeddings: only rows with resolvable audio ----------------
    clap_a2c_mine: list[float | None] = [None] * n
    clap_a2r:      list[float | None] = [None] * n
    usable_idx = [i for i, p in enumerate(audio_paths) if p is not None]
    if usable_idx:
        print(f"[extra-clap] embedding {len(usable_idx)} audio file(s) ...",
              file=sys.stderr)
        # msclap expects a flat list of paths
        usable_paths = [audio_paths[i] for i in usable_idx]
        audio_embs_dense = []
        for i in range(0, len(usable_paths), batch_size):
            chunk = usable_paths[i:i + batch_size]
            e = clap.get_audio_embeddings(chunk)
            audio_embs_dense.extend([e[j] for j in range(len(chunk))])

        for j, i in enumerate(usable_idx):
            clap_a2c_mine[i] = _cos(audio_embs_dense[j], cand_embs[i])
            clap_a2r[i]      = _cos(audio_embs_dense[j], ref_embs[i])

    # free memory
    del clap
    if device == "cuda":
        torch.cuda.empty_cache()

    return {
        "clap_a2c_mine": clap_a2c_mine,
        "clap_a2r":      clap_a2r,
        "clap_text":     clap_text,
    }


# --------------------------------------------------------------------------- #
# 3. Data loading
# --------------------------------------------------------------------------- #
def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[warn] bad json at line {ln}: {e}", file=sys.stderr)
    return rows


def _decode_audio_field(raw) -> bytes | None:
    """
    Normalize whatever sits under row['audio'] into raw audio file bytes.
    Accepts:
      * bytes / bytearray
      * list[int] of byte values
      * dict with one of {"bytes": ..., "b64": ..., "data": ..., "path": ...}
      * str that is the repr() of a bytes object,  e.g.  "b'RIFF\\x24...'"   <- our case
      * str that is base64 (optionally with a "data:audio/...;base64," prefix)
      * str that is hex
    Returns None if nothing usable is found.
    """
    if raw is None:
        return None
    # 1) already bytes
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    # 2) list of ints -> bytes
    if isinstance(raw, list) and raw and all(isinstance(x, int) for x in raw):
        try:
            return bytes(raw)
        except ValueError:
            return None
    # 3) dict wrappers: HF-datasets style {"bytes": ..., "path": ...}, etc.
    if isinstance(raw, dict):
        if raw.get("bytes") is not None:
            return _decode_audio_field(raw["bytes"])
        for k in ("b64", "base64", "data"):
            if raw.get(k) is not None:
                return _decode_audio_field(raw[k])
        if raw.get("path"):
            p = Path(raw["path"])
            if p.exists():
                return p.read_bytes()
        return None
    # 4) string -> try, in order: bytes-literal repr, base64, hex
    if isinstance(raw, str):
        import ast, base64, binascii
        s = raw.strip()

        # (a) bytes-literal repr like  "b'RIFF\\x24\\x08...'"  or  'b"..."'
        # This is what `repr(some_bytes)` produces and what your loader expects:
        #     audio_bytes = ast.literal_eval(samples[0]['audio'])
        if (s.startswith(("b'", 'b"')) or s.startswith(("rb'", 'rb"'))) and s.endswith(("'", '"')):
            try:
                val = ast.literal_eval(s)
                if isinstance(val, (bytes, bytearray)):
                    return bytes(val)
            except (ValueError, SyntaxError):
                pass  # fall through to other string formats

        # (b) data-URI prefix
        if s.startswith("data:") and "," in s:
            s = s.split(",", 1)[1]

        # (c) hex first if the string looks like pure hex (otherwise base64 would
        #     happily decode it into garbage, since hex chars are a base64 subset)
        if len(s) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in s):
            try:
                return bytes.fromhex(s)
            except ValueError:
                pass

        # (d) base64
        try:
            return base64.b64decode(s, validate=False)
        except (binascii.Error, ValueError):
            pass

        # (e) base64 fallback already covered above; nothing else to try
        return None
    return None


def _infer_audio_ext(buf: bytes, fallback: str = ".wav") -> str:
    """Sniff a sensible extension from common audio magic numbers."""
    if not buf or len(buf) < 12:
        return fallback
    head = buf[:12]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[:4] == b"fLaC":
        return ".flac"
    if head[:4] == b"OggS":
        return ".ogg"
    if head[:3] == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return ".mp3"
    if head[4:8] in (b"ftyp",):
        return ".m4a"
    return fallback


def materialize_audio(
    rows: list[dict],
    *,
    audio_dir: Path | None,
    audio_ext: str,
    tmp_dir: Path,
) -> tuple[list[str | None], list[str]]:
    """
    For every row produce an audio file path on disk (or None if unavailable).

    Resolution order, per row:
        1) row["audio"] bytes -> write to tmp_dir
        2) audio_dir / f"{audiocap_id}{audio_ext}" if --audio-dir given
        3) None

    Returns (paths, temp_files_written) so the caller can clean them up.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str | None] = []
    tmp_files: list[str] = []
    n_bytes = n_disk = n_missing = 0

    for r in rows:
        # 1) embedded bytes win — usually cheaper than scanning a dir
        buf = _decode_audio_field(r.get("audio")) if "audio" in r else None
        if buf:
            ext = _infer_audio_ext(buf, fallback=audio_ext)
            key = r.get("audiocap_id", r.get("idx", id(r)))
            fp = tmp_dir / f"audio_{key}{ext}"
            if not fp.exists():
                fp.write_bytes(buf)
                tmp_files.append(str(fp))
            paths.append(str(fp))
            n_bytes += 1
            continue
        # 2) on-disk lookup
        if audio_dir is not None:
            aid = r.get("audiocap_id")
            if aid is not None:
                p = audio_dir / f"{aid}{audio_ext}"
                if p.exists():
                    paths.append(str(p))
                    n_disk += 1
                    continue
        paths.append(None)
        n_missing += 1

    print(f"[audio] {n_bytes} from bytes, {n_disk} from disk, {n_missing} missing",
          file=sys.stderr)
    return paths, tmp_files


# --------------------------------------------------------------------------- #
# 4. Main eval loop
# --------------------------------------------------------------------------- #
def run(args):
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(Path(args.input))
    print(f"[data] loaded {len(rows)} rows from {args.input}", file=sys.stderr)

    candidates: list[str] = [r["modified_caption"] for r in rows]
    mult_refs:  list[list[str]] = [[r["original_caption"]] for r in rows]

    # PTB tokenization (same prep aac_metrics.evaluate does internally)
    from aac_metrics.utils.tokenization import preprocess_mono_sents, preprocess_mult_sents
    cands_tok = preprocess_mono_sents(candidates)
    refs_tok  = preprocess_mult_sents(mult_refs)

    device = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    print(f"[device] {device}", file=sys.stderr)

    registry = build_metric_registry(
        device,
        java_max_memory=args.java_max_memory,
        java_path=args.java_path,
    )
    metric_names = args.metrics or list(registry.keys())

    audio_paths: list[str | None] | None = None
    tmp_audio_files: list[str] = []
    has_inline_audio = any("audio" in r and r.get("audio") is not None for r in rows)
    if args.audio_dir or has_inline_audio:
        tmp_dir = Path(args.audio_tmp_dir) if args.audio_tmp_dir else (out_dir / "_audio_tmp")
        audio_paths, tmp_audio_files = materialize_audio(
            rows,
            audio_dir=Path(args.audio_dir) if args.audio_dir else None,
            audio_ext=args.audio_ext,
            tmp_dir=tmp_dir,
        )

    # per_item_scores[i][metric] = float
    per_item_scores: list[dict[str, float]] = [dict() for _ in rows]
    corpus_scores: dict[str, float] = {}

    # ---- group requested metric names by their *physical* loader -----------
    # Several logical names can share one underlying class (BLEU produces
    # bleu_1..bleu_4 in one go), so we identify a group by the loader function
    # object itself. Within a group all entries share the needs_audio flag.
    groups: dict[Any, list[str]] = {}
    for name in metric_names:
        if name not in registry:
            print(f"[skip] unknown metric '{name}'", file=sys.stderr)
            continue
        loader, _ = registry[name]
        groups.setdefault(loader, []).append(name)

    for loader, names in groups.items():
        _, needs_audio = registry[names[0]]
        label = "+".join(names) if len(names) > 1 else names[0]

        if needs_audio:
            if audio_paths is None:
                print(f"[skip] {label}: no audio source "
                      f"(pass --audio-dir or include 'audio' bytes in JSONL)",
                      file=sys.stderr)
                continue
            usable_idx = [i for i, p in enumerate(audio_paths) if p is not None]
            if not usable_idx:
                print(f"[skip] {label}: no audio files resolved", file=sys.stderr)
                continue

        print(f"\n[metric] {label} ...", file=sys.stderr)
        try:
            metric = loader()
            if needs_audio:
                sub_cands = [cands_tok[i] for i in usable_idx]
                sub_refs  = [refs_tok[i]  for i in usable_idx]
                sub_audio = [audio_paths[i] for i in usable_idx]
                corpus, sents = metric(
                    candidates=sub_cands,
                    mult_references=sub_refs,
                    audio_paths=sub_audio,
                )
            else:
                corpus, sents = metric(candidates=cands_tok, mult_references=refs_tok)

            # harvest every requested logical metric from this single run
            for nm in names:
                sent_vals = extract_per_sentence(sents, nm)
                if needs_audio:
                    for j, i in enumerate(usable_idx):
                        if j < len(sent_vals):
                            per_item_scores[i][nm] = sent_vals[j]
                else:
                    for i, v in enumerate(sent_vals):
                        per_item_scores[i][nm] = v

                ck = PRIMARY_SENT_KEY.get(nm, nm)
                if ck in corpus:
                    corpus_scores[nm] = float(_to_float_list(corpus[ck])[0])
                elif nm in corpus:
                    corpus_scores[nm] = float(_to_float_list(corpus[nm])[0])

                print(f"        corpus {nm:<10} = "
                      f"{corpus_scores.get(nm, float('nan')):.4f}",
                      file=sys.stderr)

            # Free GPU memory between heavy metrics
            del metric
            if device == "cuda":
                torch.cuda.empty_cache()

        except Exception as e:
            print(f"[error] {label} failed: {e}", file=sys.stderr)
            import subprocess
            if isinstance(e, subprocess.CalledProcessError) and "meteor" in names:
                print(
                    f"[hint] METEOR runs an external java jar. Exit code "
                    f"{e.returncode} usually means one of:\n"
                    f"        - JVM heap too large for the host (lower --java-max-memory, "
                    f"currently {args.java_max_memory!r}; try 2G or 1G)\n"
                    f"        - JVM heap too small (raise --java-max-memory on big datasets)\n"
                    f"        - METEOR jar missing in ~/.cache/aac-metrics "
                    f"(re-run `aac-metrics-download`)\n"
                    f"        - wrong java version (need 1.8 <= java <= 13), or no java on ARM\n"
                    f"        The failing command was:\n"
                    f"        {' '.join(map(str, e.cmd))}",
                    file=sys.stderr,
                )
            traceback.print_exc(file=sys.stderr)

    # ---------- extra CLAP similarities --------------------------------- #
    # Computed unconditionally when --extra-clap is on (default: on if msclap
    # is installed). The three columns (clap_a2c_mine / clap_a2r / clap_text)
    # come from a single CLAP load and let you study how audio-grounded vs
    # text-only CLAP scores agree per-row.
    if args.extra_clap and audio_paths is not None:
        try:
            references = [r["original_caption"] for r in rows]
            extra = compute_extra_clap_similarities(
                candidates=candidates,
                references=references,
                audio_paths=audio_paths,
                device=device,
                version=args.clap_version,
                batch_size=args.clap_batch_size,
            )
            for key, vals in extra.items():
                for i, v in enumerate(vals):
                    if v is not None:
                        per_item_scores[i][key] = v
            print(f"[extra-clap] added columns: {list(extra.keys())}",
                  file=sys.stderr)
        except Exception as e:
            print(f"[error] extra-clap failed: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    elif args.extra_clap and audio_paths is None:
        print("[skip] extra-clap: no audio source available", file=sys.stderr)

    # ---------- write per-item results ---------------------------------- #
    out_jsonl = out_dir / "per_item_scores.jsonl"
    out_csv   = out_dir / "per_item_scores.csv"
    enriched = []
    for r, scores in zip(rows, per_item_scores):
        merged = {
            "idx":               r.get("idx"),
            "audiocap_id":       r.get("audiocap_id"),
            "modification_type": r.get("modification_type"),
            "label":             r.get("label"),
            "original_caption":  r.get("original_caption"),
            "modified_caption":  r.get("modified_caption"),
            **{f"score__{k}": v for k, v in scores.items()},
        }
        enriched.append(merged)

    with open(out_jsonl, "w") as f:
        for row in enriched:
            f.write(json.dumps(row) + "\n")
    pd.DataFrame(enriched).to_csv(out_csv, index=False)
    print(f"\n[out] per-item -> {out_jsonl}  &  {out_csv}", file=sys.stderr)

    # ---------- corpus + failure-rate report ---------------------------- #
    df = pd.DataFrame(enriched)
    report_path = out_dir / "report.md"
    report_lines = ["# Antibench metric report", "", "## Corpus scores", ""]
    for m, s in corpus_scores.items():
        report_lines.append(f"- **{m}**: {s:.4f}")

    # Failure rates per (label, modification_type, metric)
    report_lines += ["", "## Failure rates per (modification_type, label)",
                     "",
                     "A metric *fails* on a `positive` if its score < threshold,",
                     "and on a `negative` if its score > threshold.",
                     "(FER is inverted: higher = more fluency errors.)",
                     ""]

    # Allow --threshold overrides like bleu_4=0.25 fense=0.6
    thresholds = dict(DEFAULT_THRESHOLDS)
    for kv in args.threshold or []:
        k, _, v = kv.partition("=")
        thresholds[k] = float(v)

    summary_rows = []
    metrics_present = [m for m in metric_names if f"score__{m}" in df.columns]
    for (mod, lab), g in df.groupby(["modification_type", "label"], dropna=False):
        n = len(g)
        row = {"modification_type": mod, "label": lab, "n": n}
        for m in metrics_present:
            thr = thresholds.get(m)
            if thr is None:
                row[m] = float("nan")
                continue
            col = g[f"score__{m}"].dropna()
            if col.empty:
                row[m] = float("nan")
                continue
            if m in HIGHER_IS_WORSE:
                # FER: a "good" positive has LOW error; a "good" negative has HIGH error
                if lab == "positive":
                    fails = (col > thr).mean()
                else:
                    fails = (col <= thr).mean()
            else:
                if lab == "positive":
                    fails = (col < thr).mean()
                elif lab == "negative":
                    fails = (col > thr).mean()
                else:
                    fails = float("nan")
            row[m] = float(fails)
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = out_dir / "failure_rates.csv"
    summary_df.to_csv(summary_csv, index=False)
    report_lines.append("")
    report_lines.append(summary_df.to_markdown(index=False, floatfmt=".3f"))

    # mean per-metric score per (label, mod) — useful sanity check
    report_lines += ["", "## Mean metric score per (modification_type, label)", ""]
    mean_rows = []
    for (mod, lab), g in df.groupby(["modification_type", "label"], dropna=False):
        row = {"modification_type": mod, "label": lab, "n": len(g)}
        for m in metrics_present:
            col = g[f"score__{m}"].dropna()
            row[m] = float(col.mean()) if not col.empty else float("nan")
        mean_rows.append(row)
    mean_df = pd.DataFrame(mean_rows)
    mean_df.to_csv(out_dir / "mean_scores.csv", index=False)
    report_lines.append(mean_df.to_markdown(index=False, floatfmt=".3f"))

    # ---------- CLAP audio-vs-text-encoder correlation ------------------ #
    # The whole point of computing clap_a2c_mine + clap_text per-row is to ask:
    # how much does the audio-grounded CLAP score agree with the text-only
    # CLAP score? Low correlation on a perturbation type = the perturbation
    # changes one signal but not the other, which is an antibench finding.
    clap_cols = [c for c in ["clap_sim", "clap_a2c_mine", "clap_a2r",
                             "clap_text", "mace"] if f"score__{c}" in df.columns]
    if len(clap_cols) >= 2:
        report_lines += ["", "## CLAP per-row correlations", "",
                         "Pearson correlation between CLAP-family score columns. "
                         "The cell (`clap_a2c_mine`, `clap_text`) is the headline: "
                         "do the audio-grounded and text-only CLAP scores agree?", ""]
        corr_df = df[[f"score__{c}" for c in clap_cols]].corr().round(3)
        corr_df.index   = clap_cols
        corr_df.columns = clap_cols
        corr_df.to_csv(out_dir / "clap_correlations.csv")
        report_lines.append(corr_df.to_markdown(floatfmt=".3f"))

        # Per (modification_type, label) breakdown — where the metrics disagree
        report_lines += ["", "### Per-perturbation: corr(clap_a2c_mine, clap_text)",
                         "",
                         "Low values flag perturbations that move audio-grounded "
                         "and text-only CLAP scores differently — these are the "
                         "antibench-relevant cases.", ""]
        per_mod_rows = []
        for (mod, lab), g in df.groupby(["modification_type", "label"], dropna=False):
            row = {"modification_type": mod, "label": lab, "n": len(g)}
            if {"score__clap_a2c_mine", "score__clap_text"}.issubset(g.columns):
                gg = g[["score__clap_a2c_mine", "score__clap_text"]].dropna()
                row["corr(a2c, text)"] = (
                    float(gg["score__clap_a2c_mine"].corr(gg["score__clap_text"]))
                    if len(gg) >= 2 else float("nan")
                )
            else:
                row["corr(a2c, text)"] = float("nan")
            per_mod_rows.append(row)
        per_mod_df = pd.DataFrame(per_mod_rows)
        per_mod_df.to_csv(out_dir / "clap_a2c_vs_text_corr.csv", index=False)
        report_lines.append(per_mod_df.to_markdown(index=False, floatfmt=".3f"))

    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"[out] report   -> {report_path}", file=sys.stderr)
    print(f"[out] failures -> {summary_csv}", file=sys.stderr)

    # ---------- clean up temp audio files ------------------------------- #
    if tmp_audio_files and not args.keep_audio_tmp:
        removed = 0
        for fp in tmp_audio_files:
            try:
                Path(fp).unlink()
                removed += 1
            except OSError:
                pass
        # try to remove the dir if empty
        try:
            (out_dir / "_audio_tmp").rmdir()
        except OSError:
            pass
        print(f"[audio] cleaned {removed} temp file(s)", file=sys.stderr)


# --------------------------------------------------------------------------- #
def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="antibench JSONL")
    p.add_argument("--output-dir", default="antibench_results")
    p.add_argument("--metrics", nargs="*", default=None,
                   help="subset of metrics to run (default: all available)")
    p.add_argument("--audio-dir", default=None,
                   help="directory of audio files (used when JSONL has no inline audio bytes)")
    p.add_argument("--audio-ext", default=".wav",
                   help="extension for --audio-dir lookups and fallback for inline bytes (default: .wav)")
    p.add_argument("--audio-tmp-dir", default=None,
                   help="where to write decoded inline-audio temp files (default: <output-dir>/_audio_tmp)")
    p.add_argument("--keep-audio-tmp", action="store_true",
                   help="don't delete decoded temp audio files after the run")
    p.add_argument("--cpu", action="store_true", help="force CPU")
    p.add_argument("--java-max-memory", default="2G",
                   help="JVM heap cap for METEOR/SPICE/SPIDEr/SPIDEr-FL (default: 2G). "
                        "Lower this if the SPICE jar fails with 'returned non-zero exit status 1' "
                        "due to insufficient memory; raise it on huge datasets.")
    p.add_argument("--java-path", default=None,
                   help="path to a specific java binary if 'java' on PATH is wrong "
                        "(also overridable via env AAC_METRICS_JAVA_PATH)")
    p.add_argument("--threshold", nargs="*", default=None,
                   help="override thresholds, e.g. --threshold bleu_4=0.25 fense=0.6")
    p.add_argument("--extra-clap", action="store_true", default=True,
                   help="compute extra CLAP similarities per row: clap_a2c_mine "
                        "(audio↔candidate), clap_a2r (audio↔reference), "
                        "clap_text (text↔text via CLAP text encoder). "
                        "Enabled by default; use --no-extra-clap to disable.")
    p.add_argument("--no-extra-clap", dest="extra_clap", action="store_false",
                   help="disable the extra CLAP similarity columns")
    p.add_argument("--clap-version", default="2023", choices=["2022", "2023"],
                   help="msclap model version for the extra CLAP columns (default: 2023)")
    p.add_argument("--clap-batch-size", type=int, default=16,
                   help="batch size for CLAP text/audio embedding (default: 16)")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
