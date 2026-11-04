<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Test runs: what ran and what was skipped

**2026-11-04.** Recorded with `tests/run_suites.py`, on the code in the commit that adds this file.

**Several suites need files that are not in this repository:**
- D'Hondt's nominal models (`DHONDT_NOMINAL_DIR`);
- the Synergy model (`SYNERGY_MODEL`);
- the paper's saved bspline (`DHONDT_EXP5`) together with CasADi.

Without them, those tests skip. **A skip is not a pass.**

CI (`.github/workflows/validate.yml`) runs only `test_channel_map.py`, so none of the OpenSim, CasADi or KiCad
suites run there.

## Summary

| Configuration | Suite | ok | skipped | expected failure | failed | Skip reasons |
|---|---|---|---|---|---|---|
| Pipeline Python (OpenSim 4.6), external models present | `test_sim_osim.py` | 16 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), external models present | `test_dhondt_port.py` | 11 | 1 | 0 | 0 | needs casadi and DHONDT_EXP5 |
| Pipeline Python (OpenSim 4.6), external models present | `test_foot_comparison.py` | 3 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), no external models | `test_sim_osim.py` | 16 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), no external models | `test_dhondt_port.py` | 5 | 7 | 0 | 0 | needs casadi and DHONDT_EXP5; needs opensim and DHONDT_NOMINAL_DIR |
| Pipeline Python (OpenSim 4.6), no external models | `test_foot_comparison.py` | 0 | 3 | 0 | 0 | needs opensim and DHONDT_NOMINAL_DIR; needs opensim and SYNERGY_MODEL |
| CasADi 3.8.2 Python, paper's saved bspline present | `test_dhondt_port.py` | 6 | 6 | 0 | 0 | needs opensim and DHONDT_NOMINAL_DIR |
| CasADi 3.8.2 Python, no external files | `test_dhondt_port.py` | 5 | 7 | 0 | 0 | needs casadi and DHONDT_EXP5; needs opensim and DHONDT_NOMINAL_DIR |
| Generator Python (shapely 2.2.0), fast cases | `test_sim_print.py` | 5 | 0 | 0 | 0 | — |
| Generator Python (shapely 2.2.0), fast cases | `test_generator_regressions.py` | 8 | 3 | 0 | 0 | set SOLE_SLOW_TESTS=1 (minutes per test) |
| System Python 3 (as CI runs it) | `test_channel_map.py` | 10 | 0 | 0 | 0 | — |

## What this means for the D'Hondt port

Its verification ran in two environments, and both are needed. No single environment has OpenSim and CasADi
together:
- **CasADi environment:** the committed knot table equals the paper's own saved bspline, at all 1,201
  reference angles (`OriginalBspline`).
- **OpenSim environment, with the models:** the ported models' forces against the original equations
  (`PortedModels`, including the output-hash check against `foot_models/PROVENANCE.json`).
- **Both, needing no external files:** the transcribed equations, and that the recorded hashes agree with
  the code (`Equations`, `Provenance`).

## Not run in this round

- **Slow generator cases** (`SOLE_SLOW_TESTS=1 python tests/test_generator_regressions.py`). The last run
  was 2026-11-04 on generator commit 0257862: 10 passed and 1 expected failure
  (`test_t1_eu37_right_fine_pass_is_clean`; the T1 EU 37 fine pass has not passed). The generator files
  have not changed since.
