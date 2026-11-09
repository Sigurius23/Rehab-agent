---
type: "idea"
title: "EU compliance before any device leaves the lab"
status: "new"
area: "project"
serves:
  - "[[goal-working-method]]"
source: "owner's research note on open-source OpenGo alternatives, 2026-11-02/03"
updated: "2026-11-09"
---
# EU compliance before any device leaves the lab

A checklist from the research note (not legal advice):
- **Radio and EMC** for anything with BLE: RED 2014/53/EU, EN 300 328, EN 301 489, ESD immunity for custom boards.
- **Materials:** RoHS, REACH (sensors, adhesives, TPU, batteries), WEEE.
- **Data:** GDPR (gait and health data are special-category and can re-identify people), with a data protection
  impact assessment for systematic monitoring.
- **Medical device rules (MDR) only if the intended purpose is medical**; diagnostic information can make the app
  one.
- **Ethics committee approval** for studies with people.
