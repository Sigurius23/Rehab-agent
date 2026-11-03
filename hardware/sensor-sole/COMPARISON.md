<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole compared with other pressure insoles

**Basis.** For the other insoles, the documented features come from the project's comparison corpus: the
research report "Open-Source Alternatives to Moticon OpenGo Sensor Insoles", last verified 2026-11-02. For
OpenGo, they also come from Moticon's current product page and from three validation papers, all read on
2026-11-03 (section "OpenGo: what was validated, and on which hardware"). We have tested none of these
insoles. For our sole, every figure is a **design goal or a geometric estimate**: nothing has been built or
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
| Coverage of the sole | 75–80 %: region outlines as a share of the sole outline, toe tabs included (geometric estimate) | 62.5–67.4 %, size-dependent (corpus); "65% area coverage" (product page); definition not stated | Not documented as a percentage; foot-shaped grid | Not documented | Not documented; discrete sensors |
| Toes, toe pockets, five-toe shoes | Five toe tabs, each toe its own region; designed for a five-toe shoe | Not documented (9 double sizes) | Not documented | Not documented | Not documented |
| Sizes, personalisation | Generator capability: an EU size, a measured length and width, or a personal outline from landmarks. Generated and checked: EU 37, 42, 46 and one synthetic foot; fit not demonstrated | 9 double sizes, "covering 98% of adult sizes" (product page) | Not documented | Not documented | Not documented |
| Wiring of the sensors | One sense line per region, no crossbar | Not documented | Crossbar; crosstalk compensation in the 2026 paper | Not documented | Multiplexer (74HC4067) |
| In the shoe | Passive flex, about 0.35–0.40 mm stack (proposed); all electronics in a pod outside | Electronics in the insole, coin cells | ESP32 board, IMU | Passive footbed; reusable pod on the shoe | ESP32 nodes, SD card |
| Motion sensor | 6-axis IMU in the pod (planned) | 6-axis IMU (current product) | 6-axis | 9-DOF | None |
| Rate | 100 Hz (target) | 10–100 Hz | 60 Hz (30 Hz dual-frame) | 100 Hz | 100 Hz |
| Recording, radio | microSD and BLE (planned) | 32 MB on board; BLE | Wi-Fi; no on-board storage | BLE; no on-board storage | SD card; no radio |
| Left/right sync | Crystals plus a hardware sync input (planned, to verify) | < 0.006 % drift | Host-side | None documented (single foot) | Master/slave |
| Calibration | Per region on our bench (planned) | Factory, lifetime; auto-zeroing; firmware updatable through the app | Research lookup table | Not documented | Per sensor |
| Load cycles | Not known; bend test planned | ≥ 100,000 | Not documented | Not documented | Not documented |
| Licence | CERN-OHL-S-2.0 | Commercial | MIT | MIT | CC BY 4.0 |

## Measured performance

| | Measured against a reference | Result as reported |
|---|---|---|
| **Our sensor sole** | **Nothing.** No board made, no film chosen, no calibration | — |
| OpenGo | Three independent studies, all on the earlier **13-sensor** insoles (next section) | Timing agrees well with force plates. Force is underestimated, more so at higher forces and in fast motions. Medio-lateral centre of pressure is less reliable than anterior–posterior. **No independent validation of the current 16-sensor product was found**; its figures (≤ 1 % hysteresis, < 5 % total-force error) are the manufacturer's |
| smartinsole | Two IEEE ISCAS papers (2025, 2026) | Force-plate error metrics not published in the README |
| KAKI | 10 m walk tests: 3 participants, 5 sessions, footstrike checked visually | Gait events only; no pressure range or calibration published |
| GRFMS | Ground reaction force against a reference, with Vicon motion capture | GRF estimation fit 68.71 % ± 4.80 % |

## OpenGo: what was validated, and on which hardware

