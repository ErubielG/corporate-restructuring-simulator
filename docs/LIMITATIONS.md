# Limitations and interpretation rules

The public repository uses **synthetic company profiles**, a SQLite fixture with
**zero real case records**, and hypothetical distributions, incidents and
category-specific deadlines. Its output does **not** estimate the behavior of
real companies, prove legal compliance, or assess the merits of any regulatory
policy.

## What is observed versus simulated?

| Item | Public demo status |
|---|---|
| Company profiles | Entirely synthetic (`SYNT-*`) |
| Legal transfer durations | Simulated; no historical durations imported |
| Operational independence durations | Simulated, not historically calibrated |
| Appeal, withdrawal, suspension probabilities | Hypothetical configuration parameters |
| Legal rulings, wrongdoing or sanctions | Not established by simulation |
| Category deadlines | Experimental assumptions, not legal standards |
| Sensitivity plots | Conditional variation across hypothetical scenarios |

The separate **Sistemas y Sociedad** research program documented 63 historical
case files and 23 precisely dated sale durations in an earlier archival cut,
but the sample is concentrated in the United Kingdom and does not supply
reliably paired sale-to-full-operational-autonomy durations. Those documents,
source material and SQLite databases are **not distributed in this repo**.

## What can go wrong?

- Historical selection bias: completed, documented sales are not representative
  of all proposed restructuring processes.
- Right-censoring: an unfinished case cannot be treated as a completed sale at
  the analysis horizon.
- Correlation: company characteristics and difficulties may co-vary; assuming
  independence can make outcomes too optimistic.
- Model risk: details of supply contracts, certification, ownership and
  infrastructure can defeat simplified event rules.
- Deadline choice: a high rate of modeled success can be an artifact of permissive
  hypothetical deadlines, as seen in an early Category III scenario.
- Monte Carlo sampling variability does not quantify uncertainty in the
  assumed probability distributions (epistemic uncertainty).
- Synthetic-only machine-learning models would learn the simulator's own rules;
  they would not establish real-world prediction accuracy.

## Metric definitions

- **control transfer**: time when the model's transfer event completes;
  not proof of ultimate beneficial ownership independence.
- **operational autonomy**: model-specific time at which critical operational
  conditions are completed; not a legal finding.
- **autonomy_by_maximum**: share of invented profiles whose simulated autonomy
  time is before an assumed category-specific threshold; **not a compliance
  rate** or externally validated probability.
- **min–max over seeds**: range observed in a finite set of simulations with
  fixed assumed distributions; **not a statistical confidence interval**.

## Legal and safety scope

No personal information or real-company confidential material is intentionally
included. Do not use this software as a decision system for legal enforcement,
employment decisions, transactions, or public policy without independent
validation, risk assessment and competent review.
