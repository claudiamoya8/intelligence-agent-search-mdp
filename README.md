# Intelligent Agents, Search and Markov Decision Processes

[![Python checks](https://github.com/claudiamoya8/intelligence-agent-search-mdp/actions/workflows/tests.yml/badge.svg)](https://github.com/claudiamoya8/intelligence-agent-search-mdp/actions/workflows/tests.yml)
![Python 3.10-3.14](https://img.shields.io/badge/Python-3.10--3.14-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Dependencies](https://img.shields.io/badge/dependencies-standard%20library%20only-2ea44f)

Three interactive artificial-intelligence environments implemented in Python using only the standard library. Together they explore how an agent can act when the world is hidden, uncertain, or governed by stochastic dynamics: logical model enumeration, classical and heuristic search, Bayesian belief updates, risk-aware planning, and Markov decision processes.

The scenarios share a narrative inspired by *Apocalypse Now*. Captain Willard must locate Colonel Kurtz, avoid hidden threats, find an exit, or cross a river whose current makes movement uncertain. The emphasis is on transparent reasoning: percepts, inferred worlds, probability maps, search traces, policies, and simulated transitions are visible in the console.

This is an individual project by **Claudia Moya Rodríguez**, developed for the *Fundamentals of Artificial Intelligence* course at ICAI, Universidad Pontificia Comillas, during the 2025-2026 academic year.

> **Language note:** the public documentation and technical report are in English. Source-code comments and interactive console prompts remain in Spanish, as originally submitted. The prompt tables below translate every input required to run the programs.

## Table of contents

- [Project overview](#project-overview)
- [AI concepts demonstrated](#ai-concepts-demonstrated)
- [Representative output](#representative-output)
- [Repository structure](#repository-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the programs](#running-the-programs)
- [Reproducibility](#reproducibility)
- [Validation](#validation)
- [Design notes](#design-notes)
- [Limitations](#limitations)
- [Technical report](#technical-report)
- [Academic-use notice](#academic-use-notice)
- [License](#license)
- [Author](#author)

## Project overview

The repository contains three executable programs. They are related by topic and narrative, but each uses a different representation of uncertainty and a different decision mechanism.

### 1. Logical knowledge-based agent (`kurtz.py`)

A partially observable 6 x 6 palace in the spirit of the Wumpus World.

- The hidden world contains exactly three distinct pits, one hostile soldier, one exit, and Colonel Kurtz.
- The agent observes only local percepts: breeze, snore, glow, four wall indicators, and the temporary scream caused by a successful grenade throw.
- A persistent knowledge base stores visited cells and every observation collected so far.
- Complete three-pit configurations are enumerated and rejected when they contradict any recorded breeze.
- Candidate sets for the soldier and exit are refined through positive and negative percepts.
- Cross-dependent deductions are repeated until the knowledge state stabilises.
- A cell is called safe only when the knowledge base can prove the absence of both a pit and the live soldier.
- BFS, DFS, Greedy Best-First Search, and A* plan routes over the currently permitted grid.
- Manhattan distance guides GBFS and A*, while deterministic tie-breaking makes traces reproducible.
- Manual play and two-stage automatic planning are available. Automatic mode plans first to Kurtz and then to the exit.

### 2. Bayesian palace agent (`palacio.py`)

A probabilistic counterpart to the first environment.

- The hidden map contains three trap types (`F`, `P`, and `D`), a soldier, an exit, and Kurtz.
- One discrete posterior distribution is maintained for each hidden entity.
- Deterministic likelihood masks update beliefs from positive and negative local stimuli.
- Visited cells, discovered events, and structural constraints remove impossible locations.
- An exact safety reweighting accounts for the fact that the soldier, exit, and Kurtz cannot be generated on trap cells.
- Marginal trap probabilities are combined into an aggregate probability of at least one trap.
- The mortality-risk map combines trap risk with the posterior probability of the live soldier.
- A configurable threshold `p` determines which cells are available to BFS, DFS, GBFS, or A*.
- If a complete route cannot be proved under the current evidence, any additional risk requires an explicit user decision.
- Manual and automatic modes expose both the belief matrices and the derived planning map.

### 3. Stochastic river-crossing MDP (`river_mdp.py`)

A finite Markov decision process solved by dynamic programming.

- The default environment is a 7 x 6 grid with two impassable islands, a start state, and an exit on the far bank.
- The action set is `up`, `down`, `left`, `right`, and `stay`.
- Interior columns have independently generated current strengths; the two banks have no current.
- For actions other than `down`, the intended move competes with a downward drift whose probability depends on the current column.
- Invalid movements become self-loops, so every transition remains inside the state space.
- Every action costs `-1`; entering the exit adds `+100`.
- Optional traversable hazards add a configurable penalty and may be terminal or non-terminal.
- Value Iteration computes the optimal value function and a greedy policy using `gamma = 0.95` and convergence tolerance `10^-6`.
- A sampled episode reports every state, action, transition cause, immediate reward, and accumulated return.

## AI concepts demonstrated

| Area | Implementation in this project |
| --- | --- |
| Knowledge-based agents | Persistent observations, candidate sets, consistent-world enumeration, and fixed-point propagation. |
| Uninformed search | Breadth-First Search and Depth-First Search over demonstrably permitted cells. |
| Informed search | Greedy Best-First Search and A* with admissible, consistent Manhattan distance. |
| Search diagnostics | Frontier, removed-node, and explored-set traces with method-specific `g`, `h`, or `f` values. |
| Probabilistic reasoning | Normalised belief distributions and deterministic Bayesian conditioning from local evidence. |
| Decision-making under risk | Mortality estimates, configurable risk thresholds, and explicit acceptance of uncertain expansions. |
| Markov decision processes | Finite state and action spaces, stochastic transitions, rewards, terminal states, and Bellman updates. |
| Dynamic programming | Value Iteration followed by greedy policy extraction. |
| Empirical inspection | Seeded environment generation and detailed policy-execution traces. |

The three agents can also be compared directly:

| Component | Hidden or uncertain information | Internal representation | Decision rule |
| --- | --- | --- | --- |
| Logical palace | Real location of pits, soldier, exit, and Kurtz | Consistent worlds and candidate sets | Enter only cells whose safety is logically established, unless the user accepts risk. |
| Bayesian palace | Location of every hidden entity | Posterior probability distributions | Plan through cells with `P(death | cell) < p`. |
| River MDP | Successor produced by an action | Transition and reward model | Select the action with maximum expected discounted return. |

## Representative output

The excerpts below come from real executions with seed `3`, with ANSI colour codes removed and long repetitive sections shortened.

### Logical deductions at the initial state

```text
--- Conocimiento del agente sobre el PALACIO ---

      1     2     3     4     5     6
     ------------------------------------
  1 | CW    ✓     *     *     *     *
  2 | ✓     *     *     *     *     *
  3 | *     *     *     *     *     *
  4 | *     *     *     *     *     *
  5 | *     *     *     *     *     *
  6 | *     *     *     *     *     *

Modelos pits consistentes: 5456
Recomendación de movimientos:
- derecha (pulse 'd') -> (1, 2)
- abajo (pulse 's') -> (2, 1)
Seguras no visitadas (según KB): (1, 2), (2, 1)
```

`CW` is Captain Willard, `✓` is a cell proved safe but not yet visited, and `*` is an unknown cell. The count of consistent pit worlds makes the remaining logical uncertainty explicit.

### Bayesian mortality-risk map

```text
--- Mapa de riesgo (para decidir movimientos) ---
Colores: riesgo de muerte (permitida si riesgo < p = 0.20)

      1     2     3     4     5     6
     ------------------------------------
  1 | CW    0.00  0.12  0.12  0.12  0.12
  2 | 0.00  0.12  0.12  0.12  0.12  0.12
  3 | 0.12  0.12  0.12  0.12  0.12  0.12
  4 | 0.12  0.12  0.12  0.12  0.12  0.12
  5 | 0.12  0.12  0.12  0.12  0.12  0.12
  6 | 0.12  0.12  0.12  0.12  0.12  0.12
```

The displayed number is the estimated probability of death on entering each cell, not the probability of one particular entity.

### River policy and sampled result

```text
River_strength por columna:
- columna 1: 0.0
- columna 2: 0.3
- columna 3: 0.5
- columna 4: 0.4
- columna 5: 0.6
- columna 6: 0.0

Política óptima (flechas):
 1   2   3   4   5   6
 →   →   →   →   →   ↓
 →   →   →   →   →   ↓
 →   →   ↓   I   →   ↓
 →   →   →   →   →   ↓
 →   →   →   →   →   ↓
 ↓   ↓   I   →   →   ↓
 →   →   →   →   →   E

Fin: EXIT  | pasos=11 | retorno_total=89
Estado final: (6, 5) (EXIT)
```

The policy is computed from the full transition model. The trajectory is then sampled, so a policy arrow does not guarantee that the intended successor will occur on a particular step.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── tests.yml                 # Cross-version syntax, unit, and CLI checks
├── output/
│   └── pdf/
│       └── intelligent-agents-technical-report.pdf
├── tests/
│   ├── test_cli.py                   # End-to-end console smoke tests
│   └── test_core.py                  # Model and algorithm regression tests
├── .editorconfig                     # Consistent editor settings
├── .gitattributes                    # Stable text and binary handling
├── .gitignore                        # Python, editor, build, and local-file exclusions
├── kurtz.py                          # Logical agent and search algorithms
├── LICENSE                           # MIT License
├── palacio.py                        # Bayesian agent and risk-aware planning
├── README.md
├── requirements.txt                  # Documents the zero-dependency runtime
└── river_mdp.py                      # Stochastic MDP and Value Iteration
```

`palacio.py` reuses shared grid, input, colour, and search utilities from `kurtz.py`; keep both files in the same directory.

## Requirements

- Python 3.10 or newer
- No third-party packages, datasets, APIs, or external services
- A UTF-8-capable terminal; ANSI colour support is optional

The repository has been validated locally with Python 3.12 and continuously on Python 3.10, 3.11, 3.12, 3.13, and 3.14.

`requirements.txt` is intentionally comment-only because every runtime import comes from Python's standard library. The usual installation command is safe and completes without downloading packages:

```bash
python -m pip install -r requirements.txt
```

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/claudiamoya8/intelligence-agent-search-mdp.git
cd intelligence-agent-search-mdp
```

A virtual environment is optional because there are no external dependencies. If you want an isolated interpreter:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Running the programs

Run every command from the repository root. Pressing `Enter` on a prompt with a documented default accepts that default.

### 1. Logical palace

```bash
python kurtz.py
```

| Spanish prompt | Meaning | Accepted input |
| --- | --- | --- |
| `En que modo desea jugar` | Select interactive or planned execution | `manual` or `auto` |
| `Elige búsqueda` | Search strategy in automatic mode | `bfs`, `dfs`, `gbfs`, or `astar` |
| `¿Modo silencioso?` | Hide detailed search and board output | `s` or `n`; default `n` |
| `¿Desea usar colores?` | Enable ANSI console colours | `s` or `n`; default `s` |
| `Semilla` | Reproduce the same generated world | Any integer, or `Enter` for random |

Manual controls:

```text
w / a / s / d    move up / left / down / right
g                throw the grenade, followed by a direction key
e                exit when Willard is on the exit and has found Kurtz
t                end the current game
```

The command-line entry point uses the assignment's fixed 6 x 6 board. The reusable helper functions accept other valid grid sizes for testing.

### 2. Bayesian palace

```bash
python palacio.py
```

| Spanish prompt | Meaning | Accepted input |
| --- | --- | --- |
| `¿Modo de juego?` | Select interactive or planned execution | `manual` or `auto` |
| `Búsqueda` | Search strategy in automatic mode | `bfs`, `dfs`, `gbfs`, or `astar` |
| `¿Modo silencioso?` | Reduce detailed automatic output | `s` or `n`; default `n` |
| `¿Mostrar traza de planificación?` | Print frontier and explored-state traces | `s` or `n`; default `s` |
| `¿Usar colores en consola?` | Enable ANSI console colours | `s` or `n`; default `s` |
| `Semilla` | Reproduce the same generated world | Any integer, or `Enter` for random |
| `Umbral de riesgo p` | Maximum estimated death probability accepted by the planner | A decimal value; default `0.20` |

Manual controls:

```text
w / a / s / d    move up / left / down / right
g                throw the grenade, followed by a direction key
x                exit when Willard is on the exit and has found Kurtz
t                end the current game
```

Automatic planning may ask whether one additional uncertain cell can be expanded. This is deliberately left to the user because accepting it changes the stated risk constraint.

### 3. River-crossing MDP

```bash
python river_mdp.py
```

| Spanish prompt | Meaning | Accepted input |
| --- | --- | --- |
| `¿Desea usar colores?` | Enable ANSI console colours | `s` or `n`; default `s` |
| `Semilla` | Reproduce the world and sampled episode | Any integer, or `Enter` for random |
| `Número de casillas peligrosas 'P'` | Add traversable hazardous cells | Integer `>= 0`; default `0` |
| `¿Las casillas peligrosas son terminales?` | End the episode on entry into a hazard | `s` or `n`; asked only when hazards exist |

The program displays the generated map, current strength per column, optimal policy, transition-by-transition simulation, final state, and final map.

On a legacy Windows terminal, redirected output may require UTF-8 mode because the policy uses arrow symbols:

```powershell
$env:PYTHONUTF8 = "1"
python river_mdp.py
```

## Reproducibility

All three programs accept an optional integer seed. Reusing the same seed and the same answers recreates the hidden map and its initial conditions. In the river component, the same random generator also samples the trajectory, so the entire demonstrated episode is reproducible.

Search ordering and tie-breaking are deterministic. Given an unchanged knowledge state, target, and algorithm, the frontier and explored traces remain stable.

## Validation

The project includes **14 automated checks**:

- 11 unit-level regression tests for model invariants and algorithms.
- 3 end-to-end smoke tests that launch the real console entry points with deterministic input.

| Component | Verified behaviour |
| --- | --- |
| Logical palace | Boundary-aware neighbours, distinct world entities, percept schema, valid paths for all four searches, and shortest paths for BFS/A*. |
| Bayesian palace | Normalised priors, deterministic likelihood updates, structural exclusion of traps, and route generation for all search methods. |
| River MDP | Environment invariants, valid probability distributions, and the optimal policy on a deterministic reference problem. |
| Console interfaces | All three scripts start, display their expected model output, and terminate cleanly without a traceback. |

Run the complete suite locally:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions repeats syntax compilation and all tests after every push and pull request on Python 3.10 through 3.14. The workflow uses read-only repository permissions and a five-minute job timeout.

## Design notes

- Palace coordinates are 1-indexed to match the assignment; the river MDP uses conventional 0-indexed internal coordinates.
- The palace boards display the agent's knowledge or beliefs, never a direct dump of the hidden map.
- Logical safety and Bayesian permission are intentionally different: the first requires proof, while the second compares estimated risk with `p`.
- Search traces expose `g` for BFS/DFS, `h` for GBFS, and `f = g + h` for A*.
- The Manhattan heuristic belongs to the palace graph searches. Value Iteration does not use a heuristic; it evaluates the MDP's complete transition and reward model.
- River islands are impassable obstacles. Optional hazards are separate, traversable cells with a penalty.
- ANSI colours improve readability only; every program can disable them without changing any algorithm.
- The absence of third-party dependencies is deliberate: the data structures, search routines, belief updates, and Value Iteration are implemented directly in Python.

## Limitations

- These are educational, terminal-based simulations rather than production applications.
- The interactive prompts and source comments are in Spanish.
- The command-line palace scenarios use a fixed 6 x 6 board, although several lower-level helpers are parameterised.
- The Bayesian observation model is deterministic; it does not model sensor noise or false observations.
- The aggregate trap-risk calculation uses the three marginal trap distributions before applying the environment's structural constraints to the safe entities.
- A normal river run demonstrates one sampled trajectory. Statistical evaluation would require many episodes and aggregate success, return, and path-length metrics.
- Complete pit-world enumeration is practical for the assignment's small grid but grows combinatorially with the board size and pit count.

## Technical report

A detailed English report explains the world models, percepts, logical deductions, Bayesian updates, risk calculations, search procedures, and MDP formulation:

[Read the technical report](output/pdf/intelligent-agents-technical-report.pdf)

The original Spanish submission is retained locally for provenance but intentionally excluded from the public repository.

## Academic-use notice

This repository is coursework published as a portfolio project. If you are currently completing the same or a closely related assignment, use it to understand the ideas and compare approaches, not as a submission to copy.

## License

Released under the [MIT License](LICENSE).

## Author

**Claudia Moya Rodríguez**<br>
Mathematical Engineering and Artificial Intelligence<br>
ICAI, Universidad Pontificia Comillas<br>
[GitHub profile](https://github.com/claudiamoya8)
