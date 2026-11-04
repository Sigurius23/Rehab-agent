<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# 3D-printed first prototype

**2026-11-04. Decided by the project owner: the first physical prototype is 3D-printed.**
- **Design only.** Nothing has been printed or bought, and no material is chosen.
- **Untested:** sensing, fit and durability.
- **Not released.** The flex circuit (`DESIGN.md`, `kicad/`) remains a later stage.

`sole_print.py` builds the printed sole from the same generator output as the flex board: the outline with
toe tabs and tail, the sensing regions and the routing plan. Any size, foot or candidate the generator makes
can therefore be printed, and the printed sole and the simulated sole (`SIMULATION.md`) share their regions.

```
python sole_print.py out/sole_EU42_R.board.json -o print/   # generator's Python + manifold3d
```

## 1. The parts

| Part | Layers, bottom to top | Thickness |
|---|---|---|
| Carrier (TPU, 95A class, proposed) | Wire channels on the underside along the routing plan (0.5 mm) → a closed floor with one 1.2 mm hole per region and one for the common wire (0.5 mm) → one pocket per region on top (0.5 mm) | 1.5 mm |
| Cover (TPU) | A plain skin with the same outline | 0.4 mm |

- **Pockets** are the sensing regions inset by 0.6 mm. Neighbouring pockets keep a wall of at least 2.4 mm
  between them (EU 42).
- **Channels** follow the generator's routing plan to the tail at the medial arch. They widen with the number
  of wires they carry, up to 17 in the trunk (16 sense wires and the common wire, each 0.35 mm). The tail carries
  them to its end, where a connector or the pod's lead is attached.
- **Walls narrower than 0.8 mm** (two 0.4 mm nozzle widths) would not print as walls, so they are removed on
  purpose and reported. For EU 42 R that is 6.9 mm² in the channel layer, along the outline, and under 0.2 mm²
  elsewhere.
- **Bed fit.** An EU 42 sole with its tail fits a 256 × 256 mm bed when turned 138° (217 × 216 mm).
  `--bed` checks other printers.
- **Checks on the output:** both parts are written as watertight meshes. The carrier's genus of 17 is its 17
  holes through the floor. Outlines are simplified to 0.02 mm before meshing.

## 2. The sensor stack in each pocket (a proposal)

Bottom to top:
1. **Sense electrode:** copper tape or conductive fabric. Its wire comes up through the pocket's hole.
2. **Pressure-sensitive film:** one patch per pocket, Velostat class, about 0.1 mm thick.
3. **Common electrode:** one conductive-fabric sheet over the whole top. Its wire comes up through the hole at the
   tail root, which lies in a wall outside every pocket, so it cannot touch a sense electrode.
4. **The printed cover.**

That is 16 sense wires and one common wire, the same number of connections as the flex sole's 18 contacts. The
pod design (`DESIGN.md`, section 6) reads it the same way: one channel per region, the common driven.

## 3. How it differs from the flex sole

| | Flex sole | Printed prototype |
|---|---|---|
| Sensing | Shunt mode: interleaved copper combs under the film | Through mode: film between two electrodes |
| Thickness | About 0.35–0.40 mm (proposed stack) | 1.5 mm carrier + 0.4 mm cover, plus the electrodes and film |
| Connections | Copper on two layers, vias, a 0.5 mm-pitch tail | Insulated wires in printed channels |
| Region shape | The region itself | The region inset by 0.6 mm |
| Made by | A flex fabricator (not contacted) | A desktop printer with flexible filament, and hand assembly |

The response, hysteresis and crosstalk of through-mode film sensing are unknown. So is whether about 2 mm of
sole fits in the KSO Trek's toe pockets. Both are first questions for the bench and fit tests, not settled
facts.

## 4. Files

`print/EU42_R_<hash>.carrier.stl`, `.cover.stl`, `.print.json` (parameters, checks, bed fit, wiring) and
`.print.png` (top and underside). The printed sole carries the board ID of the design it came from, so a
printed sole and its simulation model name the same design.

## 5. First tests once it is printed (a plan; nothing printed yet)

1. **Coupon:** a few pockets with the stack, loaded with dead weights and an indenter. Linearity, hysteresis,
   creep, partial loading, and crosstalk between neighbouring pockets.
2. **Fit:** the toe tabs in the KSO Trek's pockets, the tail at the collar, comfort over an hour.
3. **Against simulation:** the same task simulated with this sole's regions (`SIMULATION.md`) and recorded on
   the bench, with thresholds set before the data is seen.
4. **Durability:** bending at the toe joint, delamination of the stack, and wire breaks in the channels.