- **KiCad suites** (`test_verify_drc.py`, `test_verify_negative.py`; KiCad's Python). `verify_board.py` has not
  changed since their last recorded run (VERIFICATION.md, section 4).

## Each test

**Pipeline Python (OpenSim 4.6), external models present**

- `AssumedContact.test_calibration_hits_the_target_force`: ok
- `AssumedContact.test_same_law_whatever_the_model_contact`: ok
- `FailsClosed.test_contact_on_the_talus`: ok
- `FailsClosed.test_differing_contact_parameters`: ok
- `FailsClosed.test_geometry_used_by_another_force_type`: ok
- `FailsClosed.test_geometry_used_by_no_force`: ok
- `FailsClosed.test_half_space_on_the_foot`: ok
- `FailsClosed.test_keep_generic_tolerates_unused_geometry`: ok
- `FailsClosed.test_non_sphere_geometry_on_the_foot`: ok
- `FailsClosed.test_two_coordinate_joint_in_the_chain`: ok
- `MeasuredAxes.test_segment_boundary_follows_an_oblique_axis`: ok
- `MeasuredAxes.test_toe_line_follows_the_measured_axis`: ok
- `MultiSegmentFoot.test_points_go_on_the_segment_they_lie_under`: ok
- `MultiSegmentFoot.test_toes_not_reached_from_calcn_is_refused`: ok
- `ResidualsAndPerturbation.test_lateral_shift_and_unknown_key`: ok
- `ResidualsAndPerturbation.test_residuals_report_the_model_contact_off_the_plane`: ok
- `Equations.test_falisse_passive_moment`: ok
- `Equations.test_interpolation_error_against_the_reference`: ok
- `Equations.test_natali_transcription`: ok
- `Equations.test_table_knots_are_reference_samples`: ok
- `OriginalBspline.test_table_equals_the_saved_function`: skipped (needs casadi and DHONDT_EXP5)
- `PortedModels.test_fascia_tension_follows_natali`: ok
- `PortedModels.test_midtarsal_generalized_force`: ok
- `PortedModels.test_midtarsal_ligaments_off_only_in_the_port`: ok
- `PortedModels.test_mtp_generalized_force`: ok
- `PortedModels.test_other_files_are_refused`: ok
- `PortedModels.test_port_output_matches_the_recorded_hashes`: ok
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok
- `Harness.test_posture_mapping`: ok
- `Harness.test_rigid_three_and_four_segment_feet_agree`: ok
- `Synergy.test_kinematic_checks`: ok

**Pipeline Python (OpenSim 4.6), no external models**

- `AssumedContact.test_calibration_hits_the_target_force`: ok
- `AssumedContact.test_same_law_whatever_the_model_contact`: ok
- `FailsClosed.test_contact_on_the_talus`: ok
- `FailsClosed.test_differing_contact_parameters`: ok
- `FailsClosed.test_geometry_used_by_another_force_type`: ok
- `FailsClosed.test_geometry_used_by_no_force`: ok
- `FailsClosed.test_half_space_on_the_foot`: ok
- `FailsClosed.test_keep_generic_tolerates_unused_geometry`: ok
- `FailsClosed.test_non_sphere_geometry_on_the_foot`: ok
- `FailsClosed.test_two_coordinate_joint_in_the_chain`: ok
- `MeasuredAxes.test_segment_boundary_follows_an_oblique_axis`: ok
- `MeasuredAxes.test_toe_line_follows_the_measured_axis`: ok
- `MultiSegmentFoot.test_points_go_on_the_segment_they_lie_under`: ok
- `MultiSegmentFoot.test_toes_not_reached_from_calcn_is_refused`: ok
- `ResidualsAndPerturbation.test_lateral_shift_and_unknown_key`: ok
- `ResidualsAndPerturbation.test_residuals_report_the_model_contact_off_the_plane`: ok
- `Equations.test_falisse_passive_moment`: ok
- `Equations.test_interpolation_error_against_the_reference`: ok
- `Equations.test_natali_transcription`: ok
- `Equations.test_table_knots_are_reference_samples`: ok
- `OriginalBspline.test_table_equals_the_saved_function`: skipped (needs casadi and DHONDT_EXP5)
- `PortedModels.test_fascia_tension_follows_natali`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_ligaments_off_only_in_the_port`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_mtp_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_other_files_are_refused`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_port_output_matches_the_recorded_hashes`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok
- `Harness.test_posture_mapping`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Harness.test_rigid_three_and_four_segment_feet_agree`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Synergy.test_kinematic_checks`: skipped (needs opensim and SYNERGY_MODEL)

**CasADi 3.8.2 Python, paper's saved bspline present**

- `Equations.test_falisse_passive_moment`: ok
- `Equations.test_interpolation_error_against_the_reference`: ok
- `Equations.test_natali_transcription`: ok
- `Equations.test_table_knots_are_reference_samples`: ok
- `OriginalBspline.test_table_equals_the_saved_function`: ok
- `PortedModels.test_fascia_tension_follows_natali`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_ligaments_off_only_in_the_port`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_mtp_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_other_files_are_refused`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_port_output_matches_the_recorded_hashes`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok

**CasADi 3.8.2 Python, no external files**

- `Equations.test_falisse_passive_moment`: ok
- `Equations.test_interpolation_error_against_the_reference`: ok
- `Equations.test_natali_transcription`: ok
- `Equations.test_table_knots_are_reference_samples`: ok
- `OriginalBspline.test_table_equals_the_saved_function`: skipped (needs casadi and DHONDT_EXP5)
- `PortedModels.test_fascia_tension_follows_natali`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_midtarsal_ligaments_off_only_in_the_port`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_mtp_generalized_force`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_other_files_are_refused`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `PortedModels.test_port_output_matches_the_recorded_hashes`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok

**Generator Python (shapely 2.2.0), fast cases**

- `Print.test_carrier_and_cover_are_watertight_with_one_hole_per_wire`: ok
- `Sim.test_export_has_points_in_every_region_and_contact_order`: ok
- `Sim.test_left_points_mirror_right`: ok
- `Sim.test_missing_force_columns_fail`: ok
- `Sim.test_readout_sums_regions_and_follows_the_sensor_model`: ok
- `ExportPrecision.test_larger_difference_fails_closed`: ok
- `ExportPrecision.test_mirrored_comb_exports_valid_connected_pads`: ok
- `ExportPrecision.test_subgrid_neck_fails_closed`: ok
- `ExportPrecision.test_subgrid_slit_is_rebuilt_without_changing_copper`: ok
- `ExportPrecision.test_valid_outline_is_written_exactly_as_before`: ok
- `Fracture.test_mirrored_comb_splits_into_hole_free_pieces`: ok
- `Fracture.test_no_progress_fails_closed`: ok
- `Fracture.test_vertical_cut_without_progress_falls_back_to_another_cut`: ok
- `SlowRegressions.test_t1_eu37_right_fine_pass_is_clean`: skipped (set SOLE_SLOW_TESTS=1 (minutes per test))
- `SlowRegressions.test_t1_eu37_right_plan_is_planar`: skipped (set SOLE_SLOW_TESTS=1 (minutes per test))
- `SlowRegressions.test_t1_mirrored_synthetic_foot_exports`: skipped (set SOLE_SLOW_TESTS=1 (minutes per test))

**System Python 3 (as CI runs it)**

- `Resolve.test_ambiguous`: ok
- `Resolve.test_edited_map`: ok
- `Resolve.test_id_not_from_design_hash`: ok
- `Resolve.test_inconsistent_maps`: ok
- `Resolve.test_malformed_ids`: ok
- `Resolve.test_missing`: ok
- `Resolve.test_one_matching_map`: ok
- `Resolve.test_package_side_differs_from_id`: ok
- `Resolve.test_unreadable_file_blocks_resolution`: ok
- `Resolve.test_wrong_foot`: ok

