# DCIM Framework — coarse

The `coarse` branch continues the earlier executable DCIM construction and
coarse-placement workflow. It retains bounded heuristic search, reviewed memory,
action guards and evidence interfaces.

## Branches

| Branch | Purpose | Workflow |
| --- | --- | --- |
| [main](https://github.com/astshby/DCIM-framework/tree/main) | Process-neutral improve-3-derived workflow, with configuration, initialization, context and evidence helpers | Main plans, Builder implements, Analyst reviews and reflects |
| [coarse](https://github.com/astshby/DCIM-framework/tree/coarse) | Earlier coarse-placement workflow, executable search and action guards | Integrated `initial-plan` / `reviewed-decision`, with legacy role APIs |
| [coarse_fine](https://github.com/astshby/DCIM-framework/tree/coarse_fine) | Experimental relative fine/coarse hierarchy, joint actions and physical-consumer interfaces | Earlier explicit role loop with granularity selection |

Each branch documents its own commands and validation scope. Existing runs retain
their pinned programs, instructions and configuration contracts.

## Getting started

Read [AGENTS.md](AGENTS.md), the [skill](dcim-self-improve/SKILL.md) and the
[runtime guide](dcim-self-improve/references/runtime.md). This branch uses its
existing private `project` / `input_files` configuration contract.

```sh
python3 dcim-self-improve/scripts/configure.py --output ../dcim.v2.local.json --from-config ../dcim.local.json --init study01
```

Initialization pins the run's programs and instructions. Use the resulting run's
copied scripts for subsequent commands. Relative configuration paths resolve
against the configuration file. Python 3.8+ supports the core runtime. Optional
GDS import/export uses `gdspy`.

## Workflow and capabilities

```text
Initialization -> initial-plan -> Builder -> independent Analyst / memory / reflection -> next task or closure
```

- `initial-plan` binds applicable compiler and digital-flow observations to
  learning goals, construction tasks and checks.
- `reviewed-decision` combines review, short memory, reflection and the next task
  or closure. AI proposal records are optional through this integrated entry.
- Budgeted geometry search includes simulated annealing, local improvement,
  sampled large-neighborhood rearrangement, coordinate beam search and adaptive
  destroy/repair.
- Builder executes candidate construction and retains inputs, scripts,
  dependencies, layout evidence and placement state.
- Analyst reviews evidence and learning outcomes. Short memory and reflection
  preserve failures, strategy changes and closure decisions.

Later searches start from the immediately preceding reviewed Builder's actual
placement. Compatible legacy request/Reflect interfaces retain the explicit
Reflect0 -> Builder -> Analyst -> memory -> Reflect loop and its required new AI
proposal at Reflect. Exact payloads and state transitions for both entry styles
are documented in the runtime guide.

## Components

| Location under `dcim-self-improve/` | Responsibility |
| --- | --- |
| `scripts/workflow.py` | Role transitions, requests, results and recovery |
| `scripts/planner.py`, `scripts/search/` | Budgeted search and proxy evaluation |
| `scripts/builder.py` | Candidate execution and retained outputs |
| `scripts/learning_contract.py` | Source-backed goals and per-goal review |
| `scripts/memory.py`, `scripts/experience.py` | Scoped memory and reviewed private experience packages |
| `references/runtime.md`, `references/sources.md` | Commands, contracts and method provenance |

Selected improve-3 guidance covers bounded tasks, relevant context, evidence
reuse, physical rows, seams and body/access ownership. See
[improve3-guidance.md](dcim-self-improve/references/improve3-guidance.md).

## Validation scope

Search evaluates geometry and center-HPWL proxies. Physical application requires
an actual consumer and candidate-bound verification. Source LVS, DRC, function,
ERC, electrical behavior and parent integration retain their own checks. See the
[algorithm portfolio](dcim-self-improve/references/algorithm-portfolio.md) for
implementation and validation details.

Action guards bind declared inputs, permitted actions, affected/frozen conditions
and output witnesses. Adapters declare the relevant physical conditions. Actual
mask/body/connectivity truth requires appropriate physical checks. OpenROAD
methods are research references. An OpenROAD integration is outside the current
implemented interfaces.

## Development checks

```sh
python3 -B -m unittest discover -s dcim-self-improve/tests -v
python3 -B -m unittest discover -s tests -v
git diff --check
```

Private configuration, PDK/compiler IP, models, runs and experimental evidence
belong in the user's private workspace. [HANDOFF.md](HANDOFF.md) records technical
history and validation. Source licensing is described in [LICENSE](LICENSE).
