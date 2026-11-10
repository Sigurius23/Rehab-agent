---
type: "decision"
title: "When a consumer feature may report an output"
status: "open"
area: "project"
question: "What must an output pass before a consumer feature is allowed to report it?"
source: "owner's research note on foot capture and pressure insoles, 2026-11-02"
updated: "2026-11-10"
---
# When a consumer feature may report an output

Intended-use thresholds per output; related to [[D-03]].

**Evidence from the video pilot (2026-11-10).** The validation report labels a route "approved for: screening" as
soon as one joint-and-plane cell passes against marker motion capture (`pipeline/rehabtwin/validation.py`). In the
pilot the one-camera route got that label with 1 cell passing and 33 failing, from one trial of one subject. The
cue gate itself is stricter: it opens only the cells that passed, and only for that session. The label is what a
reader of the report sees, so what it should require is part of this decision.
