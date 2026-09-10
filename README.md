# Intelligent Agents, Search and Markov Decision Processes

An academic artificial intelligence project that explores three complementary ways of making decisions under incomplete or uncertain information: logical inference, Bayesian belief updates, and Markov decision processes (MDPs).

The project places Captain Willard in grid-based environments inspired by *Apocalypse Now*. Depending on the scenario, the agent must locate Colonel Kurtz, avoid hidden hazards, plan safe routes, or cross a stochastic river while maximizing expected reward.

## What this project demonstrates

- Knowledge-based reasoning from accumulated percepts rather than access to the hidden map.
- Enumeration of logically consistent worlds to infer safe cells and possible hazards.
- BFS, DFS, Greedy Best-First Search, and A* route planning.
- Bayesian updates over the possible locations of traps, a soldier, an exit, and Kurtz.
- Risk-aware planning based on posterior probabilities.
- MDP modelling with stochastic transitions, obstacles, rewards, terminal states, and Value Iteration.
- Reproducible experiments through optional random seeds.
- Manual and automatic execution modes with inspectable console output.

## Project structure

| File | Purpose |
| --- | --- |
| `kurtz.py` | Knowledge-based agent for the hidden palace. It combines logical inference with uninformed and heuristic search. |
| `palacio.py` | Bayesian version of the palace problem. It maintains probability distributions and plans using a configurable risk threshold. |
| `river_mdp.py` | Stochastic river-crossing environment solved with Value Iteration and validated through simulation. |
| [`intelligent-agents-technical-report.pdf`](output/pdf/intelligent-agents-technical-report.pdf) | English technical report that preserves the structure and restrained academic style of the original submission. |
| `tests/test_core.py` | Dependency-free regression tests for the main invariants and algorithms. |
| `requirements.txt` | Explicitly records that the project has no third-party package dependencies. |

`palacio.py` reuses utilities from `kurtz.py`, so both files must remain in the same directory.

## Requirements

- Python 3.10 or newer
- No third-party Python packages
- A UTF-8-capable terminal for the symbols and optional ANSI colours

For compatibility with standard Python workflows, the repository includes a comment-only `requirements.txt`. Running the usual installation command is therefore safe but does not download anything:

```bash
python -m pip install -r requirements.txt
```

## Run the programs

Clone the repository, enter its directory, and run any of the three entry points:

```bash
python kurtz.py
python palacio.py
python river_mdp.py
```

Each program guides you through its available options. Press `Enter` when prompted for a seed to generate a new environment, or enter an integer to reproduce the same random setup.

### Logical palace agent

`kurtz.py` offers manual and automatic modes. The automatic mode supports:

```text
bfs | dfs | gbfs | astar
```

The displayed board represents the agent's knowledge, not the hidden world. Candidate hazards and goals therefore change as new percepts are collected.

### Bayesian palace agent

`palacio.py` also supports manual and automatic modes. Its risk threshold `p` controls which cells the planner may enter:

```text
cell allowed <=> P(death | cell) < p
```

The default threshold is `0.20`. A higher value permits more aggressive plans; a lower value makes the agent more conservative.

### River MDP

`river_mdp.py` builds a stochastic river, computes an optimal policy with Value Iteration, and simulates one episode. Interior columns have different current strengths, while islands behave as impassable obstacles. Optional hazardous cells add configurable terminal risk and a strong negative reward.

On a legacy Windows shell, redirected output may require UTF-8 mode because the visual policy uses arrow characters:

```powershell
$env:PYTHONUTF8 = "1"
python river_mdp.py
```

## Run the tests

The test suite uses Python's standard library only:

```bash
python -m unittest discover -s tests -v
```

The same suite runs automatically on GitHub Actions with supported Python versions.

## Academic context

This repository was developed by Claudia Moya Rodríguez for the *Fundamentals of Artificial Intelligence* course during the 2025-2026 academic year. The original console interface remains in Spanish to preserve the terminology of the assignment, while the README and technical report are presented in English for an international audience.

## Author

[Claudia Moya Rodríguez](https://github.com/claudiamoya8)

## License

Distributed under the [MIT License](LICENSE).
