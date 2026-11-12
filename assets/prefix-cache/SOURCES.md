# Prefix-cache portfolio data

Source repository: https://github.com/ryan30402/vllm-prefix-cache-bench

Pinned source commit: `31bd3f27adc617a32b6c9756b2e1d219f037bd8c`

Report: https://github.com/ryan30402/vllm-prefix-cache-bench/blob/31bd3f27adc617a32b6c9756b2e1d219f037bd8c/analysis/REPORT.md

## Data scope

`reference-summary.csv` and `reference-summary.json` reproduce the six normal-memory conditions in the report's **Clean reference runs (v2 harness)** table. Each cache condition has three repeats. This table summarizes 36 runs; six additional memory-pressure runs bring the reference dataset to 42 runs and 21,000 measured requests. Warm-up requests are excluded from that request count.

All displayed values are rounded in the source report. Throughput gains use the report's stated ratios. This export is a portfolio summary, not a replacement for raw request records. The earlier 150-run exploratory sweep is not pooled into these results.

## Interpretation

One NVIDIA A40, Qwen2.5-7B-Instruct in BF16, vLLM 0.33.0. Synthetic single-prefix requests, 256 suffix tokens and 128 requested output tokens. Closed-loop load begins with a burst. End-to-end latency starts at request send and excludes the client-side concurrency queue. A per-run p99 is summarized across three repeats; it is not a pooled p99 or a production SLO.

Small latency differences should not be interpreted as universal improvements. Output exact-match checks do not establish equal task quality. No new GPU measurements were made to create this page.
