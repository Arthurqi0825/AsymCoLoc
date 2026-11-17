#!/usr/bin/env python3
"""Validate the archived trajectory package without ROS or original rosbags."""

import csv
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "results/real_world_snapshot"
ROUTES = {
    "Suburban 1": ("suburban_1", 388, 1782983050, 1782983437, 0.0, 362),
    "Suburban 2": ("suburban_2", 751, 1782983635, 1782984385, 0.0, 690),
    "Urban 1": ("urban_1", 232, 1780633605, 1780633836, -0.28, 9),
    "Urban 2": ("urban_2", 137, 1780634534, 1780634670, -0.15, 7),
}
METHODS = ("Proposed full", "CR-EKF", "u-blox", "GICI")


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def percentile(values, quantile):
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def check(condition, message):
    if not condition:
        raise ValueError(message)


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.paths.append(dict(attrs)["src"])


def main():
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        check(hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"],
              f"Packaged file hash mismatch: {path}")

    metrics = read_csv(PACKAGE / "metrics.csv")
    check(len(metrics) == 16, "Expected four methods on each of four routes")
    for label, (slug, count, start, end, offset, rtk_count) in ROUTES.items():
        rows = read_csv(PACKAGE / "data" / f"{slug}.csv")
        expected_times = list(range(start, end + 1))
        check(len(expected_times) == count, f"Incorrect window: {label}")
        gt = {float(row["evaluation_time_s"]): (float(row["east_m"]), float(row["north_m"]))
              for row in rows if row["method"] == "Ground truth"}
        check(sorted(gt) == expected_times, f"Ground-truth grid mismatch: {label}")
        check(sum(row["valid"] == "1" for row in rows if row["method"] == "RTKLIB-MB") == rtk_count,
              f"RTKLIB availability mismatch: {label}")
        route_rmse = {}
        for method in METHODS:
            samples = [row for row in rows if row["method"] == method]
            check([float(row["evaluation_time_s"]) for row in samples] == expected_times,
                  f"Common timestamps mismatch: {label}/{method}")
            errors = []
            for row in samples:
                check(row["valid"] == "1", f"Invalid main-method sample: {label}/{method}")
                time = float(row["evaluation_time_s"])
                check((float(row["gt_east_m"]), float(row["gt_north_m"])) == gt[time],
                      f"GT differs between methods: {label}/{method}")
                error = math.hypot(float(row["east_m"]) - gt[time][0],
                                   float(row["north_m"]) - gt[time][1])
                check(math.isfinite(error) and abs(error - float(row["horizontal_error_m"])) < 2e-8,
                      f"Stored error mismatch: {label}/{method}")
                errors.append(error)
            stored_rows = [row for row in metrics if row["sequence"] == label and row["method"] == method]
            check(len(stored_rows) == 1, f"Missing/duplicate metric row: {label}/{method}")
            stored = stored_rows[0]
            check(int(stored["n"]) == count and int(stored["start_unix_s"]) == start
                  and int(stored["end_unix_s"]) == end and float(stored["frozen_gt_offset_s"]) == offset,
                  f"Metric window mismatch: {label}/{method}")
            calculated = {
                "rmse_m": math.sqrt(sum(error**2 for error in errors) / count),
                "mae_m": sum(errors) / count,
                "min_m": min(errors), "median_m": percentile(errors, 0.5),
                "p95_m": percentile(errors, 0.95), "max_m": max(errors),
            }
            for key, value in calculated.items():
                check(abs(float(stored[key]) - value) < 2e-8,
                      f"Metric mismatch: {label}/{method}/{key}")
            route_rmse[method] = calculated["rmse_m"]
        proposed = next(row for row in metrics if row["sequence"] == label and row["method"] == "Proposed full")
        improvement = 100 * (route_rmse["CR-EKF"] - route_rmse["Proposed full"]) / route_rmse["CR-EKF"]
        check(abs(float(proposed["proposed_rmse_reduction_vs_cr_ekf_percent"]) - improvement) < 2e-6,
              f"Improvement mismatch: {label}")
        print(f"OK: {label}, N={count}, RMSE={route_rmse['Proposed full']:.3f} m, reduction={improvement:.2f}%")

    audits = read_csv(PACKAGE / "repeat_replay_audit.csv")
    check(len(audits) == 8 and all(row["method"] == "proposed" for row in audits),
          "Expected both Proposed replay audits for all four routes")
    for slug, *_ in ROUTES.values():
        check(sorted(row["repeat"] for row in audits if row["route"] == slug) == ["1", "2"],
              f"Missing repeat audit: {slug}")

    text = (ROOT / "README.md").read_text()
    parser = Images()
    parser.feed(text)
    references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text) + parser.paths
    check(len(references) == 7, "Expected seven README images")
    for path in references:
        check(path.endswith(".jpg") and (ROOT / path).is_file(), f"Missing JPG reference: {path}")
    print("OK: all archived file hashes, 16 metric rows, eight replay audits and seven README JPG references")


if __name__ == "__main__":
    main()
