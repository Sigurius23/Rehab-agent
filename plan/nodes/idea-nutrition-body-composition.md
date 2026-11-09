---
type: "idea"
title: "Muscle and fat change with what and when the person eats"
status: "promoted"
area: "nutrition"
promoted_to: "[[adapt-nutrition-body-composition]]"
serves:
  - "[[pillar-adapt]]"
source: "owner's idea, 2026-11-09"
updated: "2026-11-09"
---
# Muscle and fat change with what and when the person eats

Predict how the twin's muscle and fat layers change with food intake: how much, what (protein especially), and when (meal timing, protein spread over the day, timing around training). The twin then shows the expected change in muscle capacity and fat distribution, and the next measurement (DXA, body shape, strength) checks it.

**Building blocks:**
- energy balance and body-composition dynamics, such as Hall et al.'s model behind the NIDDK Body Weight Planner, which splits a weight change into fat and fat-free mass;
- the twin's existing layers: fat (`fat-distribution/`), mass distribution from DXA, muscle capacity, strength calibration and training load from the sessions.

**Caveats to carry into the model:** the evidence for total intake and protein amount is much stronger than for meal timing, so timing effects need wide uncertainty bands. Food logs are health data: local-only by default ([[D-07]]).

## Food timing: what the evidence says (researched 2026-11-09)

From strongest to weakest:
- **Total energy and total protein: strong.** Energy balance sets the overall gain or loss, and the fat and fat-free
  split depends on the starting body fat (Hall et al. 2011). With resistance training, extra protein added
  0.30 kg (95 % CI 0.09–0.52) of fat-free mass across 49 trials and 1,863 people (Morton et al. 2018). The gain
  levelled off around 1.6 g/kg per day, but with a wide interval, and critics argue the breakpoint is uncertain and
  probably higher. The effect was smaller with age and larger in trained people.
- **Protein timing around training: no clear independent effect.** In a meta-analysis of 23 trials, timing showed
  no significant effect once total protein was accounted for; total intake was the strongest predictor of muscle
  gain (Schoenfeld, Aragon and Krieger 2013). Few of those trials matched total protein, so the timing question was
  barely tested. A later trial with protein matched found pre- and post-exercise protein gave similar gains.
- **Protein before sleep: preliminary.** In 44 young men over 12 weeks of training, about 30 g of casein before
  sleep gave more strength and muscle size than a placebo drink, without more fat (Snijders et al. 2015). The
  authors themselves call the evidence not yet conclusive.
- **Time-restricted eating: works through eating less, with a possible small lean-mass cost.** A 16:8 trial
  (TREAT) gave the same weight loss as three structured meals, with a small extra loss of appendicular lean mass,
  about 0.47 kg (Lowe et al. 2020). Over 12 months, eating within 8 hours plus calorie restriction was not
  significantly better than calorie restriction alone: −8.0 against −6.3 kg, with no substantial lean-mass
  difference (Liu et al. 2022).
- **Eating late: metabolic signals, no body-composition outcome.** In a lab crossover of 16 adults with overweight
  or obesity, the same meals eaten later raised hunger, lowered waking energy expenditure and shifted fat-tissue
  gene expression towards storage (Vujović et al. 2022). Weight was not measured.

**What this means for the model:**
- **The core** is energy balance and body-composition dynamics, plus a protein-and-training term for lean mass with
  a plateau of uncertain height that shrinks with age.
- **Timing enters as small modifiers** with priors near zero and wide uncertainty: protein spread and protein
  before sleep as possible small positive terms; time-restricted eating mainly through intake, with a possible
  small lean-mass cost; late eating through appetite and energy expenditure, not directly through composition.
- **The person calibrates it.** Each prediction is checked against the next DXA, body-shape or strength
  measurement, so the twin learns this person's response instead of assuming the average.
- **Promoted to a step** ([[adapt-nutrition-body-composition]]), with this test: predicted against measured DXA
  change over 8–12 weeks, with logged intake and training ([[t-nutrition-dxa]]).

## Resources

- [Hall et al. 2011, Quantification of the effect of energy imbalance on bodyweight (Lancet)](https://pubmed.ncbi.nlm.nih.gov/21872751/)
- [NIDDK Body Weight Planner, built on that model](https://niddk.nih.gov/research-funding/at-niddk/labs-branches/laboratory-biological-modeling/integrative-physiology-section/research/body-weight-planner)
- [The fat-distribution models in this repository](../../fat-distribution/README.md)
- [Morton et al. 2018, protein and resistance training meta-analysis (Br J Sports Med)](https://pubmed.ncbi.nlm.nih.gov/28698222/)
- [Schoenfeld, Aragon and Krieger 2013, protein timing meta-analysis (JISSN)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3879660)
- [Snijders et al. 2015, protein before sleep (summary, Frontiers)](https://blog.frontiersin.org/2019/03/07/bedtime-protein-for-bigger-gains-heres-the-scoop/)
- [Liu et al. 2022, calorie restriction with or without time-restricted eating (NEJM)](https://pubmed.ncbi.nlm.nih.gov/35443107/)
- [Vujović et al. 2022, late isocaloric eating (Cell Metabolism; Harvard summary)](https://sleep.hms.harvard.edu/news/late-isocaloric-eating-increases-hunger-decreases-energy-expenditure-and-modifies-metabolic)
