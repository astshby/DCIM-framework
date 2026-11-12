# DCIM Framework — coarse_fine

The `coarse_fine` branch preserves experimental relative fine/coarse planning,
joint actions and an opted-in physical consumer. End-to-end physical qualification
of fine optimization followed by coarse reuse remains incomplete.

## Branches

| Branch | Purpose | Workflow |
| --- | --- | --- |
| [main](https://github.com/astshby/DCIM-framework/tree/main) | Process-neutral improve-3-derived workflow, with configuration, initialization, context and evidence helpers | Main plans, Builder implements, Analyst reviews and reflects |
| [coarse](https://github.com/astshby/DCIM-framework/tree/coarse) | Earlier coarse-placement workflow, executable search and action guards | Integrated `initial-plan` / `reviewed-decision`, with legacy role APIs |
| [coarse_fine](https://github.com/astshby/DCIM-framework/tree/coarse_fine) | Experimental relative fine/coarse hierarchy, joint actions and physical-consumer interfaces | Earlier explicit role loop with granularity selection |

Each branch documents its own commands and validation scope. Existing runs retain
their pinned programs, instructions and configuration contracts.

## Getting started

Read [AGENTS.md](AGENTS.md), the [skill](dcim-self-improve/SKILL.md), the
[runtime guide](dcim-self-improve/references/runtime.md) and the
[two-scale guide](dcim-self-improve/references/two-scale.md). This branch retains
its original private configuration and explicit role-transition contracts.

```sh
python3 dcim-self-improve/scripts/configure.py --output ../dcim.v2.local.json --from-config ../dcim.local.json --init study01
```

Use each initialized run's pinned scripts and instructions. Relative configuration
paths resolve against the configuration file. Python 3.8+ supports the core
runtime. Optional GDS import/export uses `gdspy`.

## Workflow and granularity

```text
Initialization -> Reflect0 -> Builder -> independent Analyst -> memory -> Reflect
```

Reflect selects a fine, coarse or joint action for the current physical problem.
Fine actions address declared local interfaces and mutable geometry. Coarse
actions compose and place retained blocks. The action's scope, permitted changes,
frozen surroundings and physical checks are explicit.

Coarse composition inherits applicable fine constraints, including row height,
metal/track alignment, continuous PP/NP interfaces, powered TAP/body access and
signal/power entry. Relative granularity depends on the task and parent
constraints. The [two-scale guide](dcim-self-improve/references/two-scale.md)
describes hierarchy, selectors, actions and consumer contracts.

Builder retains actual construction outputs. Analyst reviews qualification,
commits scoped memory and passes evidence to Reflect. Later searches use the
immediately preceding reviewed Builder's actual placement. This branch uses its
explicit request/Reflect APIs. Consult the runtime guide for payloads.

## Components

| Location under `dcim-self-improve/` | Responsibility |
| --- | --- |
| `scripts/workflow.py` | Explicit role transitions and recovery |
| `scripts/planner.py`, `scripts/search/` | Budgeted heuristic exploration |
| `scripts/learning_contract.py` | Source-backed goals and review outcomes |
| `scripts/memory.py`, `scripts/experience.py` | Scoped memory and reviewed private experience packages |
| `references/two-scale.md` | Relative hierarchy, actions and physical-consumer interfaces |
| `references/algorithm-portfolio.md` | Algorithm choices, implementation and validation scope |

Selected improve-3 lessons are documented in
[improve3-guidance.md](dcim-self-improve/references/improve3-guidance.md).

## Validation scope and remaining work

The captured complete8x4 physical coarse round closed with failed physical
qualification due to OD density. Fine and return-coarse physical rounds were
unexecuted at that checkpoint. The full fine-to-coarse physical loop requires
further validation.

Consumer identity and pose checks bind declared actions to artifacts. Raw mask,
body, connectivity, electrical behavior and complete parent acceptance require
candidate-bound physical evidence. Geometry and center-HPWL search remain proxy
evaluations. Method references include OpenROAD work. Current interfaces require
private physical runners and adapters for actual implementation.

## Development checks

```sh
python3 -B -m unittest discover -s dcim-self-improve/tests -v
python3 -B -m unittest discover -s tests -v
git diff --check
```

Private configuration, PDK/compiler IP, models, runs and experimental evidence
belong in the user's private workspace. [HANDOFF.md](HANDOFF.md) records technical
history and validation. Source licensing is described in [LICENSE](LICENSE).
