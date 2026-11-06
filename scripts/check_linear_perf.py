#!/usr/bin/env python3
"""Validate the static v1.1.0 publication without rerunning GPU measurements."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets/linear-perf"
SPLITS = ("train", "test", "challenge", "stress")
METRIC_KEYS = {
    "weighted_mean_ape_pct": "weighted_mean_ape_pct",
    "mean_ape_pct": "mean_ape_pct",
    "median_ape_pct": "median_ape_pct",
    "p90_ape_pct": "p90_ape_pct",
    "worst_ape_pct": "max_ape_pct",
}
errors = []


def require(condition, message):
    if not condition:
        errors.append(message)


def close(actual, expected, message):
    require(math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10), message)


def counts(rows):
    counter = Counter(row["split"] for row in rows)
    return {split: counter[split] for split in SPLITS}


def read_csv(name):
    with (ASSET / "evidence" / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def metric_key(row, *, csv_row=False):
    return (row["group_id" if csv_row else "context_id"], row["split"], row["model_id"])


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.categories = []
        self.h1_count = 0
        self.lang = None
        self.cards = []
        self.card = None
        self.card_depth = 0
        self.card_bold = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "h1":
            self.h1_count += 1
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if attrs.get("data-category"):
            self.categories.append(attrs["data-category"])
        key = "href" if tag in ("a", "link") else "src" if tag in ("img", "script") else None
        if key and attrs.get(key):
            self.links.append(attrs[key])
        if tag == "div" and "lp-mini-row" in attrs.get("class", "").split():
            self.card = {"context_id": attrs.get("data-context"), "value": "", "width": None}
            self.card_depth = 1
        elif tag == "div" and self.card is not None:
            self.card_depth += 1
        if tag == "b" and self.card is not None:
            self.card_bold = True
        if tag == "i" and self.card is not None:
            match = re.search(r"width\s*:\s*([\d.]+)%", attrs.get("style", ""))
            if match:
                self.card["width"] = float(match.group(1))

    def handle_endtag(self, tag):
        if tag == "b":
            self.card_bold = False
        if tag == "div" and self.card is not None:
            self.card_depth -= 1
            if self.card_depth == 0:
                self.cards.append(self.card)
                self.card = None

    def handle_data(self, data):
        if self.card is not None and self.card_bold:
            self.card["value"] += data


def check_pages(data):
    pages = {}
    for path in sorted(ROOT.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        page = Page()
        page.feed(text)
        pages[path.resolve()] = page
        name = str(path.relative_to(ROOT))
        require(page.lang == "en", name + ": expected English HTML")
        require(page.h1_count == 1, name + ": expected exactly one H1")
        require(len(page.ids) == len(set(page.ids)), name + ": duplicate HTML IDs")
        require(not re.search(r"[\u3400-\u9fff]", text), name + ": non-English page content")
        require(not re.search(r"coming\s+soon|InferScale|TraceGuard|School of General Studies", text, re.I), name + ": retired content remains")

    for path, page in pages.items():
        for url in page.links:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            if not parts.path:
                target = path
            elif parts.path.startswith("/"):
                target = ROOT / unquote(parts.path).lstrip("/")
            else:
                target = path.parent / unquote(parts.path)
            if target.is_dir():
                target /= "index.html"
            target = target.resolve()
            require(target.is_file(), str(path.relative_to(ROOT)) + ": missing target " + url)
            if parts.fragment and target in pages:
                require(unquote(parts.fragment) in pages[target].ids, str(path.relative_to(ROOT)) + ": missing anchor " + url)

    expected_cards = {row["context_id"]: row["weighted_mean_ape_pct"] for row in data["selected_metrics"] if row["split"] == "test"}
    for filename in ("index.html", "projects/index.html"):
        path = ROOT / filename
        cards = pages[path.resolve()].cards
        require(len(cards) == 4, filename + ": expected four current result bars")
        require({card["context_id"] for card in cards} == set(expected_cards), filename + ": incorrect result contexts")
        for card in cards:
            if card["context_id"] not in expected_cards:
                continue
            expected = expected_cards[card["context_id"]]
            require(card["value"].strip() == f"{expected:.2f}%", filename + ": card differs from archived weighted mean APE")
            require(card["width"] is not None and abs(card["width"] - expected / 12 * 100) < 0.0001, filename + ": bar width differs from the fixed 12% scale")
        text = path.read_text(encoding="utf-8")
        require("Ordinary-test weighted mean APE" in text, filename + ": card metric is not explicitly labelled")
        require("v1.1.0" in text and "v1.0.0" not in text, filename + ": stale project release")

    detail = (ROOT / "projects/linear-perf-lab/index.html").read_text(encoding="utf-8")
    require("v1.1.0" in detail and "v1.0.0" not in detail, "Project page: stale release")
    require("fp16_s01" not in detail and "bf16_s03" not in detail, "Project page: obsolete session data")
    require(sorted(pages[(ROOT / "projects/index.html").resolve()].categories) == ["learning", "systems"], "Expected the two existing project categories")
    require("/projects/linear-perf-lab/" in (ROOT / "sitemap.xml").read_text(), "Project route absent from sitemap")
    require((ROOT / "README.md").read_text().strip() == "This is my portfolio website: https://ryan30402.github.io/", "README differs from the existing single-line format")


def check_data(data):
    require(data["schema_version"] == 2, "Expected result schema 2")
    require(data["provenance"]["protocol_version"] == "1.1.0", "Expected v1.1.0 evidence")
    require(len(data["models"]) == 5 and len({row["id"] for row in data["models"]}) == 5, "Expected five unique candidate models")
    require(len(data["contexts"]) == 4, "Expected four precision/buffer contexts")
    require(len(data["metrics"]) == 60, "Expected 60 candidate metric rows")
    require(len(data["selected_metrics"]) == 12, "Expected 12 selected-model rows")
    require(len({metric_key(row) for row in data["metrics"]}) == len(data["metrics"]), "Duplicate model metric row")
    source_rows = read_csv("model_metrics.csv")
    original = {metric_key(row, csv_row=True): row for row in source_rows}
    require(len(original) == 60, "Expected 60 unique archived metric rows")
    for row in data["metrics"]:
        key = metric_key(row)
        require(key in original, "Result row absent from archived metric table")
        if key not in original:
            continue
        source = original[key]
        require((row["dtype"], row["cache_policy"], row["n_cases"], row["selected_by_cv"]) == (source["dtype"], source["cache_policy"], int(source["n"]), source["selected_by_cv"] == "True"), "UI context/selection/count differs from archived metrics")
        for target_key, source_key in METRIC_KEYS.items():
            close(row[target_key], float(source[source_key]), "UI metric differs from archived CSV: " + str(key) + " " + target_key)
            require(row[target_key] >= 0, "Negative prediction error")
        require(row["median_ape_pct"] <= row["p90_ape_pct"] <= row["worst_ape_pct"], "Invalid unweighted error quantiles")
    selected_source = {metric_key(row, csv_row=True): row for row in read_csv("selected_model_metrics.csv")}
    selected_data = {metric_key(row): row for row in data["selected_metrics"]}
    require(set(selected_source) == set(selected_data), "Selected CSV and JSON cover different contexts/splits")
    require(selected_data == {metric_key(row): row for row in data["metrics"] if row["selected_by_cv"]}, "Selected metrics differ from the unchanged CV selection")
    for key, row in selected_data.items():
        for target_key, source_key in METRIC_KEYS.items():
            close(row[target_key], float(selected_source[key][source_key]), "Selected metric differs from archived selected-model CSV")

    flat_cases = []
    for family in data["sampling"]["families"]:
        require(family["count"] == len(family["cases"]), "Sampling family count mismatch")
        require(family["split_counts"] == counts(family["cases"]), "Sampling family split counts mismatch")
        require(family["rotation_count"] == sum(row["rotation_eligible"] for row in family["cases"]), "Sampling family rotation count mismatch")
        require(family["repeat_count"] == sum(row["repeat"] for row in family["cases"]), "Sampling family repeat count mismatch")
        for case in family["cases"]:
            require(case["id"] == f"m{case['m']}_n{family['n']}_k{family['k']}", "Case ID disagrees with M,N,K")
            require(case["split"] in SPLITS and case["weight"] > 0, "Invalid shape split or declared weight")
            require(not family["challenge"] or case["split"] == "challenge", "Challenge family contains training/test shapes")
            require(family["kind"] != "stress" or case["split"] == "stress", "Stress family contains ordinary shapes")
            flat_cases.append({"case_id": case["id"], "family": family["id"], "m": case["m"], "n": family["n"], "k": family["k"], **{k: case[k] for k in ("split", "weight", "repeat", "rotation_eligible", "coverage")}})
    cases = {row["case_id"]: row for row in flat_cases}
    require(len(cases) == len(flat_cases) == 609, "Expected 609 unique retained shapes")
    require(len(data["sampling"]["families"]) == 41, "Expected 29 retained architecture and 12 stress families")
    require(counts(flat_cases) == {"train": 311, "test": 134, "challenge": 118, "stress": 46}, "Incorrect primary split counts")
    require(data["summary"]["split_counts"] == data["sampling"]["split_counts"] == counts(flat_cases), "Summary differs from actual sampling cases")
    require(data["summary"]["primary_shapes"] == len(cases), "Primary shape summary mismatch")
    rotated = [row for row in flat_cases if row["rotation_eligible"]]
    repeated = [row for row in flat_cases if row["repeat"]]
    require(counts(rotated) == {"train": 266, "test": 113, "challenge": 100, "stress": 40}, "Incorrect rotation-eligible split counts")
    require(len(repeated) == data["summary"]["repeat_shapes"] == 77, "Incorrect repeat subset size")
    require(data["sampling"]["repeat_split_counts"] == counts(repeated) == {"train": 39, "test": 18, "challenge": 15, "stress": 5}, "Incorrect repeat stratification counts")
    require(len([row for row in repeated if row["rotation_eligible"]]) == 63, "Incorrect rotating repeat cohort")
    require(data["sampling"]["exclusions"]["memory_budget"] == 38 and data["sampling"]["exclusions"]["previously_exposed"] == 1, "Incorrect planning exclusion counts")
    require(len(data["sampling"]["exclusions"]["cases"]) == 39, "Missing explicit planning exclusions")
    train_families = {row["family"] for row in flat_cases if row["split"] == "train"}
    require({row["family"] for row in flat_cases if row["split"] == "test"} <= train_families, "Ordinary test includes a family absent from training")
    require(not {row["family"] for row in flat_cases if row["split"] == "challenge"} & train_families, "Challenge family leaks into training")
    sampling_csv = {row["case_id"]: row for row in read_csv("sampling_cases.csv")}
    require(set(sampling_csv) == set(cases), "Sampling CSV and JSON cover different cases")
    for key, row in cases.items():
        source = sampling_csv[key]
        require(all(int(source[k]) == row[k] for k in ("m", "n", "k")), "Sampling dimensions differ from CSV")
        require(all(source[k] == row[k] for k in ("family", "split", "coverage")), "Sampling assignment differs from CSV")
        require(all((source[k] == "True") == row[k] for k in ("repeat", "rotation_eligible")), "Sampling cohort differs from CSV")
        close(row["weight"], float(source["weight"]), "Declared sample weight differs from CSV")

    selection = read_json(ASSET / "evidence/model_selection.json")
    require(data["selection"] == selection, "UI selection metadata differs from evidence")
    require(selection["heldout_labels_used_for_selection"] is False, "Held-out labels were used for selection")
    require(selection["test_labels_measured_before_fitting"] is True, "Measurement chronology is misstated")
    require(selection["repeat_labels_used_for_refit"] is False, "Repeat labels were used for refitting")
    selection_by_context = {row["context_id"]: row for row in selection["groups"]}
    total_rows = 0
    for context in data["contexts"]:
        cohort = flat_cases if context["cache_policy"] == "warm_reuse" else rotated
        require(context["split_counts"] == counts(cohort), "Context split counts differ from eligible cases")
        require(context["primary_count"] == len(cohort), "Context primary count differs from eligible cases")
        require(context["repeat_count"] == sum(row["repeat"] for row in cohort), "Context repeat count differs from actual subset")
        total_rows += len(cohort)
        chosen = selection_by_context[context["id"]]
        require(chosen["selected_model_id"] == context["selected_model_id"] == "roofline_residual_krr", "Displayed selection differs from archived CV selection")
        require(chosen["folds"] == context["cv_folds"] == 6 and chosen["configurations"] == 19, "Incorrect training CV setup")
        require(chosen["selection_score_key"] == "weighted_mean_ape_pct", "Incorrect model-selection objective")
        require(chosen["training_shapes"] == context["train_count"] == counts(cohort)["train"], "Incorrect training size")
        for split in ("test", "challenge", "stress"):
            rows = [row for row in data["metrics"] if row["context_id"] == context["id"] and row["split"] == split]
            require(len(rows) == 5, "Missing candidate in a context/split")
            require(sum(row["selected_by_cv"] for row in rows) == 1, "Expected one CV-selected candidate per context/split")
            require(all(row["n_cases"] == context["split_counts"][split] for row in rows), "Metric shape count differs from sampling cohort")
    require(total_rows == data["summary"]["primary_rows"] == 2256, "Primary precision/cache row total mismatch")

    pairs = read_csv("repeat_comparison.csv")
    require(len(pairs) == data["summary"]["repeat_rows"] == 280, "Incorrect repeat pair count")
    require(len({(row["context_id"], row["case_id"]) for row in pairs}) == len(pairs), "Duplicate repeat pair")
    repeat_csv = {row["context_id"]: row for row in read_csv("repeat_summary.csv")}
    for summary in data["repeat_contexts"]:
        rows = [row for row in pairs if row["context_id"] == summary["context_id"]]
        require(len(rows) == summary["paired_shapes"], "Repeat summary count mismatch")
        changes = []
        for row in rows:
            require(cases[row["case_id"]]["repeat"], "Repeat pair absent from predetermined subset")
            require(cases[row["case_id"]]["split"] == row["split"], "Repeat split assignment changed")
            source, target = float(row["source_ms"]), float(row["target_ms"])
            require(source > 0 and target > 0, "Nonpositive latency in repeat comparison")
            close(float(row["target_over_source"]), target / source, "Repeat latency ratio mismatch")
            close(float(row["absolute_change_pct"]), 100 * abs(target - source) / source, "Repeat percentage-change arithmetic mismatch")
            changes.append(float(row["absolute_change_pct"]))
        changes.sort()
        position = (len(changes) - 1) * 0.9
        p90 = changes[math.floor(position)] + (changes[math.ceil(position)] - changes[math.floor(position)]) * (position % 1)
        for field, expected in (("median_absolute_change_pct", statistics.median(changes)), ("p90_absolute_change_pct", p90), ("maximum_absolute_change_pct", max(changes))):
            close(summary[field], expected, "Repeat summary differs from paired observations: " + field)
            close(summary[field], float(repeat_csv[summary["context_id"]][field]), "Repeat summary CSV differs from JSON")
        require(summary["pairs_above_10pct"] == sum(value > 10 for value in changes), "Incorrect repeat outlier count")
    require(data["summary"]["same_physical_gpu_verified"] is True, "Repeat hardware identity claim differs from evidence")

    quality = read_json(ASSET / "evidence/quality_summary.json")
    require(data["quality"] == quality, "UI quality metadata differs from evidence")
    require(data["summary"]["measurement_quality_passed"] is quality["measurement_quality_passed"] is False, "Overall timing-quality failure is hidden")
    require(quality["thresholds"] == {"quality_cv_pct": 10.0, "quality_visit_ratio": 1.2, "quality_control_ratio": 1.2}, "Declared timing-quality thresholds changed")
    require(quality["primary"]["flagged_rows_count"] == len(quality["primary"]["flagged_rows"]) == 6, "Primary timing flags are missing")
    require(quality["primary"]["flagged_split_counts"] == {"train": 3, "test": 0, "challenge": 2, "stress": 1}, "Quality flags assigned to incorrect splits")
    require(quality["repeat"]["flagged_rows_count"] == 0 and len(quality["repeat"]["failing_control_groups"]) == 1, "Repeat timing qualification is missing")
    require(quality["primary_flagged_rows_in_repeat"] == 0, "Repeat is incorrectly presented as resolving primary timing flags")
    require(data["measurement"] == read_json(ASSET / "evidence/measurement_contract.json"), "Measurement contract differs from evidence")
    require(data["measurement"]["layer_experiment_status"] == "not_requested", "An unrun decoder-layer experiment is being claimed")
    require(data["provenance"] == read_json(ASSET / "evidence/provenance.json"), "Provenance differs between UI and evidence")


def check_hashes():
    manifest = read_json(ASSET / "evidence/manifest.json")
    expected_paths = set(manifest["files"]) | {"evidence/manifest.json", "linear-perf-evidence.zip"}
    actual_paths = {str(path.relative_to(ASSET)) for path in ASSET.rglob("*") if path.is_file()}
    require(actual_paths == expected_paths, "Evidence folder contains missing or obsolete files: " + str(sorted(actual_paths ^ expected_paths)))
    for name, expected in manifest["files"].items():
        path = ASSET / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Evidence hash mismatch: " + name)
    with zipfile.ZipFile(ASSET / "linear-perf-evidence.zip") as archive:
        require(set(archive.namelist()) == expected_paths - {"linear-perf-evidence.zip"}, "Download ZIP has missing or obsolete members")
        require(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate ZIP member")
        for name in archive.namelist():
            require(archive.read(name) == (ASSET / name).read_bytes(), "Download ZIP differs from published file: " + name)
    require("assets/linear-perf/** -text" in (ROOT / ".gitattributes").read_text(), "Exact-byte evidence is missing its Git line-ending protection")
    for path in ASSET.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".csv", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        require(not re.search(r"[\u3400-\u9fff]", text), str(path.relative_to(ROOT)) + ": private-language material in public extract")
        require(not re.search(r"/workspace/|/content/|AI[- ]assisted|job[- ]seek|v0\.[1234]", text, re.I), str(path.relative_to(ROOT)) + ": unintended local or retired publication content")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-only", action="store_true", help="Check the evidence before HTML integration is complete")
    args = parser.parse_args()
    try:
        data = read_json(ASSET / "results.json")
        check_data(data)
        check_hashes()
        if not args.data_only:
            check_pages(data)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        errors.append(str(error))
    if errors:
        print("FAILED:")
        for error in errors:
            print(" -", error)
        return 1
    print("PASS: 60 candidate metrics, 12 selected summaries, 609 shapes, 280 repeat pairs, CV selection, quality qualifications, exact CSV values, hashes, and download ZIP.")
    if not args.data_only:
        print("PASS: English HTML, routes/anchors, current project cards, and archived card values.")
    print("Publication consistency checks only; no GPU measurements were rerun.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
