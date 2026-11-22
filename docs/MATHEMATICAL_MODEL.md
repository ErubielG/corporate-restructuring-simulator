# Mathematical model and design decisions

## Purpose and scope

This repository provides a **synthetic computational experiment**, not a fitted economic forecast.
The engine was developed within a research project on restructuring timelines and the
**distinction between formal legal transfer and operational autonomy**. It does not attempt
to establish that any hypothetical divestiture is legally required or economically beneficial.

## Historical research and calibration boundary

The wider offline research compiled an Atlas with **63 documentary case records**. Only
**23 exact sale-duration observations** were available in one exploratory sample, largely
concentrated in the United Kingdom. A subset of 22 was provisionally used to illustrate a
legal-sale benchmark in the private research package. No sufficiently validated pairs of
sale date and full operational-independence date were established. To avoid implying that
this sample can support broad probabilistic claims, the **public package does not ship the
Atlas or use historical observations**. All stochastic parameters in this demo are hypothetical.

## 1. Reproducible Monte Carlo experiment

For each synthetic entity `i`, the generator samples a profile and stage durations using a
pseudo-random number generator with a declared seed. Repeated cohort runs across configured
seeds explore **variation produced by the simulation assumptions**, not a confidence interval
for real-world corporate restructurings.

For a stage with lower `a`, mode `m`, upper `b`, a triangular distribution is used:

```text
T ~ Triangular(a, m, b)        where a <= m <= b
```

The triangular distribution is a **scenario assumption**, not an empirical fit. The engine
applies configured stage multipliers, complexity effects, dependencies and stochastic incidents.
See `v3sim/engine.py` for the sampling logic and `v3sim/dynamic_engine.py` for event scheduling.

## 2. Complexity scores and categories

The synthetic profile combines four dimensions: technical complexity, dependencies,
labor, and service continuity. A weighted score is computed using configured weights:

```text
S_i = w_T T_i + w_D D_i + w_L L_i + w_C C_i
sum(weights) = 1
```

Configured thresholds and critical risk rules define experimental categories I, II and III.
They are **not validated legal classifications** and are not proposed statutory deadlines.
The public baseline config uses sample category maxima of 18, 36 and 60 months; these are
purely illustrative values.

## 3. Directed acyclic graph of tasks

A task may start only when all its predecessors are complete:

```text
ready(k, t) = all(status(predecessor) == finished)
```

Legal and operational tasks can overlap where the dependency graph permits. The model tracks
**control transfer** and **operational autonomy** separately; the latter may depend on
completion of critical transitional services (TSA). Noncritical ordinary commercial supply is
not automatically treated as a block to autonomy.

## 4. Dynamic discrete-event engine

Events are ordered in a min-heap using tuples conceptually like:

```text
(event_time, event_priority, sequence_id, event_kind, stage, token, payload)
```

Generation tokens invalidate a superseded completion event when its task has been paused,
rescheduled, or replaced. This prevents an old event from incorrectly completing a task
without deleting the historical event trace. The engine supports appeals, suspensions,
buyer withdrawal, remedy revisions, and technical failures. The optional I03 extension adds
scripted adverse pathways, not empirically estimated event frequencies.

## 5. Outcome definitions

For a synthetic entity `i`, with modeled autonomy time `A_i` and assumed category deadline
`D_i`, the demo computes:

```text
I_i = 1 if A_i <= D_i else 0
R = (1/N) * sum(I_i for i in 1..N)
```

`R` is the **simulated share of cases meeting an artificial time threshold**, not the fraction
of actual firms complying with a law. The reference target of 60% present in some configs
is an evaluation benchmark, **not** a target for automatic calibration or fitting.

## 6. Sensitivity and predictive-modeling cautions

Changing one or more assumed multipliers and repeating across seeds measures model
sensitivity. Min/max bands across a fixed set of seeds are **not statistical confidence
intervals**. A future machine-learning model trained on these synthetic outcomes would only
learn to emulate the simulator unless independently validated on real observations.

## Methodology and honest limits

- Historical cases are incomplete and geographically unrepresentative for generalization.
- Formal transfer and full independent operations are different observables.
- The model has no price, worker, welfare, or competition-outcomes component.
- Convergence of a computation does not establish predictive validity.
- Probability values, transition effects, and category deadlines in this demo are assumed.
- Simulated outcomes must never be described as empirical policy success rates.

## Code origins

The 16 Python modules in `v3sim/` are the unmodified V3.2.1-I03 engine and related
research utilities. Public tests and analysis scripts are an additional wrapper. The
research questions and criteria were human-directed, with AI-assisted code development,
review and documentation. The private documentary Atlas is not included.
