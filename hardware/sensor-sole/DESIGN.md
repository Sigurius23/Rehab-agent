<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->
# Sensor sole v0: our own pressure-sensing sole for five-toe shoes

Status, 2026-11-02: **layout design and generator only.** Nothing has been fabricated or measured. Physical
sensing, fit in the shoe and durability are untested. Every electrical figure below is a design target or an
estimate, marked as such, until the bench says otherwise.

## 1. What it is

A pressure-sensing sole with five toe tabs, designed for a size-42 Vibram FiveFingers. Fit in the shoe has not
been tested. The generator can produce it for other sizes (a layout-only sweep covered EU 36–47) and from a
person's foot landmarks; so far EU 37, 42 and 46 and one synthetic foot have been generated and checked, and
none has been fitted. Its sensing regions are anchored to the foot's anatomy. It has two parts:

- **The sole:** a passive, thin flex circuit in the shoe. Each sensing region is an interdigitated electrode
  pair under a piezoresistive film (a shunt-mode force-sensing resistor). There are no components under the foot.
- **The pod:** a small module outside the shoe, joined to the sole by a flat tail. It holds the readout,
  motion sensor, radio, storage and battery.

| | OpenGo (vendor spec, from our comparison corpus) | Sensor sole v0 target |
|---|---|---|
| Pressure channels | 16 capacitive | 16 piezoresistive regions (pod v1: up to 32) |
| Sensing coverage of the sole | 62.5–67.4 % (corpus); "65% area coverage" (current product page); definition not stated | 75–80 % at EU 37, 42 and 46: region outlines as a share of the sole outline, toe tabs included (geometric estimate, section 5). Not comparable with the vendor's figure: the definitions may differ, and neither number is a measured effect on force or centre of pressure |
| Toes | Toe pockets and five-toe fit not documented in the corpus | Five toe tabs; big toe and four lesser toes sensed |
| Motion sensor | 6-axis in the insole | 6-axis in the pod, worn on the instep, so it moves with the foot |
| Rate | 10–100 Hz | 100 Hz (target) |
| Recording | 32 MB on board | microSD in the pod (prototype); stream over Bluetooth LE |
| Left/right sync | Timing crystals, < 0.006 % drift | 32.768 kHz crystals (±20 ppm = 0.002 %) plus post-hoc clock fit and a hardware sync input (to verify) |
| Calibration | Factory, lifetime | Per region on our bench; zeroed during each swing phase |
| Sizes | 9 double sizes | Generator capability: an EU size, a measured length and width, or a personal outline from foot landmarks. Generated and checked: EU 37, 42, 46 and one synthetic foot. Fit not demonstrated at any size |

## 2. Fitting a size-42 FiveFingers KSO Trek

The target shoe is the **Vibram FiveFingers KSO Trek** (kangaroo leather) in EU 42.

- **Length.** Vibram EU 42 fits a foot of about 264–273 mm; sources differ (section 12). The generator
  defaults to 270 mm and takes the measured length when there is one.
- **What the sole sits on.** The KSO Trek is built as follows (section 12):
  - a kangaroo-leather footbed;
  - a 4 mm EVA midsole;
  - a 4 mm Vibram rubber outsole.

  The outsole is bonded to the shoe, and the leather footbed is not made to come out. So the sensor sole
  **lies on top of the leather footbed**; nothing is replaced.
  - The sensor stack targets **≤ 0.4 mm** (section 4), which is less than a thin sock.
  - Leather takes up sweat. Both faces of the sole are therefore sealed: coverlay underneath, the cover film
    on top. Humidity is part of the coupon test (section 8).
  - Fix the sole to the footbed without adhesive, or with a residue-free tape at the heel only. The toe
    tabs and the tail keep it in place, and the leather is left unmarked.
  - Other FiveFingers models have a 2 mm EVA insole instead (KSO EVO, V-Run). There the sole can also lie on
    top, or replace the insole where it comes out.
- **Toe pockets.** The pockets are walled off down to the sole. The RiverFamily toe shoe we inspected (CC0,
  used only as a stand-in) has 1.2 mm of sole and toe dividers about 30 mm high. The sole therefore has five
  thin toe tabs that slide into the pockets, separated by 2 mm slits. A toe-less variant (no tabs, or the big
  toe only) is one setting away.
- **Tail exit.** The default exit is at the **medial arch**, the highest and least-loaded point of the
  sole's edge. A heel exit is available.
  - The KSO upper rides higher than low-cut models. The tail must reach from the arch, up the inside of the
    upper, over the collar and on to the pod on the instep strap.
  - The default tail is 70 mm (`tail_len`). Measure the collar height at the arch on your pair and lengthen
    the tail if needed.

## 3. Architecture

```
 [ sole: 16 sensing regions ]--flat tail (18 conductors, 0.5 mm pitch)--[ pod on the instep strap ]
   passive flex, ≤0.4 mm                                                  readout, 6-axis IMU, nRF52840,
   common comb + sense comb per region                                    microSD, LiPo, sync input
                                                                              |  Bluetooth LE
                                                                          [ host ] -> LSL streams
                                                                                      -> rehabtwin session
```

## 4. The sole

