# ATLAS-THROUGHPUT-008 — release-lane timing

Machine service time, queue admission to verified, for three packages staged serially, each from the release
its predecessor produced.

| release | market | queue | FAST | stage | authorize | activate | verify | handoff | service s |
|---|---|---|---|---|---|---|---|---|---|
| R1 | dayton-oh | 0.0 | 5.5 | 177.9 | 2.3 | 4.20 | 0.02 | 100.2 | **300.4** |
| R2 | cleveland-akron-canton-oh | 0.0 | 12.3 | 198.3 | 2.3 | 2.13 | 0.03 | 103.3 | **327.7** |

| measure | value |
|---|---|
| median service time | **327.7 s** (5.5 min) |
| slowest service time | 327.7 s (5.5 min) |
| all three, end to end | 628.1 s (10.5 min) |
| releases per 8-hour day at the median | **87.9** |

Founder wait is not in these numbers and was zero here, because activation was simulated: there was no
authorization gate to wait at. A real launch adds that wait, and it is reported separately rather than folded
into service time.