| | Stöggl & Martiner, J Sports Sci 2017 (online 2016) | Braun et al., J Foot Ankle Res 2015 | Rowing study, PMC8036524 (2021) |
|---|---|---|---|
| Task | Slow and fast walking and running on a 15 m walkway; standing, countermovement and drop jumps; three cross-country-skiing imitation drills; two balance tests | Treadmill walking at 1.0 and 1.7 m/s (3 × 3 min each); 30 steps on the plate | Four 500 m trials on a Concept2 rowing ergometer |
| Sample | 16 healthy sport-science students (2 female, 14 male), 31 ± 10 years | 12 healthy adults, 18–37 years | 19 rowers (16 female, 3 male), 18.6 ± 0.5 years |
| Reference | AMTI force plate (1000 Hz) and Pedar-X insoles (99 sensors, 50 Hz), recorded together | Zebris FDM-S pressure plate | Pedar-x insoles (crossover design) |
| Insole tested | "OpenGo", **13 capacitive sensors** per insole, 3-axis accelerometer (Bosch BMA150), 50 Hz, 16 MB flash; no recalibration ("lifetime of 100-km running") | "OpenGo", **13 capacitive sensors**, 3-D accelerometer, temperature sensor, Li-ion battery, 50 Hz | Moticon "SensorInsole2" (Moticon ReGo AG), **13 capacitive sensors**, 3-D accelerometer, analysed at 50 Hz |
| Firmware or software version | Not stated | Not stated | Software named (Moticon Science), version not stated |
| Main results | Contact and flight times close to AMTI; force–time curves of similar shape. Force impulses 13–34 % lower than AMTI (abstract; 13–36 % in the discussion) and 12–26 % lower than Pedar-X. Correlations with AMTI mostly r = 0.8–1.0. Lower force and latency in fast, high-impact motions; heteroscedastic errors. Balance: medio-lateral centre of pressure differed, anterior–posterior closer; limits of agreement for centre-of-pressure measures 23–79 % | No significant difference in resultant force or stance time against the plate; ICC above 0.837 (stance time) and 0.796 (peak force); high test–retest reliability | Correlations with force platforms showed heteroscedasticity: the underestimation grew with force |
| Limitations stated by the authors | Insoles measure normal force, not necessarily vertical ground reaction force; medio-lateral centre of pressure "should be considered with care"; wide limits of agreement for centre of pressure | Low number of participants (addressed by step-by-step analysis of over 10,000 steps); reliability tested under controlled conditions | The two insoles could not be calibrated with the same system, so two measurements were compared rather than a true value; 50 Hz may be too low for rowing forces; at 100 Hz not all sensors can be sampled |

Two further limitations, ours rather than the authors': all three samples are small and healthy (sport students,
young adults, young rowers). In Stöggl & Martiner, the OpenGo insoles lay under the Pedar-X insoles in the same
shoe.

**Does the tested hardware match the product offered now?** No, as far as the papers and the product page show:
- **Sensors.** All three studies used 13-sensor insoles. Moticon's current page lists 16 textile pressure
  sensors with "65% area coverage".
- **Motion sensor, rate and power.** The current page lists a 6-axis IMU, 10–100 Hz sampling and coin cells.
  Stöggl & Martiner had a 3-axis accelerometer at 50 Hz; Braun et al. a Li-ion battery.
- **Firmware.** None of the papers states a firmware version, and the current firmware is updatable through
  the app. So even an unchanged insole may not behave as the tested one did.
- **No independent study of the 16-sensor product was found.** Searched 2026-11-03: two general web searches
  and one extended search, plus the papers above. PubMed refused direct access (HTTP 429), so a PubMed or
  Google Scholar search with a year filter is still to do.

Stöggl & Martiner is the study with 16 *participants*. If a different study was meant, its details need adding
here.

## What this means for our sole

**What the design aims at (goals, not results):**
- **Five-toe shoes,** with each toe sensed. None of the corpus projects documents this; whether any of them
  could be adapted to it is unknown. Fit has not been tested.
- **Coverage.** Our 75–80 % and OpenGo's 62.5–67.4 % (or "65%") are not comparable. Ours is region outlines
  over the sole outline; the vendor does not define theirs. Neither number shows an effect on force or
  centre-of-pressure estimates; for us that needs the coupon test and the force-plate comparison.
- **Sizes and personal outlines:** a generator capability, not a demonstrated fit. Four configurations have
  been generated and checked, and none has been fitted.
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
