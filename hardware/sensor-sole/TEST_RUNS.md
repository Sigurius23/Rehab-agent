<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Test runs: what ran and what was skipped

**2026-11-04.** Recorded with `tests/run_suites.py`, on the code in the commit that adds this version of the file.
`workstation/setup.sh tests` runs the same suites on another machine and keeps its own record there.

**Several suites need files that are not in this repository:**
- D'Hondt's nominal models (`DHONDT_NOMINAL_DIR`);
- the Synergy model (`SYNERGY_MODEL`);
- the paper's saved bspline (`DHONDT_EXP5`) together with CasADi.

`workstation/fetch_inputs.py` fetches them at their pinned commits and checks them. Without them, those tests
skip. **A skip is not a pass.** A module with no unittest cases is reported as an error, not as an empty pass;
the KiCad checks are scripts, recorded by their exit code.

CI (`.github/workflows/validate.yml`, job `plan-and-sole`, from 2026-11-09) runs the suites that need no external
files on every push: `test_channel_map.py`, `test_case_store.py`, `test_compare_results.py`,
`test_forceplate_metrics.py` and `test_static_ik.py`, under Python 3.13 with numpy 2.5.4. Before they were added,
all 47 cases ran there with none skipped, on this machine. None of the OpenSim, CasADi or KiCad suites run in CI.

## Summary

