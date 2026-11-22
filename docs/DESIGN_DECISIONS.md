# Technical evolution and design rationale

This page documents *why* the public M1 motor evolved, not a claim that its
assumptions have been empirically validated.

## Origin of the problem

The broader research asked whether a forced or negotiated corporate divestiture
could actually be completed within a fixed time. An order to sell assets is not
identical to an executed legal transfer, and a legal sale is not the same as
independent operational capacity. The historical case register strengthened
that distinction but did **not** provide a representative distribution of
full operational-autonomy times.

## Main modeling decisions

1. **Separate legal and operational clocks.** Each process has a legal/control
   transfer milestone and a separate operational-autonomy milestone, plus
   verification and possible transitional services.
2. **Use event-discrete scheduling instead of a single closed-form duration.**
   The V3.2 engine keeps a priority queue of future events. Tasks depend on
   previous tasks; incidents can insert delays, reopen buyer search or require
   rework. State changes are logged for auditability.
3. **Introduce heterogeneity.** Hypothetical companies receive sector and
   complexity variables; those variables modify selected task durations and
   priority categories.
4. **Use seeded random draws.** Triangular distributions represent bounded,
   explicitly assumed durations when a trustworthy historical distribution is
   unavailable. Seeds allow deterministic reruns, not empirical calibration.
5. **Protect model interpretation.** A sale or continued ordinary commercial
   supply is not automatically classified as operational dependence. Synthetic
   flags do not establish unlawful conduct or regulatory compliance.
6. **Represent difficult edge cases.** V3.2.1-I03 adds optional scenario
   pathways for partial asset transfers, substituted remedies, staged
   contractual transitions, certification delays and unfinished cases.
7. **Test the implementation separately from the hypothesis.** Automated
   regression and event-causality tests show software behavior, not economic
   prediction quality.

## Mathematical ideas

**Triangular sampling** for hypothetical process duration:

`T ~ Triangular(a, m, b)` where `a` is a lower bound, `m` is the most
likely assumed value, and `b` is an upper bound.

**Monte Carlo estimate**, conditional on a fixed configuration:

`p_hat = (1/N) * sum(1{autonomy_i <= assumed_maximum_i})`

`p_hat` is a proportion over simulated profiles. Without validated input
distributions, it must not be interpreted as a forecast or legal compliance
probability.

**Dependency constraints:** if stage B requires completion of stage A, then
`start(B) >= finish(A)`. For simultaneous tasks, completion time can depend on
the slowest prerequisite. The event queue also handles interruptions and
rescheduling rather than only precomputed sums.

**Category scoring:** weighted scores over technical, dependency, labor and
service-continuity dimensions are configurable, with critical-condition floors.
These are *synthetic modeling rules*, not authoritative regulatory criteria.

## Meaning of version numbers

| Stage | Contribution |
|---|---|
| V3.0.1 | Separate legal and operational milestones in preliminary schedules |
| V3.1 | Link selected durations to complexity; test sensitivity |
| V3.1.1 | Fix parameter propagation and improve reproducibility/provenance |
| V3.2 | Dynamic event queue, task dependencies, interruptions and rescheduling |
| V3.2.1-I03 | Optional pathways for partial/substituted/incomplete remedies |

The downloadable public package preserves the original V3.2.1-I03 Python
modules, while adding standalone demo fixtures, tests, scripts and notebooks.
The historical Atlas and I03 candidate evidence are not redistributed.
