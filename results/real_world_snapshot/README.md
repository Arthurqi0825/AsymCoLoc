# Archived real-world experimental results

This package presents existing experiments, not a new estimator replay. Trajectory
images are white-background JPEG conversions of the saved
`results/paper_plot_export_20260915_194457/figures/*_trajectory.png` figures.
Their paired sample CSVs come from that same export. The platform image comes
from `paper/figures/experiment_setup.png`. No trajectories were redrawn or fitted
to ground truth when preparing this package.

## Evaluation protocol

Coordinates describe the target navigation/IMU center in the frozen local
East–North frame for each route. Horizontal error is the Euclidean distance
between estimated and ground-truth East/North positions. All four main methods
use the same 1-Hz evaluation timestamps after initialization. The dataset-level
GT offsets below are frozen and shared by every method.

| Sequence | N | Start (Unix UTC s) | End (Unix UTC s) | GT offset (s) |
| --- | ---: | ---: | ---: | ---: |
| Suburban 1 | 388 | 1782983050 | 1782983437 | 0.00 |
| Suburban 2 | 751 | 1782983635 | 1782984385 | 0.00 |
| Urban 1 | 232 | 1780633605 | 1780633836 | -0.28 |
| Urban 2 | 137 | 1780634534 | 1780634670 | -0.15 |

The segment duration is end minus start; inclusive 1-Hz sample counts are one
greater. Embedded sensor epochs, rather than rosbag arrival times, define the
comparison. Proposed and CR-EKF use saved keyframes on the grid; the archived
u-blox and GICI exports use unique nearest outputs within 0.01 s and 0.11 s,
respectively. Source timestamps and time differences remain in each sample CSV.
Suburban antenna-to-navigation-center corrections use the archived calibrated
lever arm and saved GT attitude. No fitted trajectory alignment is performed.

## Inputs and interpretation

- Proposed uses recorded physical GNSS, target IMU, and UWB. A postprocessed
  reference SPAN navigation trajectory supplies reference-prior means; these
  experiments do not establish performance with an online reference solution.
- Suburban 1/2 use at most the first second of target GT for initialization and
  fixed UWB-bias calibration. Urban 1/2 use raw-PVT initialization. Target GT
  is not inserted as a graph factor after initialization. There are no
  full-trajectory GT-derived synthetic UWB measurements in this package.
- CR-EKF is an offline conditioned-reference cooperative EKF using a saved
  bag-derived PVT/IMU/UWB event cache. Proposed additionally uses moving-base DD
  GNSS and a different reference-state treatment. Their comparison evaluates
  complete estimators and does not isolate smoothing versus filtering.
- GICI LC denotes the loosely coupled configuration. No invalid GICI tightly
  coupled result is presented as an accuracy baseline.
- RTKLIB-MB has valid outputs at only 362/388, 690/751, 9/232, and 7/137 epochs.
  Its unconnected markers retain this availability limitation. It is excluded
  from the four-method full-grid statistics, and its sparse Urban outputs do
  not represent whole-route accuracy. Missing positions remain empty.
- These Urban 1/2 physical-input snapshots have RMSEs of 1.846 m and 1.471 m;
  they do not pass the requirement that both periods be below 1.5 m.

## Saved statistics and provenance

[`metrics.csv`](metrics.csv) contains all 16 route/method rows, each with sample
count, evaluation start/end, frozen GT offset, horizontal RMSE, MAE, minimum,
median, P95, maximum, validity, and input provenance. Values are recomputed
from the packaged East/North coordinates and checked against the saved source
RMSEs within 2e-8 m. The Proposed percentage reduction is
`100 * (CR-EKF RMSE - Proposed RMSE) / CR-EKF RMSE`, using full precision.
Small percentage differences from rounded manuscript values are expected.

[`data/`](data) preserves the archived per-epoch rows for Ground truth,
Proposed full, CR-EKF, u-blox, GICI LC, and RTKLIB-MB. The separate matched-input
FGO diagnostic is omitted. Proposed Suburban 1 comes from
`replay_consistency_suburban1_1x_retry_20260915`; the other Proposed routes come
from `dd_covariance_B_remaining_1x_frozen_20260915`. These source replays use 1x
playback. No UWB ablation or synthetic-range experiment is packaged here.

[`manifest.json`](manifest.json) records source workspace paths, source file
SHA-256 values, packaged file SHA-256 values, and conversion/filtering steps.
Source paths identify the internal archive; they are not public download links.
The original raw rosbags and estimator implementation are not included.

## Replay variability

[`repeat_replay_audit.csv`](repeat_replay_audit.csv) preserves both Proposed
replays from the subsequent `journal_tim_repeatability_20261105` audit,
including their full error statistics, factor counts, and input provenance.
No best repeat is selected. The online estimator is sensitive to callback
ordering, and later replays do not reproduce every historical metric exactly.
This limitation applies to the archived results shown in the project README.

Validate this package from the repository root with Python 3 (standard library
only):

```bash
python3 tools/verify_experiment_snapshot.py
```
