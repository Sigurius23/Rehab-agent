<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->
# Sensor sole v0: our own pressure-sensing sole for five-toe shoes

Status, 2026-11-02: **layout design and generator only.** Nothing has been fabricated or measured. Every
electrical figure below is a design target or an estimate, marked as such, until the bench says otherwise.

## 1. What it is

A pressure-sensing sole with five toe tabs that fits a size-42 Vibram FiveFingers and scales to EU 36–47.
Its sensing regions are anchored to the wearer's own anatomy. It has two parts:

- **The sole:** a passive, thin flex circuit in the shoe. Each sensing region is an interdigitated electrode
  pair under a piezoresistive film (a shunt-mode force-sensing resistor). There are no components under the foot.
- **The pod:** a small module outside the shoe, joined to the sole by a flat tail. It holds the readout,
  motion sensor, radio, storage and battery.

| | OpenGo (vendor spec, from our comparison corpus) | Sensor sole v0 target |
|---|---|---|
| Pressure channels | 16 capacitive | 16 piezoresistive regions (pod v1: up to 32) |
| Sensing coverage of the sole | 62.5–67.4 % | 78–83 % across EU 36–47 (generator, section 5) |
| Toes | Standard insole, no toe pockets | Five toe tabs; big toe and four lesser toes sensed |
| Motion sensor | 6-axis in the insole | 6-axis in the pod, worn on the instep, so it moves with the foot |
| Rate | 10–100 Hz | 100 Hz (target) |
| Recording | 32 MB on board | microSD in the pod (prototype); stream over Bluetooth LE |
| Left/right sync | Timing crystals, < 0.006 % drift | 32.768 kHz crystals (±20 ppm = 0.002 %) plus post-hoc clock fit and a hardware sync input (to verify) |
| Calibration | Factory, lifetime | Per region on our bench; zeroed during each swing phase |
| Sizes | 9 double sizes | Any length and width; personal outlines from a foot scan |

## 2. Fitting a size-42 FiveFingers KSO Trek

The target shoe is the **Vibram FiveFingers KSO Trek** (kangaroo leather) in EU 42.

- **Length.** Vibram EU 42 fits a foot of about 264–273 mm; sources differ (section 11). The generator
  defaults to 270 mm and takes the measured length when there is one.
- **What the sole sits on.** The KSO Trek is built as follows (section 11):
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
- All regions share one common comb net. Each region has its own sense line, so there is no matrix and no
  ghosting between regions.

**Layer stack (proposed; thicknesses depend on the fabricator and the chosen film):**

| Layer | Purpose | ≈ mm |
|---|---|---|
| Top cover, thin TPU film or textile | Wear surface, moisture barrier | 0.05 |
| Piezoresistive film, die-cut per region (0.5 mm inside the region) | Sensing; one patch per region avoids leakage between regions | 0.10 |
| Adhesive spacer frame around each region | Defines the start of sensing, holds the film | 0.05 |
| Two-layer polyimide flex: combs and the common net on top (ENIG, exposed), sense lines on the bottom (coverlay) | Electrodes and routing | ~0.15 |
| Total | | ~0.35–0.40 |

**Regions.** The 16 default regions are:
- the heel (posterior, medial and lateral);
- the midfoot (medial arch, proximal lateral, distal lateral);
- the five metatarsal heads;
- the five toes.

They are Voronoi tiles around anatomical anchors, clipped to the sole. This is deliberate. OpenGo's high
coverage is what makes total force and centre of pressure usable. Small discs ("point mode", still available)
cover only 9 % of the sole and put three vias in the bend zone. The regions also map onto foot segments
(hindfoot, midfoot, forefoot, big toe, lesser toes), which is what the multi-segment foot model needs.

**Routing.** The sole is routed in copper by the generator itself (`sole_route.py`).
- **Sense lines (B.Cu).** Every line runs from its region to the tail along the seams between regions, or
  along the outline as a perimeter channel.
  - The lines form one tree rooted at the tail. Regions are added farthest first, and each new line joins the
    existing tree, so lines share bundles instead of running side by side.
  - Each bundle has a fixed left-to-right order that is the same at every branch, so no two lines cross. The
    order at the root is the connector's pin order.
  - Lines are 0.12 mm wide at a 0.40 mm pitch. The bundle is carved out of the neighbouring regions at its true
    width plus 0.5 mm, with extra room at each via.
  - Turns use concentric fillets, which keep the pitch exact through any angle.
  - A final pass re-routes each line on a 0.06 mm grid, guided by its planned lane, with every other line and
    via as an obstacle at full clearance. That resolves conflicts at closely spaced branches.
  - Nothing runs under a sensing region: B.Cu stays clear there, so each region has an even backing.
- **Vias.** Each region's via sits on the border of its sense comb nearest the tail. A short F.Cu stub
  joins the via to the comb, and no via falls within 12 mm of the toe-joint bend line.
- **Common net (F.Cu).** It runs in the channels, which are empty on F.Cu, as a tree reaching every region's
  common comb. Two vias near the contacts take it to pins 1 and 18.
- **Tail and contacts.** The tail carries 16 sense lines, the common net and a spare and is 12 mm wide. The
  contacts are on B.Cu at 0.5 mm pitch for a bottom-contact ZIF connector, with a stiffener to 0.3 mm total.

