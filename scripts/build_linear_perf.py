#!/usr/bin/env python3
"""Build the portfolio's v1.1.0 evidence extract from its immutable result ZIP.

Uses only the Python standard library. No GPU execution, fitting, reselection,
or filtering of quality-flagged results takes place.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets/linear-perf"
SOURCE_COMMIT = "59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911"
SOURCE_REPOSITORY = "https://github.com/ryan30402/transformer-linear-layer-performance-predictor"
RESULT_SHA256 = "a601e14bb3d1d2b661f06021432b461104850452ddcc1c695c55006db29374b1"
MEASURED_SOURCE_SHA256 = "1f748883a23d0e9706856493eb011eec88d5e3f8926fafd3874c5d23d2c8345a"
EXPERIMENT = "experiments/a100_20261106"
SPLITS = ("train", "test", "challenge", "stress")
METRIC_KEYS = {
    "weighted_mean_ape_pct": "weighted_mean_ape_pct",
    "mean_ape_pct": "mean_ape_pct",
    "median_ape_pct": "median_ape_pct",
    "p90_ape_pct": "p90_ape_pct",
    "worst_ape_pct": "max_ape_pct",
}
MODELS = [
    {"id": "flop_only", "label": "FLOP-only", "short_label": "FLOP-only"},
    {"id": "roofline_2p", "label": "2-parameter Roofline", "short_label": "2p Roofline"},
    {"id": "roofline_3p", "label": "3-parameter Roofline", "short_label": "3p Roofline"},
    {"id": "shape_log_ridge", "label": "Shape-log Ridge", "short_label": "Shape-log Ridge"},
    {"id": "roofline_residual_krr", "label": "Roofline residual KRR", "short_label": "Residual KRR"},
]
COVERAGE_LABELS = {
    "training": "Training shape",
    "unseen_M_inside_training_family_range": "New M inside this training family's M range",
    "unseen_M_outside_training_family_range_after_budget_exclusions": "New M outside this training family's retained M range",
    "wholly_unseen_NK_family": "Entire N,K family excluded from training",
    "artificial_irregular_stress": "Artificial N+1, K+1 stress shape",
}
LEGACY_FILES = {
    "acquisition_all_budgets.csv", "selected_pipeline.csv", "case_latencies.csv",
    "offline_batching.csv", "six_session_summary.json", "cross_round_latency_spread.csv",
    "frozen_selected_transfer.csv", "quality_and_audits.csv", "FINAL_SUMMARY.json",
    "paired_dtype_latencies.csv", "frozen_krr_candidate_transfer.csv",
}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_bytes(value, *, compact=False) -> bytes:
    kwargs = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, **kwargs) + "\n").encode("utf-8")


def csv_bytes(rows, columns) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def read_csv(content: bytes):
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"), newline="")))


def quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    left = math.floor(position)
    right = math.ceil(position)
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)


def counts(rows):
    counter = Counter(row["split"] for row in rows)
    return {split: counter[split] for split in SPLITS}


def metric_row(source):
    return {
        "context_id": source["group_id"],
        "dtype": source["dtype"],
        "cache_policy": source["cache_policy"],
        "split": source["split"],
        "model_id": source["model_id"],
        "selected_by_cv": source["selected_by_cv"] == "True",
        "n_cases": int(source["n"]),
        **{key: float(source[original]) for key, original in METRIC_KEYS.items()},
    }


def build(source_root: Path):
    archive_path = source_root / EXPERIMENT / "results.zip"
    archive_bytes = archive_path.read_bytes()
    if sha256(archive_bytes) != RESULT_SHA256:
        raise ValueError("The result ZIP does not match the published v1.1.0 archive digest.")

    source_members = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        def raw(name):
            content = archive.read(name)
            source_members[name] = sha256(content)
            return content

        def obj(name):
            return json.loads(raw(name))

        def lines(name):
            return [json.loads(line) for line in raw(name).splitlines() if line.strip()]

        if sha256(raw("source_archive.zip")) != MEASURED_SOURCE_SHA256:
            raise ValueError("The embedded measurement source archive does not match its digest.")
        workload = obj("run/workload_manifest.json")
        run = obj("run/summary.json")
        analysis = obj("run/primary/analysis/summary.json")
        environment = obj("run/primary/dataset/environments.json")
        settings = obj("run/primary/dataset/measurement_settings.json")
        primary = lines("run/primary/dataset/measurements.jsonl")
        repeat = lines("run/repeat/dataset/measurements.jsonl")
        primary_quality = obj("run/primary/dataset/quality.json")
        repeat_quality = obj("run/repeat/dataset/quality.json")
        rotation = obj("run/primary/dataset/rotation_eligibility.json")
        repeat_summary = obj("run/repeat_comparison/summary.json")
        all_metric_bytes = raw("run/primary/analysis/metrics.csv")
        selected_metric_bytes = raw("run/selected_model_metrics.csv")
        for filename, content in (("metrics.csv", all_metric_bytes), ("selected_model_metrics.csv", selected_metric_bytes)):
            if (source_root / EXPERIMENT / filename).read_bytes() != content:
                raise ValueError(f"The published {filename} is not an exact copy of the archived table.")
        metrics = [metric_row(row) for row in read_csv(all_metric_bytes)]
        selected_metrics = [metric_row(row) for row in read_csv(selected_metric_bytes)]

        contexts, selection_groups = [], []
        for group in analysis["groups"]:
            dtype, policy = group["dtype"], group["cache_policy"]
            suite = obj("run/primary/analysis/" + group["model_suite_file"])
            primary_context = [r for r in primary if (r["dtype"], r["cache_policy"]) == (dtype, policy)]
            repeat_context = [r for r in repeat if (r["dtype"], r["cache_policy"]) == (dtype, policy)]
            context = {
                "id": group["group_id"], "dtype": dtype, "cache_policy": policy,
                "label": ("FP16" if dtype == "float16" else "BF16") + " / " + ("warm reuse" if policy == "warm_reuse" else "buffer rotation"),
                "train_count": group["train_count"], "train_family_count": group["train_family_count"],
                "selected_model_id": group["selected_model_id"], "cv_folds": suite["cv"]["fold_count"],
                "primary_count": len(primary_context), "repeat_count": len(repeat_context),
                "split_counts": counts(primary_context),
            }
            contexts.append(context)
            selection_groups.append({
                "context_id": context["id"], "dtype": dtype, "cache_policy": policy,
                "training_shapes": group["train_count"], "training_families": group["train_family_count"],
                "folds": suite["cv"]["fold_count"], "configurations": len(suite["cv"]["trials"]),
                "selected_model_id": suite["selected_model_id"],
                "selected_configuration": suite["cv"]["models"][suite["selected_model_id"]]["configuration"],
                "selection_score_key": suite["selection_score_key"],
                "secondary_score_key": suite["selection_secondary_key"],
                "selected_cv_weighted_mean_ape_pct": suite["cv"]["models"][suite["selected_model_id"]]["oof_metrics"]["weighted_mean_ape_pct"],
                "feature_count": len(suite["feature_contract"]["names"]),
            })

        context_by_pair = {(c["dtype"], c["cache_policy"]): c for c in contexts}
        repeat_contexts, repeat_pairs = [], []
        for group in repeat_summary["groups"]:
            context = context_by_pair[(group["dtype"], group["cache_policy"])]
            source_pairs = read_csv(raw("run/repeat_comparison/" + group["repeat_file"]))
            changes = [float(row["absolute_change_pct"]) for row in source_pairs]
            repeat_contexts.append({
                "context_id": context["id"], "dtype": context["dtype"], "cache_policy": context["cache_policy"],
                "paired_shapes": len(source_pairs),
                "median_absolute_change_pct": group["median_absolute_change_pct"],
                "p90_absolute_change_pct": quantile(changes, 0.9),
                "maximum_absolute_change_pct": group["maximum_absolute_change_pct"],
                "pairs_above_10pct": sum(value > 10.0 for value in changes),
            })
            for row in source_pairs:
                repeat_pairs.append({"context_id": context["id"], "dtype": context["dtype"], "cache_policy": context["cache_policy"], **row})

        repeat_ids = {row["case_id"] for row in repeat}
        if repeat_ids != set(run["repeat_plan"]["case_ids"]):
            raise ValueError("The measured repeat subset differs from its archived shape-only plan.")
        rotation_by_case = defaultdict(set)
        for row in rotation:
            rotation_by_case[row["case_id"]].add(row["eligible"])
        if any(len(values) != 1 for values in rotation_by_case.values()):
            raise ValueError("The schema requires matching FP16/BF16 rotation eligibility.")
        rotated_ids = {row["case_id"] for row in primary if row["cache_policy"] == "rotating_buffers"}
        if rotated_ids != {case for case, flags in rotation_by_case.items() if flags == {True}}:
            raise ValueError("Rotation eligibility differs from the actually measured cohort.")
        grouped_cases = defaultdict(list)
        sampling_rows = []
        for case in workload["cases"]:
            cell = {
                "id": case["id"], "m": case["m"], "split": case["split"], "weight": case["weight"],
                "repeat": case["id"] in repeat_ids, "rotation_eligible": case["id"] in rotated_ids,
                "coverage": case["coverage"], "coverage_label": COVERAGE_LABELS[case["coverage"]],
            }
            grouped_cases[(case["n"], case["k"], case["family"])].append(cell)
            sampling_rows.append({
                "case_id": case["id"], "family": case["family"], "m": case["m"], "n": case["n"], "k": case["k"],
                "split": case["split"], "weight": case["weight"], "repeat": cell["repeat"],
                "rotation_eligible": cell["rotation_eligible"], "coverage": case["coverage"],
            })
        families = []
        for (n, k, family), cells in sorted(grouped_cases.items()):
            cells.sort(key=lambda cell: cell["m"])
            families.append({
                "id": family, "n": n, "k": k,
                "kind": "stress" if all(c["split"] == "stress" for c in cells) else "architecture",
                "challenge": all(c["split"] == "challenge" for c in cells),
                "count": len(cells), "split_counts": counts(cells),
                "rotation_count": sum(c["rotation_eligible"] for c in cells),
                "repeat_count": sum(c["repeat"] for c in cells), "cases": cells,
            })
        excluded = Counter(row["reason"] for row in workload["excluded_cases"])
        sampling = {
            "seed": workload["seed"], "m_values": sorted(set(workload["split_policy"]["train_m"] + workload["split_policy"]["test_m"])),
            "train_m_values": workload["split_policy"]["train_m"], "test_m_values": workload["split_policy"]["test_m"],
            "families": families, "split_counts": counts(workload["cases"]),
            "repeat_split_counts": counts([case for case in workload["cases"] if case["id"] in repeat_ids]),
            "exclusions": {
                "memory_budget": excluded["ideal_tensor_bytes_exceed_declared_per_case_budget"],
                "previously_exposed": excluded["already_exposed_shape_not_an_independent_evaluation"],
                "cases": workload["excluded_cases"],
            },
            "architecture_configs": [{"id": source["id"], "repository": source["repository"], "revision": source["revision"], "url": source["url"]} for source in workload["source_metadata"]],
            "weight_scope": workload["weight_policy"]["interpretation"],
            "selection_scope": "Shape-only design. Latency labels and prediction errors do not determine split membership or the repeat subset.",
            "repeat_scope": "77 shapes selected before measurement using split, M regime, and alignment strata; measured later on the same physical GPU/session.",
            "rotation_scope": "Four-buffer working-set sensitivity for eligible weights up to twice the observed L2 size; not proof of cold-cache execution.",
        }

        quality_stages = {}
        for stage, records, report in (("primary", primary, primary_quality), ("repeat", repeat, repeat_quality)):
            record_by_key = {(r["case_id"], r["dtype"], r["cache_policy"]): r for r in records}
            flags = []
            for flag in report["flagged_rows"]:
                record = record_by_key[(flag["case_id"], flag["dtype"], flag["cache_policy"])]
                flags.append({**flag, "split": record["split"], "visit_medians_us": [value * 1000 for value in record["samples_ms"]]})
            quality_stages[stage] = {
                "passed": report["passed"], "aggregate_rows": len(records),
                "raw_visits": sum(row["completed_visits"] for row in records),
                "control_visits": sum(row["visits"] for row in report["controls"]),
                "flagged_rows_count": len(flags), "flagged_split_counts": counts(flags), "flagged_rows": flags,
                "failing_control_groups": [row for row in report["controls"] if not row["passed"]],
                "controls": report["controls"],
                "maximum_within_visit_cv_pct": max(row["quality"]["max_within_visit_cv_pct"] for row in records),
            }
        quality = {
            "measurement_quality_passed": run["measurement_quality_passed"],
            "thresholds": primary_quality["thresholds"], **quality_stages,
            "primary_flagged_rows_in_repeat": sum(row["case_id"] in repeat_ids for row in primary_quality["flagged_rows"]),
            "interpretation": "All flagged rows remain in the results. Passing record-consistency checks is separate from passing every timing-quality threshold.",
        }
        identity = next(iter(environment["contexts"].values()))["identity"]
        measurement = {
            "operation": "Y[M,N] = X[M,K] @ W[N,K].T",
            "execution": identity["execution"], "device": environment["device"]["name"],
            "sm_count": environment["device"]["multiprocessor_count"], "l2_cache_bytes": environment["device"]["l2_cache_bytes"],
            "python_version": identity["python_version"], "pytorch_version": identity["pytorch_version"],
            "cuda_runtime_version": identity["cuda_runtime_version"], "driver_versions": identity["driver_versions"],
            "settings": settings,
            "aggregation": "Median of 3 visit medians; each visit uses 9 graph-replay samples normalized by that visit's captured GEMM count.",
            "included": "CUDA-event graph-replay elapsed time, including resident GPU memory accesses and device-side replay/inter-kernel gaps, divided by the captured GEMM count.",
            "excluded": "Allocation, CPU-GPU transfer, graph capture, warmup, reference checks, profiling, fitting, backup-copy intervals, full decoder, and serving queues.",
            "layer_experiment_status": run["stages"]["layer"]["status"],
        }
        selection = {
            "method": "Six-fold grouped cross-validation on training N,K families only; fold-local preprocessing and fitting, followed by refitting on all training rows.",
            "primary_score": "Pooled out-of-fold weighted mean APE; weighted P90 and then fixed model order break ties.",
            "heldout_labels_used_for_selection": analysis["heldout_labels_used_for_selection"],
            "test_labels_measured_before_fitting": analysis["test_labels_measured_before_fitting"],
            "repeat_labels_used_for_refit": run["repeat_labels_used_for_refit"],
            "cv_score_scope": "Training model-selection evidence; not an unbiased final-test performance estimate.",
            "groups": selection_groups,
        }

    provenance = {
        "protocol_version": workload["protocol_version"], "recorded_date_utc": run["created_at_utc"][:10],
        "session_id": run["session_id"], "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "results_archive_url": f"{SOURCE_REPOSITORY}/raw/{SOURCE_COMMIT}/{EXPERIMENT}/results.zip",
        "results_archive_sha256": RESULT_SHA256, "results_archive_bytes": len(archive_bytes),
        "measurement_source_archive_sha256": MEASURED_SOURCE_SHA256,
        "source_members_sha256": source_members,
        "scope": "Derived static presentation of an archived A100 experiment. No new GPU work, refitting, model selection, or deletion of flagged rows.",
    }
    summary = {
        "primary_shapes": len(workload["cases"]), "primary_rows": len(primary),
        "split_counts": counts(workload["cases"]), "repeat_shapes": len(repeat_ids), "repeat_rows": len(repeat),
        "context_count": len(contexts), "model_families": len(MODELS), "cv_folds": 6,
        "candidate_configurations": selection_groups[0]["configurations"],
        "measurement_quality_passed": run["measurement_quality_passed"],
        "requested_stages_completed": run["all_requested_stages_completed"],
        "same_physical_gpu_verified": repeat_summary["same_physical_gpu_verified"],
        "architecture_families": sum(f["kind"] == "architecture" for f in families),
        "stress_families": sum(f["kind"] == "stress" for f in families),
        "challenge_families": sum(f["challenge"] for f in families),
        "hardware_name": measurement["device"],
    }
    data = {
        "schema_version": 2, "provenance": provenance, "summary": summary,
        "models": MODELS, "contexts": contexts, "metrics": metrics, "selected_metrics": selected_metrics,
        "repeat_contexts": repeat_contexts, "sampling": sampling, "quality": quality,
        "measurement": measurement, "selection": selection,
        "metric_definitions": {
            "ape": "100 * abs(predicted - observed) / observed",
            "weighted_mean_ape_pct": "Sum of weight * APE divided by the sum of weights; declared architectural occurrence weights, not traffic weights or WAPE.",
            "mean_ape_pct": "Unweighted arithmetic mean of per-shape APE.",
            "median_ape_pct": "Unweighted median of per-shape APE.",
            "p90_ape_pct": "Unweighted 90th percentile of per-shape APE, using linear interpolation.",
            "worst_ape_pct": "Maximum observed per-shape APE in this evaluation subset; not a future error bound.",
        },
        "limitations": [
            "One A100 hardware/software configuration and one session with a later subset repeat; no cross-day or cross-device replication.",
            "Cache contexts use separately fitted models and partly different eligible cohorts; their errors do not isolate a causal cache effect.",
            "Six primary rows and one repeat control group fail declared timing thresholds. The overall quality flag is false; all rows are retained.",
            "Matrix dimensions come from five pinned architecture configurations, not observed production traffic or full pretrained-model execution.",
            "No hardware counters establish cache-hit rates, bandwidth saturation, or Tensor Core utilization.",
            "The optional decoder-layer experiment was not requested. Per-GEMM prediction error is not full-model latency, serving performance, or a GPU speedup.",
        ],
    }
    payload = {
        "results.json": json_bytes(data, compact=True),
        "evidence/model_metrics.csv": all_metric_bytes,
        "evidence/selected_model_metrics.csv": selected_metric_bytes,
        "evidence/sampling_cases.csv": csv_bytes(sampling_rows, list(sampling_rows[0])),
        "evidence/repeat_comparison.csv": csv_bytes(repeat_pairs, list(repeat_pairs[0])),
        "evidence/repeat_summary.csv": csv_bytes(repeat_contexts, list(repeat_contexts[0])),
        "evidence/quality_summary.json": json_bytes(quality),
        "evidence/measurement_contract.json": json_bytes(measurement),
        "evidence/model_selection.json": json_bytes(selection),
        "evidence/provenance.json": json_bytes(provenance),
    }
    evidence_text = f"""# Transformer Linear Layer Performance Predictor: v1.1.0 website evidence

