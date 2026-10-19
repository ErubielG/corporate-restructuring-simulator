# Corporate Restructuring Simulator

### Discrete-Event Simulation | Data Analysis | Monte Carlo Methods | Python

## Overview

Corporate Restructuring Simulator is a Python-based computational project designed to study the uncertainty, complexity, and duration of corporate restructuring processes.

The project uses **discrete-event simulation and Monte Carlo methods** to model how regulatory procedures, operational dependencies, legal appeals, and unexpected disruptions can influence restructuring timelines.

Rather than assuming that corporate restructuring follows a fixed schedule, the simulator models different events and evaluates how they affect the progress and outcomes of simulated companies.

The project is also a practical exploration of **data science, statistical analysis, simulation engineering, and predictive modeling**.

## Objectives

The main objectives are to:

- Develop reproducible computational simulations of corporate restructuring.
- Model legal, technical, and operational dependencies.
- Analyze the effects of delays and unexpected events.
- Study uncertainty through Monte Carlo experiments.
- Explore relationships between organizational complexity and restructuring timelines.
- Evaluate different assumptions through sensitivity analysis.
- Investigate the limitations of simulation-based predictions.

## Simulation Model

The simulation engine is based on a discrete-event architecture developed through multiple iterations, including versions 3.2 and 3.2.1-I03.

The model can represent events such as:

- Regulatory approvals and legal appeals.
- Buyer withdrawal and replacement.
- Operational separation and technical dependencies.
- Transitional service agreements.
- Technical failures and certification delays.
- Partial transfers and alternative remedies.
- Unfinished restructuring processes.

By introducing uncertainty into these processes, the model generates different outcomes for analysis.

## Technologies

| Technology | Application |
|---|---|
| Python | Simulation engine and computational logic |
| SQLite | Structured data storage |
| JSON | Scenario configuration |
| CSV | Simulation results and data exchange |
| Monte Carlo Methods | Uncertainty and scenario analysis |
| Discrete-Event Simulation | Event scheduling and process modeling |

Additional data analysis and visualization tools will be integrated as the public repository develops.

## Research Background

This project originated as part of *Sistemas y Sociedad*, an independent interdisciplinary research initiative exploring economic concentration, corporate control, institutional oversight, and market regulation.

The broader research includes a documentary atlas of 63 historical restructuring and divestiture cases.

However, the simulation engine is maintained as a separate computational project.

Its purpose is to explore restructuring processes and develop technical skills in simulation, programming, and data analysis.

## Current Status

**Experimental project — public repository under development.**

The underlying simulation engine has undergone several iterations and automated testing.

The public version is being reorganized for reproducibility, documentation, and independent execution.

Future development will include exploratory data analysis, visualization, additional sensitivity experiments, and predictive modeling exercises.

## Limitations

This project is primarily an experimental simulation framework.

Simulated outcomes depend on assumptions regarding event probabilities, process durations, organizational characteristics, and operational dependencies.

**Synthetic results should not be interpreted as validated predictions of real corporate restructuring outcomes.**

The available historical research is not sufficient to establish reliable general-purpose predictions of operational independence or restructuring success.

Any predictive models developed from synthetic outputs must be evaluated separately from models trained and validated on real-world observations.

## Roadmap

- [ ] Organize and document the public simulation engine.
- [ ] Provide reproducible example scenarios.
- [ ] Add exploratory data analysis notebooks.
- [ ] Visualize simulated duration distributions.
- [ ] Perform sensitivity and uncertainty analysis.
- [ ] Introduce and evaluate predictive modeling techniques.
- [ ] Document testing procedures and methodological limitations.
- [ ] Add automated testing through GitHub Actions.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

*This repository is intended for educational, computational, and exploratory research purposes.*
