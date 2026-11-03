<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole compared with other pressure insoles

**Basis.** For the other insoles, everything below comes from the project's comparison corpus: the research
report "Open-Source Alternatives to Moticon OpenGo Sensor Insoles", last verified 2026-11-02. We have tested
none of them. For our sole, every figure is a **design goal or a geometric estimate**: nothing has been built or
measured. Passing `verify_board.py` is a software check of the copper, not sensing accuracy.

Three kinds of statement, kept apart:
- **Documented:** stated by the vendor or project (specification, README, paper), as the corpus reports it.
- **Measured:** a result against a reference instrument (force plate, Pedar-X, motion capture), as the corpus
  cites it.
- **Not documented:** the corpus does not say. Toe pockets and five-toe fit are not documented for any project
  below. That is unknown, not "absent".

## Documented features

| | Our sensor sole (design goals) | Moticon OpenGo | JunjianChi/smartinsole | KAKI Smart Insole | GRFMS |
|---|---|---|---|---|---|
| Sensing | Shunt-mode piezoresistive film over interdigitated combs; film not yet chosen | Capacitive textile sensors | Velostat sheet over a flex-circuit electrode grid | Capacitive (MPR121) through a TPU gyroid footbed | FlexiForce A301 piezoresistive sensors |
| Channels | 16 regions (14 on the synthetic personal sole); pod v1 up to 32 | 16 | 253 (33 × 15 grid, 7.5 mm pitch) | 12 | 14 per insole |
| Coverage of the sole | 75–80 % (geometric estimate from the generator) | 62.5–67.4 % (size-dependent) | Not documented as a percentage; foot-shaped grid | Not documented | Not documented; discrete sensors |
| Toes, toe pockets, five-toe shoes | Five toe tabs, each toe its own region; designed for a five-toe shoe | Not documented (9 double sizes) | Not documented | Not documented | Not documented |
| Sizes, personalisation | Any length and width; personal outline from foot landmarks | 9 double sizes | Not documented | Not documented | Not documented |
| Wiring of the sensors | One sense line per region, no crossbar | Not documented | Crossbar; crosstalk compensation in the 2026 paper | Not documented | Multiplexer (74HC4067) |
| In the shoe | Passive flex, about 0.35–0.40 mm stack (proposed); all electronics in a pod outside | Electronics in the insole, coin cells | ESP32 board, IMU | Passive footbed; reusable pod on the shoe | ESP32 nodes, SD card |
| Motion sensor | 6-axis IMU in the pod (planned) | 6-axis | 6-axis | 9-DOF | None |
| Rate | 100 Hz (target) | 10–100 Hz | 60 Hz (30 Hz dual-frame) | 100 Hz | 100 Hz |
| Recording, radio | microSD and BLE (planned) | 32 MB on board; BLE | Wi-Fi; no on-board storage | BLE; no on-board storage | SD card; no radio |
| Left/right sync | Crystals plus a hardware sync input (planned, to verify) | < 0.006 % drift | Host-side | None documented (single foot) | Master/slave |
| Calibration | Per region on our bench (planned) | Factory, lifetime; auto-zeroing | Research lookup table | Not documented | Per sensor |
| Load cycles | Not known; bend test planned | ≥ 100,000 | Not documented | Not documented | Not documented |
| Licence | CERN-OHL-S-2.0 | Commercial | MIT | MIT | CC BY 4.0 |

## Measured performance

| | Measured against a reference | Result as reported |
|---|---|---|
| **Our sensor sole** | **Nothing.** No board made, no film chosen, no calibration | — |
| OpenGo | Earlier 13-sensor versions, by independent groups, against force plates and Pedar-X (Stoeggl et al. 2016; Oerbekke et al. 2016) | High correlations (r ≈ 0.8–1.0) for most temporal and force variables; force peaks underestimated, with latency in fast motions. The current 16-sensor version has manufacturer specifications (≤ 1 % hysteresis, < 5 % total-force error) and internal validation, not independent results in the corpus |
| smartinsole | Two IEEE ISCAS papers (2025, 2026) | Force-plate error metrics not published in the README |
| KAKI | 10 m walk tests: 3 participants, 5 sessions, footstrike checked visually | Gait events only; no pressure range or calibration published |
| GRFMS | Ground reaction force against a reference, with Vicon motion capture | GRF estimation fit 68.71 % ± 4.80 % |

## What this means for our sole

**Where the design aims further (goals, not results):**
- **Five-toe fit,** with each toe sensed. None of the corpus projects documents this; whether any of them
  could be adapted to it is unknown.
- **Coverage.** Our geometric estimate is above OpenGo's documented coverage. That helps total force and
  centre of pressure. Whether the covered area actually senses evenly is for the coupon test.
- **Any size and personal outlines,** generated rather than drawn.
- **One line per region,** so there is no crossbar crosstalk to compensate. Spatial resolution is much lower
  than smartinsole's 253 cells, though: a pressure peak cannot be located within a region.
- **A passive, thin sole** with every component outside the shoe. KAKI documents the same split, and the same
  XIAO nRF52840 Sense pod.

**Where it is behind:**
- **Nothing measured.** Each alternative above has at least some measurement; OpenGo has independent
  validation of earlier versions.
- **Accuracy is open.** Piezoresistive films (Velostat class) are known for hysteresis, creep and temperature
  drift. Until our coupon test and force-plate comparison report numbers, assume nothing better than the DIY
  piezoresistive insoles.
- **Electronics, power, synchronisation and software** are designed but not built.