**Sensing principle.** Each region is a pair of interleaved copper combs. A piezoresistive film over the region
bridges the combs, and the bridge conducts more as the load rises.
- The combs are 0.2 mm fingers with 0.2 mm gaps, which fills 51–56 % of each region with copper.
- The fingers run parallel to the toe-joint (MTP) bend line, so walking strains them least.
- All regions share one common comb net. Each region has its own sense line, so there is no matrix and none of
  a matrix's sneak paths through other sensors. That does not make crosstalk zero; it is to be measured
  (section 6).

**Layer stack (proposed; thicknesses depend on the fabricator and the chosen film):**

| Layer | Purpose | ≈ mm |
|---|---|---|
| Top cover, thin TPU film or textile | Wear surface, moisture barrier | 0.05 |
| Piezoresistive film, die-cut per region (0.5 mm inside the region) | Sensing; one patch per region avoids leakage between regions | 0.10 |
| Adhesive spacer frame around each region | Defines the start of sensing, holds the film | 0.05 |
| Two-layer polyimide flex: combs on top, exposed through one coverlay opening per region; common net on top and sense lines on the bottom, both under coverlay | Electrodes and routing | ~0.12–0.15 |
| Total | | ~0.35–0.40 |

**Regions.** The 16 default regions are:
- the heel (posterior, medial and lateral);
- the midfoot (medial arch, proximal lateral, distal lateral);
- the five metatarsal heads;
- the five toes.

They are Voronoi tiles around anatomical anchors, clipped to the sole. This is deliberate: the hypothesis is
that covering most of the sole helps total force and centre-of-pressure estimates. It has not been measured
for this sole. Small discs ("point mode", still available) cover only 9 % of the sole and put three vias in
the bend zone. The regions also map onto foot segments
(hindfoot, midfoot, forefoot, big toe, lesser toes), which is what the multi-segment foot model needs.

**Routing.** The sole is routed in copper by the generator itself (`sole_route.py`).
- **Sense lines (B.Cu).** Every line runs from its region to the tail along the seams between regions, or
  along the outline as a perimeter channel.
  - The lines form one tree rooted at the tail. Regions are added farthest first, and each new line joins the
    existing tree, so lines share bundles instead of running side by side.
  - Each bundle has a fixed left-to-right order, so no two lines cross. Branches are ranked by where their lines
    are 6 mm beyond the branch point, and a planarity search fixes the side of any line that ends where its
    bundle continues. The order at the root is the connector's pin order.
  - Lines are 0.12 mm wide at a 0.40 mm pitch. The bundle is carved out of the neighbouring regions at its true
    width plus 0.8 mm, with extra room at each via. A path along the sole's edge keeps room for a full
    bundle.
  - Turns use a fillet per lane, of radius 0.8 mm plus the lane's distance from the inner lane. This keeps
    the pitch exact through any angle, including where a block of lanes shifts sideways through a turn.
    (A single arc centre for all lanes did not: where the personalised foot's trunk meets the tail at
    about 35°, the outer lanes jogged across each other.)
  - A final, negotiated pass re-routes all lines together on a 0.06 mm grid, each guided by its planned lane.
    Lines may overlap at a price that rises every round until none do (the PathFinder method); vias, regions
    and the edge are hard obstacles.
    - Each line stays within 3 mm of its planned lane. The plan fixes the topology, and this pass only
      refines the geometry. A free pass took shortcuts through space the plan avoided, such as an empty
      area where a sensor is switched off, and lines on a shortcut keep no order.
    - Copper stays out of the 2 mm copper-free margin of the sole outline; 0.3 mm applies only in the tail.
      The generator reports any copper in the margin (`copper_in_edge_margin_mm2`).
  - **Tail root.** The outline has 5 mm fillets where the tail meets the sole. Sharp inside corners are where
    a flex circuit starts to tear, and they left a bundle arriving at an angle no room to turn into the tail
    within the margin.
    - The regions also keep clear of a disk around the root: half the full bundle's width plus 0.8 mm plus
      2 mm. Every bundle merges there and turns on fillets that cut inside the coarse path, so a region
      carved only along the path could poke into the turn.
  - A crossing that the order cannot avoid would be bridged by a short F.Cu jumper. None is needed at EU 42.
  - Nothing runs under a sensing region: B.Cu stays clear there, so each region has an even backing.
- **Vias.** Each region's via sits on the border of its sense comb nearest the tail. A short F.Cu stub
  joins the via to the comb, and no via falls within 12 mm of the toe-joint bend line.
  - **A via never sits in a bundle.** Reaching a cell on the tree costs nothing, so a via used to be chosen on
    the trunk itself, inside the bundle. The lines continuing past it then had to squeeze by, and at EU 37,
    EU 46 and on the personalised foot they could not. Now a via keeps clear of the tree:
    - by the bundle's half-width there (from the lines already through it, plus the joining line);
    - plus the via's radius, clearance and a 0.3 mm margin;
    - and it keeps room for a line between itself and every other via.
    Later lines may not pass within reach of an existing via. Once all paths are known, a final pass moves any
    via still too close (the bundle can widen after its via was chosen) into its region and extends its line.
    The generator reports both: `vias_moved_clear_of_bundles_mm` and `vias_without_clear_cell`.
  - A toe's via sits at the base of its tab, where the trunk passes. A line running up a toe to a via splits
    the toe's comb, and fingers cut off from their spine have no partner electrode.
  - toe2 at EU 42, before and after this rule (a geometric estimate, not a measured sensitivity):
    - before: the area where both combs interleave was 246 mm². That is 38 % of its 640 mm² Voronoi tile,
      or 47 % of the 521 mm² region left after gaps and bundles;
    - after: 483 mm², 76 % of the tile or 85 % of the 567 mm² region (generator 49ad079).
    How much of that area responds to pressure, and how evenly, is for the coupon test (section 8).
  - On a narrow toe the comb's default sense side can have no room near the base. The toe then takes the
    other side, and its comb swaps spines.
