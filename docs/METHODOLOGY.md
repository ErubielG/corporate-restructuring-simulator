# Reproducibility and interpretation

- The demonstration database contains **no historical records**; it is a SQLite schema fixture only.
- Every simulated company is prefixed `SYNT-` and represents an invented profile.
- `evidence_mode: synthetic_only` ensures all sale-stage durations are synthetic.
- Scenario parameter values and fixed seeds are declared in JSON for audit.
- `autonomy_by_maximum` is the percentage of synthetic profiles whose modeled autonomy timestamp is no later than the experiment's category maximum. It is **not** a legal compliance rate.
- Commercial post-sale supply can coexist with operational independence: it should not be naively classified as a blocking TSA.
- Observed sales are not identical to independent operations; the demo does not model general equilibrium or policy welfare.
- Claims about incidence of court appeals, buyer withdrawal, technical failure, and delay are outside the validity of this demo.

## Local verification

1. Python `>=3.10`.
2. `python -m unittest discover -s tests -v`.
3. Generate fixture via `python scripts/make_synthetic_fixture.py`.
4. Execute `v3sim.dynamic_cli` with `config_demo_synthetic.json`.
5. Inspect `output/demo/resumen_y_procedencia.json` and source config; compare repeated runs with the same seed.

## Code provenance

All `.py` modules under `v3sim` are copied from the internal V3.2.1-I03 prototype **without modifying its simulation rules**. The demo SQLite generator, demo config, and standalone public tests are an added packaging layer. The full research data and any source copies are not redistributed.

## CI

The GitHub Actions workflow runs the **public** test suite and generates a synthetic cohort without access to the internal Atlas. The original research's 87-test suite is not reproduced by the public CI workflow and should not be represented as such.
