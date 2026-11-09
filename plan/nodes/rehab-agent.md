---
type: "goal"
title: "A full-body digital twin that personalises to each person and adapts as they change"
status: "open"
area: "project"
source: "README.md; docs/architecture.md"
updated: "2026-11-09"
---
# A full-body digital twin that personalises to each person and adapts as they change

The end goal: a personalisation engine for a full-body digital twin. It measures a person, builds their own body
(bones, shape, mass, muscles, alignment), simulates how that body moves and is loaded, follows the person over
time, and acts through clinician-reviewed feedback, haptic cues and assistance. Anatomical accuracy is the first
design priority. A research prototype, not a medical device (`README.md`).

The engine in five pillars, after the pipeline's stages (`docs/architecture.md`):
- [[pillar-sense]]: measure the person's movement, forces and body;
- [[pillar-personalise]]: the person's own bones, shape, mass and muscles;
- [[pillar-simulate]]: joint loads, muscle forces and contact for that body;
- [[pillar-adapt]]: the twin follows the person over time;
- [[pillar-act]]: feedback and assistance from the twin.

Every claim the engine makes needs a test against measurement; the tests sit under the steps they check. How the
map works: `plan/README.md`.