- **Common net (F.Cu).** It runs in the channels, which are empty on F.Cu, as a tree reaching every region's
  common comb. Two vias near the contacts take it to contacts 1 and 18.
- **Tail and contacts.** The tail carries the 16 sense lines and the common net, and is 12 mm wide. The
  contacts are on B.Cu at 0.5 mm pitch for a bottom-contact ZIF connector, with a stiffener to 0.3 mm total.
  - **Contact numbers are physical and the same rule on both feet:** look at the exposed contacts with the
    tail end pointing up; contact 1 is on the left.
  - The left sole is the mirror of the right, so a region sits on a different contact on each foot. The pod
    firmware needs one channel map per side. `verify_board.py` writes it for every board, traced through the
    copper; see section 11 for EU 42.

**KiCad.** `kicad_export.py` turns the generator's board file into a two-layer KiCad 7 board:
- the outline;
- each region as a footprint whose two combs are custom-shaped pads, exposed for the film through one
  coverlay opening per region. Per-finger openings would leave 0.2 mm coverlay webs that can't be cut and
  would hold the film off the copper. The opening is notched where an F.Cu track lands on a comb, so the
  joint stays covered and other copper keeps 0.15 mm from the opening;
- the tracks, vias and contacts;
- keep-out rule areas under every region and across the bend band;
- the routing plan on `Cmts.User`, and fabrication notes, the licence and the source location on `F.Fab`;
- the design rules in the `.kicad_pro` beside the board. Without that file KiCad falls back to its default
  rules: the EU 42 board then shows 75 DRC reports (vias under the default 0.5 mm minimum, among others) instead
  of only the 17 library warnings. The title block records which
  generator files made the board.

Design-rule results are reported in section 11.

**Material (open; decided by a coupon test, section 8).** Options:
- carbon-loaded polyolefin film (Velostat class): cheap and 0.1 mm, but known for hysteresis, creep and
  temperature drift;
- piezoresistive coated textile: more compliant, thicker;
- a printed carbon layer.
No material is chosen until coupons have been measured.

## 5. Scaling and personalisation

`sole_gen.py` builds the whole sole from a foot spec. Each run produces:
- the outline, toe tabs, regions, combs, routing plan, tail and checks;
- SVG, a DXF with KiCad-ready layers (`Edge.Cuts`, `F.Cu.common`, `F.Cu.sense`, `Routing.plan`), JSON and
  previews.

| Input | Default | Personal |
|---|---|---|
| Foot length, ball width | From EU size (length ≈ 6.67 × EU − 10 mm; width 0.385 × length) | Measured, or from the phone foot scan |
| Metatarsal heads 1 and 5 | Population proportions | Scan landmarks; heads 2–4 are interpolated |
| Toe tips, widths, webs | Big toe longest, typical widths | Scan landmarks (e.g. a longer second toe) |
| Toe tabs | All five | Any tab off, e.g. if a toe pocket does not take one |
| Regions | The 16 above | Any subset; the tiles re-form around the anchors that remain |
| Tail exit | Medial arch | Heel |
| Side | Right | Left is the mirror |

