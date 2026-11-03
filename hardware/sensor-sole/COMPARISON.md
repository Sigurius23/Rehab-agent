<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole compared with other pressure insoles

**Basis.** For the other insoles, the documented features come from the project's comparison corpus: the
research report "Open-Source Alternatives to Moticon OpenGo Sensor Insoles", last verified 2026-11-02. For
OpenGo, they also come from Moticon's current product page and from four validation papers, all read on
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
| **Our sensor sole** | **Nothing.** No board made, no film chosen, no calibration. Physical sensing, fit in the shoe and durability are untested | — |
| OpenGo | Four independent studies (next section). Three used the earlier **13-sensor** insoles. One, McNeese et al. 2026, used 16-sensor OpenGo insoles; whether those match the product sold now is unconfirmed | 13-sensor studies: timing agrees well with force plates; force is underestimated, more so at higher forces and in fast motions. 16-sensor study (10 healthy adults, submaximal jumps, values at the instant of peak force only): peak vertical force MAE 4.34 N/kg; anterior–posterior centre of pressure MAE 10 % of foot length; medial–lateral MAE 50 % of foot width, not valid by the authors' criteria. Where centre of pressure was assessed (Stöggl & Martiner; McNeese et al.), medial–lateral was less reliable than anterior–posterior. The product's own figures (≤ 1 % hysteresis, < 5 % total-force error) are the manufacturer's |
| smartinsole | Two IEEE ISCAS papers (2025, 2026) | Force-plate error metrics not published in the README |
| KAKI | 10 m walk tests: 3 participants, 5 sessions, footstrike checked visually | Gait events only; no pressure range or calibration published |
| GRFMS | Ground reaction force against a reference, with Vicon motion capture | GRF estimation fit 68.71 % ± 4.80 % |

## OpenGo: what was validated, and on which hardware

### 16-sensor insoles: McNeese et al., Sensors 2026