| Configuration | Suite | ok | skipped | expected failure | failed | Skip reasons |
|---|---|---|---|---|---|---|
| Pipeline Python (OpenSim 4.6), external models present | `test_sim_osim.py` | 16 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), external models present | `test_dhondt_port.py` | 12 | 1 | 0 | 0 | needs casadi and DHONDT_EXP5 |
| Pipeline Python (OpenSim 4.6), external models present | `test_foot_comparison.py` | 3 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), external models present | `test_case_store.py` | 11 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), no external models | `test_sim_osim.py` | 16 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), no external models | `test_dhondt_port.py` | 6 | 7 | 0 | 0 | needs casadi and DHONDT_EXP5; needs opensim and DHONDT_NOMINAL_DIR |
| Pipeline Python (OpenSim 4.6), no external models | `test_foot_comparison.py` | 0 | 3 | 0 | 0 | needs opensim and DHONDT_NOMINAL_DIR; needs opensim and SYNERGY_MODEL |
| Pipeline Python (OpenSim 4.6), no external models | `test_case_store.py` | 11 | 0 | 0 | 0 | — |
| CasADi 3.8.2 Python, paper's saved bspline present | `test_dhondt_port.py` | 7 | 6 | 0 | 0 | needs opensim and DHONDT_NOMINAL_DIR |
| CasADi 3.8.2 Python, no external files | `test_dhondt_port.py` | 6 | 7 | 0 | 0 | needs casadi and DHONDT_EXP5; needs opensim and DHONDT_NOMINAL_DIR |
| Generator Python (shapely 2.2.0), fast cases | `test_sim_print.py` | 5 | 0 | 0 | 0 | — |
| Generator Python (shapely 2.2.0), fast cases | `test_generator_regressions.py` | 8 | 3 | 0 | 0 | set SOLE_SLOW_TESTS=1 (minutes per test) |
| System Python 3 (as CI runs it) | `test_channel_map.py` | 10 | 0 | 0 | 0 | — |
| System Python 3 (as CI runs it) | `test_case_store.py` | 11 | 0 | 0 | 0 | — |
| System Python 3.14.6, the laptop below, 2026-11-05 | `test_compare_results.py` | 9 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-05 | `test_compare_results.py` | 9 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-06 | `test_double_support.py` | 16 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-06 | `test_opencap_contacts.py` | 5 | 1 | 0 | 0 | needs OPENCAP_UTILS (opencap-processing's utilsProcessing.py at 72b5416) |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-06, OPENCAP_UTILS set | `test_opencap_contacts.py` | 6 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-06 | `test_static_ik.py` | 5 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-06 | `test_forceplate_metrics.py` | 12 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-08 | `test_dynamic.py` | 11 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-08, amendment 5 | `test_dynamic.py` | 19 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-08, amendment 6 | `test_dynamic.py` | 25 | 0 | 0 | 0 | — |
| Pipeline Python (OpenSim 4.6), the laptop below, 2026-11-09, settings v3 | `test_dynamic.py` | 33 | 0 | 0 | 0 | — |
| Generator Python (shapely 2.2.0), slow cases, the laptop below, 2026-11-06 | `test_generator_regressions.py` | 10 | 0 | 1 | 0 | — |
| KiCad 7.0.11's Python (pcbnew), script-style check | `test_verify_drc.py` | 1 | 0 | 0 | 0 | — |

**The same suites through `workstation/setup.sh tests`.** Inputs fetched by `fetch_inputs.py`, and the self-test
model rebuilt at commit 33aeb49. Run on this machine, they gave the same outcome for every test. On a laptop
without AVX-512 (Intel Core Ultra 9 290HX Plus, Ubuntu 26.04.1, 2026-11-05), where the rebuilt model's hash
differs (`PROVENANCE.json`, `two_segment`), every suite passed. Skipped there: the cases that need the other
environment's packages, the slow generator cases, and the KiCad checks (KiCad not installed).

**`test_compare_results.py`** (the results checker, added 2026-11-05) has so far run only on that laptop: under
the system Python through `setup.sh tests`, and under the pipeline Python directly. Its negative controls were
checked against two deliberately broken checkers, one blind to changed values and one blind to missing and
extra cases; the matching tests failed. CI runs it from 2026-11-09.

**`test_double_support.py`** (the force-plate check's double support and frame rule, added 2026-11-06) has so far
run only on that laptop. Its 15 cases passed through `setup.sh tests --slow`, where every other suite passed too;
all 16 passed through `setup.sh tests`. Its negative controls were checked against four deliberately broken
versions, and the matching tests failed each time:
- a solver that mirrors the posture (the lean and swap tests);
- a case store that never reuses (the resume test);
- a run that skips the inverse-kinematics hash check (the refusal test);
- the solver as committed in 5e2fa9c, before the staged start (the test with one foot off the floor).
The solver's third stage (height and ankles, with the roll held) was added for 14 static frames of one subject that
stalled with the pressure on the forefoot. No self-test case reproduces that stall, so no test covers that stage on
its own. It is checked by every one of the 6,142 dataset frames solving, with the same answer as before wherever the
earlier version had solved.
CI does not run it.

**`test_forceplate_metrics.py`** (added 2026-11-06, phase 2) checks the metrics on synthetic frames: the signs, the
force weighting of the combined centre of pressure, its projection on the forward axis, and the stop on changed
predictions. Those 7 cases were written and passed before any measured value was computed. The 3 cases of the
post-hoc plate-coverage rule, and the 2 of the post-hoc sideways diagnostic, were added after the data was seen,
with those analyses.

**`test_dynamic.py`** (added 2026-11-06, amendment 4) runs on synthetic data and reads no force data. Its 5 cases of the squat
window and the phase-2 metric functions were written before any dynamic solution existed. The 6 cases of the
pilot gate and the settings log were added on 2026-11-08 with settings v2, after the v1 pilot had failed.
The 8 cases of amendment 5 (validity with tracking, the penetration figure, evaluated counts, A minus B on
trials evaluated in both) were added the same day, before any dynamic result was compared with the plates. Two
of them read the recorded v1 arm-B pilot solution and skip without it. The 6 cases of amendment 6 (residual limits
on the recorded body weight, the recorded mass read and checked, both limits in the summary, a pilot gate that
needs no body weight) were added the same day; one reads the recorded v1 arm-A pilot solution and the dataset's
kinematics, and skips without them.
The 8 cases of settings v3 were added on 2026-11-09, after the v2 pilot had stopped. They cover:
- the strength rounding;
- the trunk and arm actuators;
- the check that no ground force reaches them, including a contact sphere on the trunk being refused;
- each strength being the peak inverse-dynamics torque rounded up, the same in both arms;
- the solve's model refusing to be built without the strengths;
- the initial guess at each arm's own contact balance.

Two of them need no data. Six use subject 2's models and kinematics, and skip without them.

**`test_static_ik.py`** (added 2026-11-06) needs no OpenSim. Its negative controls were checked against a builder
that carries unknown template elements over and one that ignores the reference marker list; the matching tests
failed.

**`test_opencap_contacts.py`** (OpenCap's contact-sphere rule, added 2026-11-06) has also run only on that laptop.
- Its comparison with OpenCap's own function needs `OPENCAP_UTILS`: opencap-processing's `utilsProcessing.py` at
  72b5416, sha256 `a79b727811ae41330b0f5a58bacf0bb6550bf1cccab74fbad7f1bdbcf05b9d13`. `fetch_inputs.py` does not
  fetch that file, so `setup.sh tests` skips that test.
- The file was fetched once by hand, and with it all 6 cases passed.
- The comparison's negative controls are in the suite: a sphere moved by 1e-8 m, a changed stiffness and a changed
  body mass are each found.

## What this means for the D'Hondt port

Its verification ran in two environments, and both are needed:
- **CasADi environment:** the committed knot table equals the paper's own saved bspline, at all 1,201
  reference angles (`OriginalBspline`).
- **OpenSim environment, with the models:** the ported models' forces against the original equations
  (`PortedModels`, including the output-hash check against `foot_models/PROVENANCE.json`).
- **Both, needing no external files:** the transcribed equations, and that the recorded hashes agree with the
  code and the committed soles (`Equations`, `Provenance`).

**Why not one environment.** OpenSim 4.6's pip wheel bundles CasADi 3.7 (for Moco). With CasADi 3.8.2 in the
same process, whichever loads second fails with undefined CasADi symbols. Checked on 2026-11-04 in both import
orders.

## Not run in this round

- **Slow generator cases** (`SOLE_SLOW_TESTS=1 python tests/test_generator_regressions.py`). Run here on
  2026-11-04, on generator commit 0257862: 10 passed and 1 expected failure
  (`test_t1_eu37_right_fine_pass_is_clean`; the T1 EU 37 fine pass has not passed). The generator files
  have not changed since. On the laptop, through `setup.sh tests --slow` on 2026-11-06, they gave the same
  outcome.
- **KiCad negative controls** (`test_verify_negative.py`, 2–3 minutes per case; `workstation/setup.sh tests
  --slow` runs them). `verify_board.py` has not changed since their last recorded run (VERIFICATION.md,
  section 4). Not run on the laptop on 2026-11-06 either: KiCad is not installed there.

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
- `Provenance.test_committed_soles_match_the_recorded_hashes`: ok
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok
- `Harness.test_posture_mapping`: ok
- `Harness.test_rigid_three_and_four_segment_feet_agree`: ok
- `Synergy.test_kinematic_checks`: ok
- `Store.test_any_change_in_the_key_runs_again_in_a_new_folder`: ok
- `Store.test_case_without_a_result_file_is_not_recorded`: ok
- `Store.test_damaged_record_or_result_is_not_trusted`: ok
- `Store.test_failing_case_leaves_no_record`: ok
- `Store.test_fingerprint_is_canonical`: ok
- `Store.test_finished_case_is_reused`: ok
- `Store.test_interrupted_case_is_repeated_and_its_folder_cleared`: ok
- `Store.test_no_resume_repeats_finished_cases`: ok
- `Store.test_parallel_workers_use_their_own_folders`: ok
- `Store.test_record_is_written_last`: ok
- `Store.test_same_key_in_another_group_is_another_case`: ok

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
- `Provenance.test_committed_soles_match_the_recorded_hashes`: ok
- `Provenance.test_recorded_hashes_agree_with_the_port`: ok
- `Harness.test_posture_mapping`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Harness.test_rigid_three_and_four_segment_feet_agree`: skipped (needs opensim and DHONDT_NOMINAL_DIR)
- `Synergy.test_kinematic_checks`: skipped (needs opensim and SYNERGY_MODEL)
- `Store.test_any_change_in_the_key_runs_again_in_a_new_folder`: ok
- `Store.test_case_without_a_result_file_is_not_recorded`: ok
- `Store.test_damaged_record_or_result_is_not_trusted`: ok
- `Store.test_failing_case_leaves_no_record`: ok
- `Store.test_fingerprint_is_canonical`: ok
- `Store.test_finished_case_is_reused`: ok
- `Store.test_interrupted_case_is_repeated_and_its_folder_cleared`: ok
- `Store.test_no_resume_repeats_finished_cases`: ok
- `Store.test_parallel_workers_use_their_own_folders`: ok
- `Store.test_record_is_written_last`: ok
- `Store.test_same_key_in_another_group_is_another_case`: ok

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
- `Provenance.test_committed_soles_match_the_recorded_hashes`: ok
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
- `Provenance.test_committed_soles_match_the_recorded_hashes`: ok
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
- `Store.test_any_change_in_the_key_runs_again_in_a_new_folder`: ok
- `Store.test_case_without_a_result_file_is_not_recorded`: ok
- `Store.test_damaged_record_or_result_is_not_trusted`: ok
- `Store.test_failing_case_leaves_no_record`: ok
- `Store.test_fingerprint_is_canonical`: ok
- `Store.test_finished_case_is_reused`: ok
- `Store.test_interrupted_case_is_repeated_and_its_folder_cleared`: ok
- `Store.test_no_resume_repeats_finished_cases`: ok
- `Store.test_parallel_workers_use_their_own_folders`: ok
- `Store.test_record_is_written_last`: ok
- `Store.test_same_key_in_another_group_is_another_case`: ok

**KiCad 7.0.11's Python (pcbnew), script-style check**

- `test_verify_drc.py (whole script)`: ok
