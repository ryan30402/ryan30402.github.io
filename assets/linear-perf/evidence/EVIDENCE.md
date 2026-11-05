# Transformer Linear Layer Performance Predictor

## First-release summary evidence - v1.0.0

This download contains the tables and summaries used by the portfolio's recorded-results explorer. The project repository contains the complete published scientific snapshot, source code, protocol, numerical witnesses, and verification tools.

- [Project repository](https://github.com/ryan30402/transformer-linear-layer-performance-predictor)
- [Pinned source snapshot](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/tree/603fcde80644fe08f2ba502feffc7e58f591a008)
- [Published results and verification guide](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/603fcde80644fe08f2ba502feffc7e58f591a008/results/README.md)
- [Published results manifest](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/603fcde80644fe08f2ba502feffc7e58f591a008/results/MANIFEST.json)
- [Measurement and evaluation protocol](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/603fcde80644fe08f2ba502feffc7e58f591a008/docs/PROTOCOL.md)

The source report is dated November 1, 2026. It covers six sessions on NVIDIA A100-SXM4-40GB GPUs: three FP16 sessions and three BF16 sessions, paired by recorded physical GPU. The same 96 modeling/acquisition shapes repeat across all six sessions.

## What this extract contains

| File | Contents |
| --- | --- |
| `model_metrics.csv` | All five registered models, three evaluation splits, and six sessions: 90 rows |
| `selected_pipeline.csv` | Official models selected using development data and their recorded errors |
| `case_latencies.csv` | All 576 shape-session latency labels |
| `paired_dtype_latencies.csv` | 96 matched shapes across three recorded FP16/BF16 rounds: 288 rows |
| `cross_round_latency_spread.csv` | Per-shape repeatability across three sessions within each dtype |
| `quality_and_audits.csv` | Recorded timing qualifications and acquisition-audit outcomes |
| `frozen_selected_transfer.csv` | Frozen first-session selected models evaluated on subsequent sessions |
| `frozen_krr_candidate_transfer.csv` | A separate descriptive transfer analysis of the registered residual KRR candidate |
| `acquisition_all_budgets.csv` | Offline acquisition results at budgets of 2, 4, 8, and 12 labels |
| `offline_batching.csv` | An offline comparison of 64 small GEMMs with one equal-work larger GEMM |
| `FINAL_SUMMARY.json` | The repository's `results/summary/summary.json`, retained under the website's stable filename |
| `six_session_summary.json` | The repository's `results/summary/cross_session_summary.json`, retained under the website's stable filename |

Every CSV and summary JSON is byte-identical to the corresponding published source file. The website's `results.json` keeps the same numeric observations and Boolean selection flags in a presentation-oriented structure. Changing browser controls filters these recorded values.

## How to interpret the results

The latency target is warm-reuse CUDA Graph replay time per GEMM, measured with CUDA events around 50 captured operations. Replay and inter-kernel gaps remain inside the interval. CPU-GPU transfers, allocation, graph capture, and end-to-end serving are outside it.

`selected_by_development` preserves the original selection. Test and challenge comparisons do not replace it. APE is prediction error relative to measured latency; a percentile of these errors describes matrix shapes, not individual request latencies.

FP16 was measured before BF16 within each round. The paired comparison is descriptive and does not separate precision from runtime order or machine state. Repeated rounds use the same shape sets.

The 5,468 audit checks per session are recorded acquisition-review outcomes. The website does not repeat those audits. BF16 s03 retains control case x03's max/min ratio of 1.1724 under the declared 1.2 gate; passing a timing gate does not establish accurate predictions.

The acquisition pool was already measured before the offline label-reveal study. Its budgets count labels, not GPU time saved. The batching ratio of 25.57-26.72 compares equal offline matrix work and does not measure application-level LLM speedup.

## Provenance and verification

`manifest.json` records the source repository commit, the public dataset manifest's SHA-256, and each file's source path and SHA-256. Its `files` entries authenticate the bytes in this extract. The downloadable ZIP contains the same evidence files and manifest as the website directory.

The summary JSON's `release_source_sha256` and archive hashes identify the recorded acquisition artifacts. They are distinct from the public repository commit and the hashes of these published files. Copying a normalized publication summary does not recreate its original acquisition archive or independently attest GPU execution.

The portfolio checker compares the explorer's values with these CSVs and verifies extract hashes. For the complete publication snapshot, use the repository's `python scripts/verify_published_results.py` as described in its results guide. This smaller download does not contain the full raw timing records, model coefficients, or source release needed by that verifier.

The evidence covers one GPU model and software stack. Hardware-counter explanations, cross-architecture generalization, vendor certification, and prospective accuracy gains are not established by these measurements.