This is a small, reproducible extract of the A100 experiment recorded on 2026-11-06.
It contains archived tables and derived presentation data. It does not run a GPU benchmark or refit a model.

## Source and scope

- Publication commit: [{SOURCE_COMMIT}]({SOURCE_REPOSITORY}/tree/{SOURCE_COMMIT}).
- [Complete original result archive]({provenance['results_archive_url']}) ({len(archive_bytes):,} bytes).
- Original result archive SHA-256: `{RESULT_SHA256}`.
- Embedded measurement-source archive SHA-256: `{MEASURED_SOURCE_SHA256}`.
- [Results and limitations]({SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/docs/RESULTS.md).
- [Protocol]({SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/docs/PROTOCOL.md).
- [Published review]({SOURCE_REPOSITORY}/blob/{SOURCE_COMMIT}/{EXPERIMENT}/review.html).

The publication commit includes documentation and verification work performed after the measurements.
The embedded source archive identifies the exact retained measurement source. Its hash is separate from the publication commit.

## Included files

| File | Contents |
|---|---|
| `model_metrics.csv` | Exact archived primary table: 60 rows = 5 candidate families x 4 precision/buffer contexts x 3 evaluation splits. |
| `selected_model_metrics.csv` | Exact archived table for the training-CV-selected model: 12 rows. |
| `sampling_cases.csv` | 609 retained shapes, split assignment, declared weights, rotation eligibility, and membership in the 77-shape repeat. |
| `repeat_comparison.csv` | 280 recorded primary/repeat pairs, with context columns added; original timing values are retained. |
| `repeat_summary.csv` | Four context summaries; unweighted P90 is calculated by linear interpolation from the recorded paired changes. |
| `quality_summary.json` | The six flagged primary rows, repeat control failure, unchanged thresholds, and cohort counts. |
| `measurement_contract.json` | Recorded hardware/software, timing settings, aggregation, and scope. |
| `model_selection.json` | Training-only CV settings, selected configurations, and scores. CV scores are selection evidence, not final-test estimates. |
| `provenance.json` | Immutable repository links and hashes of the original archive members used by the extract. |
| `../results.json` | Schema 2 data consumed by the browser explorer. |
| `manifest.json` | SHA-256 digests of every extract payload, using paths relative to `assets/linear-perf/`. |

## Reading the results

The primary design has 311 training, 134 ordinary-test, 118 unseen-family challenge,
and 46 artificial irregular stress shapes. Warm reuse covers all 609 per dtype.
Four-buffer rotation covers 519 eligible shapes per dtype: 266 training, 113 test,
100 challenge, and 40 stress. Rotation tests working-set sensitivity; it does not prove cold-cache execution.

All labels were measured before fitting. Fitting and six-fold grouped CV use only training N,K families.
Each context has a separately fitted selected model. The chosen Roofline residual KRR is retained on every
evaluation split even when another candidate has a lower displayed error.

The headline error is **weighted mean APE**, using declared architectural operation-occurrence weights.
It is not WAPE, an accuracy percentage, or a GPU speedup. Mean, median, P90, and maximum columns without
the `weighted_` prefix are unweighted per-shape statistics. In `results.json`, `worst_ape_pct` is an alias
for the archived `max_ape_pct` column. All other displayed metric values are copied without rounding.

**Overall timing-quality status: false.** Six primary aggregate rows and one repeat control group fail
the declared thresholds. All rows remain in the metrics. Typical same-session repeat agreement is about
1-2%, but maximum differences approach 28%; none of the six flagged primary rows was in the preselected repeat.
This is one physical A100 and one session, not a cross-day or cross-device replication.

## Rebuild and verify

From a checkout of the website, with the source project available beside it:

```bash
python3 scripts/build_linear_perf.py --source ../transformer-linear-layer-performance-predictor
python3 scripts/build_linear_perf.py --source ../transformer-linear-layer-performance-predictor --check
python3 scripts/check_linear_perf.py
python3 scripts/check_site.py
```

The builder checks the pinned original ZIP and embedded-source hashes and verifies that the two published
CSV copies match the archive byte for byte. It then writes deterministic static files and a deterministic
download ZIP. `--check` compares the generated bytes without modifying the website.
The website validator checks route/anchor integrity, the displayed card values, CSV-to-JSON equality,
sampling counts, repeat arithmetic, model-selection consistency, file hashes, and ZIP contents.
These are publication consistency checks; they do not re-execute GPU work or certify benchmark quality.
"""
    payload["evidence/EVIDENCE.md"] = evidence_text.encode("utf-8")
    manifest = {
        "schema_version": 2, "protocol_version": "1.1.0",
        "path_base": "assets/linear-perf/", "source_commit": SOURCE_COMMIT,
        "results_archive_sha256": RESULT_SHA256,
        "files": {name: sha256(content) for name, content in sorted(payload.items())},
    }
    payload["evidence/manifest.json"] = json_bytes(manifest)
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    payload["linear-perf-evidence.zip"] = packed.getvalue()
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Checkout of the published predictor project")
    parser.add_argument("--check", action="store_true", help="Compare derived bytes without writing files")
    args = parser.parse_args()
    try:
        payload = build(args.source.resolve())
        mismatches = []
        for name, content in payload.items():
            destination = ASSET / name
            if args.check:
                if not destination.is_file() or destination.read_bytes() != content:
                    mismatches.append(name)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        for name in LEGACY_FILES:
            path = ASSET / "evidence" / name
            if path.exists():
                if args.check:
                    mismatches.append("obsolete evidence/" + name)
                else:
                    path.unlink()
        if mismatches:
            print("FAILED: evidence differs from the pinned experiment:")
            print("\n".join(" - " + name for name in mismatches))
            return 1
        print(f"PASS: {'verified' if args.check else 'built'} {len(payload)} v1.1.0 files from the pinned result archive.")
        print("No GPU work, fitting, reselection, or exclusion of flagged results was performed.")
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print("FAILED:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
