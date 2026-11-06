# Transformer Linear Layer Performance Predictor: v1.1.0 website evidence

This is a small, reproducible extract of the A100 experiment recorded on 2026-11-06.
It contains archived tables and derived presentation data. It does not run a GPU benchmark or refit a model.

## Source and scope

- Publication commit: [59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/tree/59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911).
- [Complete original result archive](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/raw/59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911/experiments/a100_20261106/results.zip) (11,255,177 bytes).
- Original result archive SHA-256: `a601e14bb3d1d2b661f06021432b461104850452ddcc1c695c55006db29374b1`.
- Embedded measurement-source archive SHA-256: `1f748883a23d0e9706856493eb011eec88d5e3f8926fafd3874c5d23d2c8345a`.
- [Results and limitations](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911/docs/RESULTS.md).
- [Protocol](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911/docs/PROTOCOL.md).
- [Published review](https://github.com/ryan30402/transformer-linear-layer-performance-predictor/blob/59a6cc5aa126abbe4b0b64eb9f1e1ecedae4c911/experiments/a100_20261106/review.html).

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