**KiCad.** `kicad_export.py` turns the generator's board file into a two-layer KiCad 7 board:
- the outline;
- each region as a footprint whose two combs are custom-shaped pads, exposed for the film;
- the tracks, vias and contacts;
- keep-out rule areas under every region and across the bend band;
- the routing plan on `Cmts.User`, and fabrication notes, the licence and the source location on `F.Fab`.

Design-rule results are reported in section 10.

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

**Size sweep, default proportions, right foot (all checks pass at every size):**

| EU | Regions | Coverage | Unrouted | Corridor outside margin | Vias in bend zone | MT1 area kept |
|---|---|---|---|---|---|---|
| 36 | 16 | 78.8 % | 0 | 0 mm² | 0 | 66 % |
| 38 | 16 | 79.3 % | 0 | 0 | 0 | 70 % |
| 40 | 16 | 79.6 % | 0 | 0 | 0 | 74 % |
| 42 | 16 | 81.0 % | 0 | 0 | 0 | 74 % |
| 44 | 16 | 82.5 % | 0 | 0 | 0 | 73 % |
| 46 | 16 | 83.0 % | 0 | 0 | 0 | 74 % |
| 47 | 16 | 82.7 % | 0 | 0 | 0 | 77 % |

**Personal example** (`person_example.json`, illustrative values, not a real person):
- foot length 262 mm and ball width 108 mm;
- metatarsal heads from "scan" landmarks;
- second toe longest;
- arch and fifth-toe sensors off.

The result is 14 regions at 82 % coverage, all routed.

**Known weak spot.** The main bundle runs along the medial edge beside the first metatarsal head, which loses
23–34 % of its tile to it. That region matters for push-off. Options for v1 are routing the trunk through
the arch seam instead, or putting part of the bundle on the bottom layer under the arch region (the arch
carries little load).

**Manufacturing.** A personal sole is a new flex design. Panelise the left and right soles together. For
research cohorts, a graded set (EU 36–47 in two widths) avoids a new order per person; personalise only
where the anatomy needs it.

## 6. The pod (prototype, off-the-shelf parts; proposed and not yet built)

| Block | Prototype part | Why |
|---|---|---|
| MCU, radio, IMU, flash, charger | Seeed XIAO nRF52840 Sense: 6-axis LSM6DS3TR-C, 2 MB flash, BQ25101 charger, 6 analog pins | All on one 21 × 17.5 mm board; the IMU moves with the foot when the pod is on the instep |
| Channel select | 16:1 analog multiplexer (CD74HC4067 class) | 16 sense lines into one readout |
| Readout | Transimpedance amplifier with a zero-drift op-amp (OPA333 class); the common comb is driven at a reference voltage | Output is proportional to conductance, roughly linear in load; unselected lines float, so there is no crosstalk |
| Connector | 18-pin, 0.5 mm flat-flex connector | Takes the sole's tail |
| Storage | microSD | 16 channels × 12 bit plus the IMU at 100 Hz is about 3.6 kB/s, or 13 MB an hour |
| Battery | 150–250 mAh LiPo | Estimate of 6–10 mA while streaming, so tens of hours; to be measured |
| Sync | One input (wired or optical pulse) | Aligns with force plates and cameras |

Pin budget on the XIAO's 11 I/O pins:
- 4 multiplexer address pins, 1 analog input, 4 for the SPI to the microSD, 1 sync input, 1 spare.

Pod v1 (custom board, bare nRF52840 module) adds 32 channels, more storage and a smaller enclosure.

## 7. Data and integration

- **Streams.** The host receives Bluetooth LE and publishes LSL streams `rehab_sole_L` and `rehab_sole_R`
  (16 pressure channels, 6 IMU channels, pod time). This is the same mechanism `rehabtwin` already uses for
  posture and cue streams, so sessions record it without new plumbing.
- **Provenance.** Values carry the label "measured, research device, not validated" until section 8 is done.
  The display rule applies: no user-facing load claim until the force-plate comparison passes its
  pre-set thresholds.
- **Data handling.** Recordings are health data and stay out of every repository.

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

## 9. Decisions needed

1. **Where the design lives.** Decided 2026-11-02: open hardware in the public repository
   `Sigurius23/rehab-agent`, folder `hardware/sensor-sole/`, under CERN-OHL-S-2.0 (see `README.md`).
2. **Which FiveFingers model.** Decided 2026-11-02: KSO Trek, kangaroo leather, EU 42. Its leather footbed
   is not removable, so the sole lies on top (section 2). Still open: the collar height at the arch, which
   sets the tail length.
3. **Pod position.** Instep (recommended: the IMU then measures the foot) or ankle.
4. **Channels.** 16 on the XIAO prototype now, or go straight to a 32-channel custom pod.
5. **Materials for the coupon test**, and the budget and fabricator for the flex boards.
6. **Ethics and consent** (decision D8 in the review) before anyone other than the developers wears it.

## 10. Files and how to run

- `sole_gen.py`: the generator. Run `python sole_gen.py --size 42 --out out/`, with optional `--length`,
  `--width`, `--side L`, `--exit heel`, `--mode point` and `--foot person.json`. It needs numpy, scipy,
  shapely, matplotlib and ezdxf.
- `person_example.json`: the personalisation format.
- `out/` (not committed; regenerate it): previews and exports of any run.

Next steps (not started):
- export the sole to KiCad, with the combs as custom-shaped pads and the tail as a connector footprint;
- draw the pod carrier schematic;
- design the coupon board.

## 11. Sources

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
