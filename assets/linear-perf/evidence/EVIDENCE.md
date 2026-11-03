# Linear Perf Lab v0.4 — public evidence extract

This is a curated, English-language extract of the supplied six-session results package, not a new experiment or the full raw archive.

## Provenance

- Supplied package: `linear-perf-lab-v0.4.0_REAL_RESULTS.zip`.
- Source report date: November 1, 2026.
- Experiment: NVIDIA A100-SXM4-40GB; FP16 and BF16; three rounds per dtype.
- All six original result-archive SHA-256 values were checked against the supplied `FINAL_SUMMARY.json` when this extract was built.
- The CSV and summary JSON files in this directory are copied without numerical modification.
- The website's `results.json` is a presentation-oriented serialization of these same tables.
- This extract omits raw traces, the full source release, and the original non-English documents. Original archive identities are retained in `FINAL_SUMMARY.json`.

## Reading the evidence

`model_metrics.csv` includes all five registered models, three evaluation splits, and six sessions (90 rows). `selected_by_development` preserves the original selection; comparisons on test/challenge do not change it.

`paired_dtype_latencies.csv` includes 96 matched shapes across three rounds (288 rows). The same shapes recur; they are not 288 independently unseen shapes. Latency is warm-reuse CUDA graph replay elapsed time per GEMM, not end-to-end application latency. FP16 ran before BF16 within each round.

`quality_and_audits.csv` records the supplied audit outcomes, not an independent audit performed by this website. The BF16 s03 x03 control max/min ratio is 1.1724 under a predeclared 1.2 gate. It was retained unchanged.

`offline_batching.csv` compares 64 small GEMMs with one equal-work larger GEMM. The observed 25.57–26.72 ratio excludes queueing and end-to-end serving. It is not an LLM application speedup.

`FINAL_SUMMARY.json` distinguishes the selected pipeline, candidate comparisons, frozen-model transfer, and limitations. `six_session_summary.json` describes the three per-session results; summaries are not population confidence intervals.

No cross-architecture validation, hardware-counter explanation, NVIDIA certification, or prospective accuracy improvement is claimed.