McNeese D, Eisner C, Todd R, Noehren B, Owen MK. "Validity and Reliability of Force Insoles to Measure Center of
Pressure During Return-to-Sport Testing." *Sensors* 26(1):66 (2026; online 22 December 2025).
[doi:10.3390/s26010066](https://doi.org/10.3390/s26010066), full text in PubMed Central (PMC12787798), CC BY 4.0.
Funded by NIH (R01AR080708); the authors declare no conflicts of interest. Read in full on 2026-11-03.

| | What the paper reports |
|---|---|
| Task | Four jumps in this order: double-leg and single-leg countermovement jumps (one maximal jump, then four vertical jumps at 50 % effort; the paper does not say whether four per jump type), then double-leg and single-leg horizontal jumps scaled to 50 % of the maximal distance (trial count not stated). Two identical sessions, 7.2 ± 4.7 days apart |
| Sample | 10 healthy, active adults with no history of lower-limb injury; 5 men, 5 women; 25.5 ± 3.8 years; 74.9 ± 12.4 kg |
| Reference | Bertec instrumented force plate in a treadmill, 2000 Hz, reduced to 100 Hz by simple decimation. 13-camera motion capture (200 Hz) placed the force-plate centre of pressure in the foot's frame (Visual3D). Each trial was aligned by shifting the two signals so that their force peaks coincide |
| Insole tested | "Moticon OpenGo force insoles": **16 pressure sensors covering ~65 % of the insole** (6 along the foot, 2–5 across), sizes S4–S9 of 9, **sampled at 100 Hz**. Calibrated with Moticon's recommended procedure (slow walking, anterior–posterior and medial–lateral shifts); the source cited for that procedure is a paper on a different insole (Insole3, Cramer et al. 2022). Force and centre of pressure as computed by the insole system |
| Not stated | Firmware version, app or software version, hardware revision or model number, purchase date, collection dates (ethics approval dated 14 July 2025), shoe model, use of the motion sensor |
| What was compared | One instant per trial: peak vertical force. Validity criteria set by the authors: at least three of MAE and RMSE below 20 % of the magnitude, MAPE below 20 %, and r above 0.75 |
| Validity, all tasks | Peak vertical force: MAE 4.34 N/kg, RMSE 5.68 N/kg, MAPE 15.03 %, r = 0.79 (per task MAE 1.99–6.22 N/kg; MAPE 19.6–21.6 % in the horizontal jumps). Anterior–posterior centre of pressure: MAE 10 % of foot length, RMSE 11 %, MAPE 21.41 %, r = 0.94. Medial–lateral centre of pressure: MAE 50 % of foot width, RMSE 50 %, r = 0.20, **not valid** |
| Reliability (ICC 3,k, session 1 vs 2) | Vertical force 0.75–0.91; anterior–posterior centre of pressure 0.88–0.97; medial–lateral 0.72–0.82, except 0.09 in the single-leg countermovement jump. For the single-leg countermovement jump the abstract gives 0.89 for anterior–posterior centre of pressure; Table 3 gives 0.88 |
| Direction of the force error | The authors read the errors as the insoles overestimating peak force, from computing force as pressure × sensor area. The tables report no signed bias |
| Limitations stated by the authors | 100 Hz may be too slow for fast changes, particularly medial–lateral centre of pressure (they cite 200 Hz for landing data). Reproducing 50 % effort across sessions. The effect of insole and shoe deformation on force and centre of pressure is unknown. Sensor density is low across the narrow forefoot (two sensors wide on the distal half), a possible cause of the poor medial–lateral result. The small sample explains the 0.09 ICC |

Further limitations, ours rather than the authors':
- **Who and what.** Ten healthy young adults doing submaximal jumps. There were no patients after injury, despite the
  return-to-sport framing, and no walking or running.
- **One instant per trial.** The signals were aligned at their force peaks by construction, so timing and the rest of
  the force curve were not assessed.
- **"Valid" is the authors' threshold,** not a general accuracy statement.
- **The reference was decimated.** Simple decimation of the 2000 Hz force plate can itself shift the reference peak;
  the paper does not quantify this.

### 13-sensor insoles: three earlier studies

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

### Does the tested hardware match the product offered now?

- **The three 13-sensor studies: no**, as far as the papers and the product page show.
  - All three used 13-sensor insoles. Moticon's current page lists 16 textile pressure sensors with "65% area
    coverage".
  - The current page lists a 6-axis IMU, 10–100 Hz sampling and coin cells. Stöggl & Martiner had a 3-axis
    accelerometer at 50 Hz; Braun et al. a Li-ion battery.
- **McNeese et al.: unconfirmed.** It neither matches nor fails to match.
  - What the paper states agrees with the current product page: 16 sensors, about 65 % coverage, nine sizes and
    100 Hz.
  - The paper does not identify the hardware revision or the firmware or software version. The firmware is
    updatable through the app.
  - So whether the tested insoles behave like the product sold now is not established either way.
- **Firmware.** None of the four papers states a firmware version.
- **Search.** Our earlier search (2026-11-03: two general web searches and one extended search) missed McNeese et
  al. It was added from a citation supplied in review. Other studies of the 16-sensor insoles may exist; a PubMed or
  Google Scholar search with a year filter is still to do.

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

**A test we could compare directly:** the McNeese protocol.
- **Protocol:** the same four jumps, values at peak vertical force, against a force plate, with centre of pressure
  in % of foot length and width.
- **Where it may bear on us:** the weak spot there was medial–lateral centre of pressure. The authors suspect the
  low sensor density across the forefoot and the 100 Hz rate. Our layout has five metatarsal-head regions across the
  forefoot and five toe regions, and also targets 100 Hz.
- **What is open:** whether our layout changes the medial–lateral error is untested. The 100 Hz limitation would
  apply to us as well.

**Where it is behind:**
- **Nothing measured.** Physical sensing, fit in the shoe and durability are untested. Each alternative above has
  at least some measurement. OpenGo has independent validation of the earlier 13-sensor versions, plus one small
  study of 16-sensor insoles whose match to the current product is unconfirmed.
- **Accuracy is open.** Piezoresistive films (Velostat class) are known for hysteresis, creep and temperature
  drift. Until our coupon test and force-plate comparison report numbers, assume nothing better than the DIY
  piezoresistive insoles.
- **Electronics, power, synchronisation and software** are designed but not built.