**Copper routing and board checks per size and side** (2026-11-03; generator files of commit 49ad079, the
same in every board's title block). Each board was generated, exported to KiCad and checked with
`verify_board.py`. A left board has the same routing as its right one (a mirror image); its KiCad board is
checked separately.

| Board | Regions | Coverage | Sensing area (geometric estimate), all / weakest region | Vias, jumpers | Fine-grid pass | DRC entries | Contacts traced through copper | Comb copper under coverlay, worst region | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| EU 37 R | 16 | 74.9 % | 75 % / mt4 69 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.17 mm² (0.15 %) | passes |
| EU 37 L | 16 | 74.9 % | 75 % / mt4 69 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.17 mm² (0.15 %) | passes |
| EU 42 R | 16 | 77.5 % | 78 % / mt4 69 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.17 mm² (0.11 %) | passes |
| EU 42 L | 16 | 77.5 % | 78 % / mt4 69 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.17 mm² (0.11 %) | passes |
| EU 46 R | 16 | 79.5 % | 80 % / mt4 58 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.16 mm² (0.09 %) | passes |
| EU 46 L | 16 | 79.5 % | 80 % / mt4 58 % | 18, none | 1 round, nothing left | 17 library warnings | each to its own region | toe5 0.16 mm² (0.09 %) | passes |
| Personal example R | 14 | 80.1 % | 80 % / mt1 73 % | 16, none | 1 round, nothing left | 15 library warnings | each to its own region | toe3 0.20 mm² (0.08 %) | passes |
| Personal example L | 14 | 80.1 % | 80 % / mt1 73 % | 16, none | 1 round, nothing left | 15 library warnings | each to its own region | toe3 0.20 mm² (0.08 %) | passes |

"Passes" means `verify_board.py` found nothing to object to. It does **not** mean released for fabrication:
see FABRICATION.md and section 8.

The personal example is `person_example.json`, with illustrative values, not a real person: foot 262 × 108 mm,
metatarsal heads from "scan" landmarks, second toe longest, arch and fifth-toe sensors off. Its 14 regions
are checked as 14, from the configuration written on the board. No copper lies in the 2 mm edge margin on
any board.

Coverage is the share of the sole covered by region outlines. Sensing area is a geometric estimate:
the share of the regions' Voronoi tiles where both combs interleave (within one finger pitch of each). A
film patch elsewhere touches one comb or none. It is not a measured sensitivity.

**What was wrong, and what fixed it.** Before these changes only EU 42 routed. EU 37 and EU 46 left lines
too close at a corner of the trunk, and the personalised foot had seven sense lines shorted. Each cause was
found by measuring the plan and the fine-grid pass, not by relaxing a rule:
1. **Vias inside bundles.** A cell on the tree costs nothing to reach, so a via was often chosen on the trunk
   itself, and the lines continuing past it had to squeeze by. Vias now keep clear of the tree, and of each
   other (section 4).
2. **Shortcuts.** The fine-grid pass could leave the plan and use the 2 mm edge margin or empty space, such as
   the arch on a foot without an arch sensor. Lines on a shortcut keep no order, so they crossed. It now
   stays within 3 mm of the plan and out of the margin.
3. **Turns with a sideways shift.** One arc centre for a whole block of lanes made the outer lanes jog across
   each other where a block shifts sideways through a turn. Each lane now has its own fillet.
4. **The tail root.** A region carved only along the coarse path could poke into the turn into the tail, and
   the sharp inside corners left no room within the margin. The outline now has 5 mm fillets there, and the
   regions keep clear of the root.

More negotiation rounds alone did not help: EU 37 with 16 rounds instead of 8 still failed. Every board now
settles in one round.

**Known weak points of the current routing:**
- **heel_med and arch_med** find no via cell clear of the trunk in their region (`vias_without_clear_cell`).
  They keep the nearest cell. The fine-grid pass and the KiCad DRC show the clearances hold, but these two
  vias sit closer to the bundle than the planner's own margin.
- **Personal example:** its longest via-to-comb stub on F.Cu is 8.7 mm (EU sizes: 2–3 mm).
- **EU 46:** 0.43 mm² of copper is stacked on both layers in the toe-joint bend zone (EU 37, EU 42 and the
  personal example: 0).

**Earlier layout-only sweep.** Before copper routing existed, a sweep over EU 36–47 passed the layout
checks: regions, routing plan, corridor inside the margin, no vias in the bend zone. That sweep says nothing
about copper. The table above replaces it.

**Weakest regions.** mt4 keeps the least sensing area at every default size (58–69 % of its tile). Comb
ends are lost at its slanted corners, and the trunk runs along its edge. 26–66 % of each metatarsal
region's comb lies in the toe-joint bend zone, depending on size and foot; see FABRICATION.md for what that
means for the plating.

**Manufacturing.** A personal sole is a new flex design. One sole fits a standard flex panel (EU 42:
270 × 167 mm). Left and right together exceed one fabricator's standard panel unless nested (FABRICATION.md).
For research cohorts, a graded set (EU 36–47 in two widths) avoids a new order per person; personalise only
where the anatomy needs it. Every size still has to pass the checks above first.

## 6. The pod (prototype, off-the-shelf parts; proposed and not yet built)

| Block | Prototype part | Why |
|---|---|---|
| MCU, radio, IMU, flash, charger | Seeed XIAO nRF52840 Sense: 6-axis LSM6DS3TR-C, 2 MB flash, BQ25101 charger, 6 analog pins | All on one 21 × 17.5 mm board; the IMU moves with the foot when the pod is on the instep |
| Channel select | 16:1 analog multiplexer (CD74HC4067 class) | 16 sense lines into one readout |
| Readout | Transimpedance amplifier with a zero-drift op-amp (OPA333 class); the common comb is driven at a reference voltage | Output is proportional to conductance, roughly linear in load (to be measured). Unselected lines float, which leaves no DC path through other regions; crosstalk is expected to be low but is to be measured (below) |
| Connector | 18-pin, 0.5 mm flat-flex connector | Takes the sole's tail |
| Storage | microSD | 16 channels × 12 bit plus the IMU at 100 Hz is about 3.6 kB/s, or 13 MB an hour |
| Battery | 150–250 mAh LiPo | Estimate of 6–10 mA while streaming, so tens of hours; to be measured |
| Sync | One input (wired or optical pulse) | Aligns with force plates and cameras |

Pin budget on the XIAO's 11 I/O pins:
- 4 multiplexer address pins, 1 analog input, 4 for the SPI to the microSD, 1 sync input, 1 spare.

Pod v1 (custom board, bare nRF52840 module) adds 32 channels, more storage and a smaller enclosure.

**Crosstalk is to be measured, not assumed.** Floating unselected lines remove a matrix's sneak paths, but
other paths remain:
- capacitive coupling between neighbouring lines in a bundle: up to about 12 pF at EU 42 and 14 pF at EU 46,
  where two lines run side by side for 300 mm or more. This is an estimate from the routed copper
  (`candidates/open_line.py`). The readout has to settle through it after each switch;
- the multiplexer's charge injection and off-leakage;
- surface leakage between lines when sweat gets in;
- film or moisture bridging between neighbouring film patches;
- the common net's own resistance, shared by every region.
The channel-isolation test (section 9.2) measures it: load one region and read its neighbours, at the chosen
settling time, dry and humid.

## 7. Data and integration

- **Streams.** The host receives Bluetooth LE and publishes LSL streams `rehab_sole_L` and `rehab_sole_R`
  (16 pressure channels, 6 IMU channels, pod time). This is the same mechanism `rehabtwin` already uses for
  posture and cue streams, so sessions record it without new plumbing.
- **Provenance.** Values carry the label "measured, research device, not validated" until section 8 is done.
  The display rule applies: no user-facing load claim until the force-plate comparison passes its
  pre-set thresholds.
- **Data handling.** Recordings are health data and stay out of every repository.
- **Channel maps.** Which region a pod channel reads depends on the side and on the exact board: the left
  map is the right one reversed, and a regenerated board can route differently. Each sole has an ID printed
  on its tail: label, side and the first 10 hex of its design hash, which changes whenever the copper or the
  map could change. The pod or host must:
  - resolve the ID with `channel_map.py` against the deployed maps in `maps/`: exactly one intact map for
    that ID and that foot, or none;
  - refuse to label channels by region if no such map is found;
  - record the ID and the board's sha256 with every recording, so data can be traced to its map.
- **What the sole could give the twin,** once built, calibrated and validated (none of it exists yet):
  - load per region and its timing: heel, midfoot, forefoot and, in the standard layout, each toe;
  - contact and toe-off times, stance duration and left–right timing, once event detection is validated;
  - shifts of load between regions and between the feet;
  - total vertical force and centre of pressure, estimated from the calibrated regions and checked against a
    force plate;
  - acceleration and angular rate of the foot from the pod IMU.
- **What it cannot measure:**
  - toe-joint angles, bone geometry, muscle forces, shear, or the full 3-D ground-reaction force vector;
  - a peak inside a region, since each region gives one aggregate signal;
  - the motion of each foot segment or toe, since the IMU on the instep moves with the foot as one body.
  These are inputs to the twin, labelled with their provenance (above).

## 8. Calibration and validation plan

1. **Coupon test.** A small flex board with identical regions in three sizes and a bend strip, for each
   material, measured for:
   - linearity, hysteresis, creep and repeatability under dead weights and an indenter;
   - temperature drift;
   - baseline shift when bent to a 10 mm radius.
   The coupon chooses the material.
2. **Per-region calibration of each sole:**
   - load against output on an indenter with a load cell;
   - zero offset re-taken in every swing phase.
3. **Fit and comfort** in a size-42 FiveFingers: insertion of the toe tabs, the tail at the collar, an hour of
   walking.
4. **Against force plates.** Total vertical force and centre of pressure in walking and in the squat protocol
   of the insole research plan. Agreement thresholds are set before the data is seen.
5. **Left/right sync** with a common trigger: offset and drift over an hour.
6. **Durability:** cycles to failure at the toe-joint bend. OpenGo states ≥ 100,000 load cycles.

Additions for the coupon, the calibration record and comparing two candidates are in sections 9.3 and 9.6.

## 9. Proposed additions (a plan; nothing here is designed, built or tested)

The 16-region sole stays the baseline. These additions come from comparing it with other insoles
(`COMPARISON.md`). Numbers are arithmetic from the current design rules unless marked otherwise.

### 9.1 A higher-resolution candidate, alongside the baseline

**Status, 2026-11-03.** Candidate T1, a targeted layout with 20 regions at EU 42, has been generated beside
the 16-region baseline with the same generator, rules and checker. 6 of its 8 configurations pass the checker;
EU 37 fails at one spot. It is compared with a dense matrix in `CANDIDATES.md`. It is design and analysis
only: not fabricated, fitted or measured. The 32-region figures below are preliminary arithmetic, not a routed
or fit-validated design.

- **Candidate subdivisions:**
  - big toe: tip and base;
  - lesser toes: one region each, as now; more only where a tab has room;
  - forefoot: inner–outer and front–back detail around the metatarsal heads;
  - heel: front–back and inner–outer;
  - midfoot: the arch and the lateral foot, without forcing regions where they would compromise fit.
- **Count and placement** come from fit, routing and measurement studies, not from a target number.
  - The generator can switch regions off already; the synthetic foot has 14.
  - Subdividing a region needs new anchors in `sole_gen.py`. That has not been tried.
- **What more regions cost at the current rules.** Preliminary arithmetic, not a routed or fit-validated design:

  | | 16 regions (now) | 32 regions |
  |---|---|---|
  | Contacts (regions plus 2 common) | 18 | 34 |
  | Contact row, centre to centre at 0.5 mm | 8.5 mm | 16.5 mm |
  | Tail width, with the same edge allowance as now | 12 mm | about 20 mm |
  | Widest bundle (0.12 mm lines at 0.40 mm pitch) | 6.1 mm | 12.5 mm |
  | Carved out of the neighbouring regions (bundle plus 0.8 mm) | 6.9 mm | 13.3 mm |

  - The full bundle meets the tail at the medial arch, so the regions there would likely lose the most area.
  - The tail passes up the inside of the upper and over the collar, so a wider tail is a fit question.
- **A dense matrix** (smartinsole-like) is a separate option: 253 cells read through 33 rows and 15 columns,
  48 lines in all.
  - On a five-toe sole the slits separate the toe tabs, so rows and columns cannot cross between toes. Each
    toe would need its own lines back through the forefoot.
  - A matrix also needs crosstalk compensation (smartinsole's 2026 paper) and a different readout (9.2).

### 9.2 Electronics for more channels

- **32 channels on the XIAO.** Two 16:1 multiplexers would share the four address lines, each feeding its own
  transimpedance amplifier, with the spare pin as the second analog input. That uses all 11 I/O pins.
- **Readout load.** 32 channels at 100 Hz are 3,200 conversions a second per foot. The nRF52840's ADC is not
  expected to be the limit, but that is still to be confirmed against its datasheet. The practical limit is how
  fast the amplifier settles after each switch, which has to be measured.
- **Data.** 32 channels × 12 bit plus the IMU at 100 Hz come to about 6.0 kB/s (21.6 MB an hour), against
  3.6 kB/s now.
- **32 channels are not 253 cells.** A dense matrix needs row drive and column sense, not this multiplexer
  chain.
- **For every candidate, specify and measure:**
  - the actual rate per channel with both feet recording;
  - channel isolation: load one region and read its neighbours;
  - range, resolution and saturation;
  - power, size and heat;
  - reliable identification of the attached sole and its channel map (section 7).
- 100 Hz stays a target until it is measured on the complete system.

### 9.3 Material and calibration additions (extending section 8)

- **Partial loading** on the coupon: the same load at a region's centre, edge and corner, and across two
  regions. A large region may respond differently when only part of it is pressed.
- **Moisture** alongside temperature, because the leather footbed takes up sweat (section 2).
- **A calibration record per sole,** keyed to its printed ID and design hash: the curve per region, zero,
  date, rig and material lot. Zero and drift are re-checked at the start of every session.
- **Warnings in the data:**
  - **Saturation.**
  - **A suspected open line.** A region that never rises above zero while its neighbours do is flagged.
    With the readout proposed in section 6, a broken sense line may be indistinguishable from an unloaded
    region. Added diagnostics could detect it. A capacitive self-test, loop-back lines, a reference
    conductance and test coupons are compared in `CANDIDATES.md`; none has been built or tested.
  - **Connector seating.** Contacts 1 and 18 both carry the common net. If the pod keeps them separate, it
    can check continuity between them. That shows both ends of the connector are seated; it does not test
    the sense lines.
- **Raw signals are kept** with every calibrated estimate. Calibrated values are labelled experimental until
  section 8 is complete (section 7).

### 9.4 Synchronising both feet and the cameras

- **Each pod records:**
  - every sample with the pod's timestamp, meaning when it was taken rather than when it arrived. smartinsole's
    README notes that host arrival times over Wi-Fi include the transmission delay;
  - IMU acceleration and angular rate;
  - sync-input events from a pulse shared with the force plates and cameras. A camera needs a visible marker
    of the same pulse, an LED for instance;
  - board ID, side, channel-map hash and calibration version.
- **Measure before relying on it:**
  - clock offset and drift between the feet and against the cameras;
  - packet loss;
  - end-to-end latency of the live stream.
- **Camera or RealSense body pose** stays an observation or an inference, not a measurement of internal
  anatomy.

### 9.5 Mechanical requirements for five-toe use

- **Toe tabs stay flat and in their pockets** while the toes spread and grip.
- **Slit ends.** The 2 mm slits between the tabs end in a full radius of about 1.0 mm at EU 37, 42 and 46, as
  measured on the generated outlines. Whether that survives repeated toe spreading is for the bend test.
- **The join between each tab and the sole** is flexible and covered on both faces.
- **Tail root and pod:** comfortable at the collar; the pod attached securely and unobtrusively.
- **Sweat, abrasion, cleaning and repeated insertion** into the shoe.
- **Bend fatigue** at the toe-joint line, including the known risks (`VERIFICATION.md`):
  - EU 46's 0.43 mm² of stacked copper in the bend zone;
  - the synthetic foot's 8.7 mm stub at 0.19 mm clearance.
- **Thickness.** The 0.35–0.40 mm stack is a proposal. Thickness and comfort depend on the film, adhesive,
  cover and fabrication.

### 9.6 Validating both candidates the same way (extending section 8)

- **Same tasks and the same references,** so that the two candidates can be compared.
- **Walking first:** regional loading, contact timing, left–right differences, and total force and centre of
  pressure against force plates.
- **Spatial pressure.** A force plate cannot check a pressure map. Options:
  - an indenter at known points on the bench;
  - a pressure plate with the sole lying on it, outside the shoe.
  In-shoe reference insoles (Pedar-X class) come in conventional outlines, so they share the five-toe fit
  problem.
- **Later:** running, turning and jumps, if those become intended uses. McNeese et al.'s jump protocol gives a
  published comparison (`COMPARISON.md`).
- **Generalisation:** people, foot shapes and sessions not used to fit the calibration.
- **Acceptance criteria are set before the data is seen.** The comparison decides whether the extra channels
  improve the outputs the twin uses enough to justify their cost.

## 10. Decisions needed

1. **Where the design lives.** Decided 2026-11-02: open hardware in the public repository
   `Sigurius23/Rehab-agent`, folder `hardware/sensor-sole/`, under CERN-OHL-S-2.0 (see `README.md`).
2. **Which FiveFingers model.** Decided 2026-11-02: KSO Trek, kangaroo leather, EU 42. Its leather footbed
   is not removable, so the sole lies on top (section 2). Still open: the collar height at the arch, which
   sets the tail length.
3. **Pod position.** Instep (recommended: the IMU then measures the foot) or ankle.
4. **Channels.** 16 on the XIAO prototype now, or go straight to a 32-channel custom pod.
5. **Materials for the coupon test**, and the budget and fabricator for the flex boards.
6. **Ethics and consent** (decision D8 in the review) before anyone other than the developers wears it.
7. **Higher-resolution candidate.** Decided 2026-11-03: develop it in parallel with the 16-region baseline,
   as design and analysis only, and keep both for a fair comparison (`CANDIDATES.md`). Still open: the region
   count, from the studies in section 9, which also settles item 4.

## 11. Files and how to run

- `sole_gen.py`: the generator. Run `python sole_gen.py --size 42 --out out/`, with optional `--length`,
  `--width`, `--side L`, `--exit heel`, `--mode point` and `--foot person.json`. It needs numpy, scipy,
  shapely, matplotlib and ezdxf.
- `person_example.json`: the personalisation format.
- `out/` and `sweep/` (not committed; regenerate them): previews and exports of any run.
- `sole_route.py`: the copper routing the generator uses (section 4).
- `kicad_export.py`: board file to KiCad 7 board. Run it with the Python that ships KiCad's `pcbnew`.
- `verify_board.py`: the checks a board must pass before fabrication (below). Same Python as above.
- `make_fab.sh`: generator, then KiCad, then `verify_board.py`, then Gerbers, drill file and a zip. Usage:
  `./make_fab.sh 42 R`. It writes no fabrication files if the check fails.
- `kicad/`: the EU 42 boards (right, left), each with:
  - its project file (the design rules);
  - its DRC report and check result (`.check.json`, including the contact map);
  - a preview.
- `kicad/` also holds the EU 37, EU 46 and personal-example boards, with the same files. `kicad/MANIFEST.json`
  (`manifest.py`) lists all eight with their IDs, hashes and provenance.
- `maps/`: the deployed channel maps, one per passing board. `channel_map.py` resolves a printed ID to one of
  them, or refuses.
- `tests/`:
  - `test_verify_drc.py`: the checker fails closed on broken DRC reports;
  - `test_verify_negative.py`: negative controls for the checker;
  - `test_channel_map.py`: the resolver (runs in CI).
  The first two need KiCad's Python.
- `FABRICATION.md`: fabrication assumptions, open questions, draft enquiry to a fabricator.

**What `verify_board.py` checks** (any failure, or anything it cannot establish, fails the board):
0. **Configuration.** The exporter writes the regions the board was built for, and its number of contacts,
   as a text on `Cmts.User`. Everything below is checked against that list, so a personal sole with 14
   regions is checked as 14, not 16. A board without the text fails.
1. **DRC with the board's own rules,** failing closed. The `.kicad_pro` must sit beside the board. The board
   fails if:
   - KiCad cannot write the report;
   - a section is missing, or the number of entries in a section differs from its header;
   - there is any entry other than one "footprint not in a library" warning for each footprint the
     generator made (each region, and J1). These are listed one by one in the result (`library_warnings`).
   The local path in the report header is replaced by the file name.
2. **Region-to-contact map through the copper.** Tracks, vias and pads that touch are joined, without using
   the net names. Each sense contact must reach exactly one region's sense comb, and contacts 1 and N must
   reach every common comb. Every comb piece must be reached, and no two contacts may be joined. The regions
   reached must be exactly those in the configuration.
3. **Contact numbering.** Pad numbers must follow the physical order (section 4).
4. **Coverlay.** One opening per region, lying on its region (≥ 95 % of the region's area). The comb copper
   it leaves covered is computed from the pads' real geometry (copper minus opening), per region and per comb
   (`coverlay` in the result). More than 2 % of a region's copper covered fails.
5. **Provenance and channel map.** The result records (`provenance`):
   - the input configuration;
   - the generator-file hashes taken at the run's start, which must match the files beside the script;
   - the tool versions and the project rules;
   - the sha256 of the board and project files, and the checker's own hash.
   For a passing board, the checker writes the deployed map package to `maps/` (`--maps`).
6. **Identity.** The ID printed on the tail must be the board's design ID: label, side and the first 10 hex
   of the design hash written on the board and in its title block. The copper-free margin keep-outs must be
   present.

**EU 42 results (KiCad 7.0.11, 2026-11-03, generator commit 99c7468).** Both boards pass every check. The
verification and risk summary for all eight boards is VERIFICATION.md.

| Check | Right | Left |
|---|---|---|
| DRC errors (clearance, edge, slivers, mask bridges, keep-outs, outline) | 0 | 0 |
| Unconnected items | 0 | 0 |
| "Footprint not in a library" warnings | 17: one for each generated footprint, S01–S16 and J1 | the same 17 |
| Each contact reaches its own region only; COM reaches all 16 common combs | yes | yes |
| Contact numbering physical | yes | yes |
| Regions and contacts match the board's configuration (16, 18) | yes | yes |
| Comb copper under coverlay, worst region | toe5, 0.17 mm² (0.11 %) | toe5, 0.17 mm² (0.11 %) |
| Generator hashes in the title block match the files | yes | yes |
| Board ID printed on the tail (design ID) | `EU42 R 4ea1726398` | `EU42 L 7d4eecd3c9` |
| Board file sha256 (first 12) | `50ca340ed60e` | `5f3730524062` |

The library warnings are expected. The region and connector footprints are generated by `kicad_export.py`
and live in no KiCad library. Each one is listed by reference in the board's `.check.json`
(`drc.library_warnings`), and any other warning or error fails the board.

**Channel maps (contact → region; contacts 1 and 18 are COM).** Each map is valid only for the board file
with that sha256 and for soles printed with that ID:

| Board (ID, sha256) | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `EU42 R 4ea1726398`, `50ca340ed60e` | heel_post | heel_med | heel_lat | mid_lat_prox | arch_med | mid_lat_dist | mt5 | toe5 | mt4 | toe4 | toe3 | toe2 | toe1 | mt1 | mt2 | mt3 |
| `EU42 L 7d4eecd3c9`, `5f3730524062` | mt3 | mt2 | mt1 | toe1 | toe2 | toe3 | toe4 | mt4 | toe5 | mt5 | mid_lat_dist | arch_med | mid_lat_prox | heel_lat | heel_med | heel_post |

- **Left and right.** The left map is the right one reversed, because the left sole is a mirror image.
- **Other boards.** The maps differ by size, and can change whenever the design changes. Each board's map is
  in its deployed package in `maps/`.
- **The pod** must take the map from the deployed package in `maps/` whose ID matches the sole, through
  `channel_map.py` (section 7). Never take it from this table or from another board.

**Routing and sensing (EU 42):**
- 16 regions at 77.5 % coverage; 78 % of the tiles' area senses (geometric estimate).
- The weakest region is mt4, at 69 % of its tile.
- 18 vias and no jumpers; the fine-grid pass settles in one round.
- No copper in the edge margin, and none stacked on both layers in the bend zone.
- About 4 minutes per foot to generate, plus about 2 minutes to export and check.

**Provenance check of the boards committed on 2026-11-02 (f653246).** Regenerated from their generator
revision (0c2b2df), the right board has the same footprints, pads, tracks, vias, zones and title block; only
KiCad's UUIDs and item order differ. Re-running DRC on the committed board and project files gave the
committed reports exactly (apart from the date). Those boards are superseded: they had the toe2 split and the
left board's reversed pad numbers.

Next steps (not started):
- route-check more feet: the remaining EU sizes 36–47 and real scanned feet, not only the four configurations
  above;
- give heel_med and arch_med via cells clear of the trunk (section 5, known weak points);
- send the fabricator questions (FABRICATION.md) once the project owner approves;
- draw the pod carrier schematic;
- design the coupon board.

## 12. Sources

- Vibram EU 42 foot length:
  - [Woot listing, EL-X and CVT models](https://sellout.woot.com/offers/mens-el-x-grey-black-orange-12) (10¾ in);
  - [Grivet Outdoors conversion](https://grivetoutdoors.com/products/vibram-five-fingers-mens-cvt-hemp-minimalist-casual-walking-shoe) (27.1 cm);
  - [Feetus](https://feetus.co.uk/?p=1156) (a 26.4 cm foot takes a 42);
  - Vibram's own [sizing guide](https://www.vibram.com/rw/sizing-guide-navigation/sizing-guide.html).
- KSO Trek build (kangaroo-leather footbed, 4 mm EVA midsole, 4 mm Vibram rubber outsole):
  - the project owner's product information, 2026-11-02;
  - [BirthdayShoes KSO Trek review](https://birthdayshoes.com/vibram-five-fingers-kso-trek-review);
  - [shop4runners product page](https://shop4runners.eu/fivefingers-kso-trek-7975).
- Other FiveFingers soles and insoles:
  - [V-Run specification](https://www.altitude-sports.com/p/vibram-fivefingers-vrun-barefoot-running-shoes-mens-vff-ff-26m70);
  - [KSO EVO 2014](https://feetus.co.uk/blog/2013/08/27/vibram-fivefingers-2014-sneak-peak-1-the-kso-evo/);
  - [KSO EVO review, 2021](https://trailrunningspain.com/2021/03/15/vibram-fivefingers-kso-evo-minimalist-off-road-training-mountain-urban-or-gym/).
- [Seeed XIAO nRF52840 (Sense) wiki](https://wiki.seeedstudio.com/XIAO_BLE/).
- [Moticon OpenGo sensor insoles](https://moticon.com/opengo/sensor-insoles): baseline figures as summarised in
  our comparison corpus.
- RiverFamily toe barefoot shoes: CC0, from riverfamily.art. Used only to inspect the construction of a
  five-toe shoe; no geometry is taken from it.
